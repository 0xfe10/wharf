"""Shared helpers for the wharf build tools (Python standard library only)."""
import gzip
import hashlib
import io
import json
import os
import re
import tarfile
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_EPOCH = 1700000000
MAINTAINER = "Wharf <https://github.com/0xfe10/wharf>"
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9.+_-]*$")
VERSION_RE = re.compile(r"^[0-9][A-Za-z0-9.+~_-]*$")
SCRIPT_NAMES = ("preinst", "postinst", "prerm", "postrm", "conffiles")
CONTROL_ORDER = ("Package", "Version", "Depends", "Source", "Section", "Maintainer",
                 "Architecture", "Installed-Size", "Description")
MAX_DOWNLOAD = 200 * 1024 * 1024
UA = "wharf-build/1.0 (+https://github.com/0xfe10/wharf)"


class WharfError(Exception):
    pass


def epoch():
    value = os.environ.get("SOURCE_DATE_EPOCH")
    if value:
        if not value.isdigit():
            raise WharfError("SOURCE_DATE_EPOCH must be an integer")
        return int(value)
    return DEFAULT_EPOCH


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- plugin specs

def _check_rel(path, what):
    if os.path.isabs(path) or ".." in path.split("/"):
        raise WharfError("%s must be a relative path without '..': %r" % (what, path))


def load_plugin(plugin_dir):
    plugin_dir = os.path.abspath(plugin_dir)
    spec_path = os.path.join(plugin_dir, "plugin.json")
    try:
        with open(spec_path, encoding="utf-8") as f:
            spec = json.load(f)
    except (OSError, ValueError) as e:
        raise WharfError("cannot read %s: %s" % (spec_path, e))
    where = spec_path
    name = spec.get("name")
    if name != os.path.basename(plugin_dir) or not NAME_RE.match(name or ""):
        raise WharfError("%s: 'name' must equal the directory name" % where)
    pkgs = spec.get("packages")
    if not isinstance(pkgs, list) or not pkgs:
        raise WharfError("%s: 'packages' must be a non-empty list" % where)
    seen = set()
    for p in pkgs:
        pname = p.get("name", "")
        if not NAME_RE.match(pname) or pname in seen:
            raise WharfError("%s: bad or duplicate package name %r" % (where, pname))
        seen.add(pname)
        if not VERSION_RE.match(p.get("version", "")):
            raise WharfError("%s: bad version for %s" % (where, pname))
        if not NAME_RE.match(p.get("feed", "")):
            raise WharfError("%s: bad feed for %s" % (where, pname))
        if not isinstance(p.get("depends", []), list):
            raise WharfError("%s: depends of %s must be a list" % (where, pname))
        if not p.get("description"):
            raise WharfError("%s: %s needs a description" % (where, pname))
        if p.get("dir"):
            _check_rel(p["dir"], "dir")
        for g in p.get("gzip", []):
            _check_rel(g, "gzip entry")
    up = spec.get("upstream")
    if up:
        for key in ("repo", "asset", "package", "feed"):
            if not up.get(key):
                raise WharfError("%s: upstream.%s missing" % (where, key))
        if not re.match(r"^[\w.-]+/[\w.-]+$", up["repo"]):
            raise WharfError("%s: bad upstream.repo" % where)
        re.compile(up["asset"])
    spec["_dir"] = plugin_dir
    return spec


def iter_plugins(root=ROOT):
    base = os.path.join(root, "plugins")
    if not os.path.isdir(base):
        return []
    return [load_plugin(os.path.join(base, d)) for d in sorted(os.listdir(base))
            if os.path.isfile(os.path.join(base, d, "plugin.json"))]


# ------------------------------------------------------------------ ipk writing

def _tar_bytes(entries, mtime):
    """entries: list of (name, data|None, mode, is_dir). Returns gzip'd tar bytes."""
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as tf:
        for name, data, mode, is_dir in entries:
            ti = tarfile.TarInfo(name)
            ti.mtime = mtime
            ti.uid = ti.gid = 0
            ti.uname = ti.gname = ""
            ti.mode = mode
            if is_dir:
                ti.type = tarfile.DIRTYPE
                tf.addfile(ti)
            else:
                ti.size = len(data)
                tf.addfile(ti, io.BytesIO(data))
    out = io.BytesIO()
    with gzip.GzipFile(filename="", fileobj=out, mode="wb", compresslevel=9, mtime=0) as gz:
        gz.write(raw.getvalue())
    return out.getvalue()


def _collect_data(root_dir, gzip_list):
    files = {}
    dirs = set()
    if not os.path.isdir(root_dir):
        return files, dirs
    for cur, dnames, fnames in os.walk(root_dir):
        dnames.sort()
        rel_cur = os.path.relpath(cur, root_dir)
        for d in dnames:
            full = os.path.join(cur, d)
            if os.path.islink(full):
                raise WharfError("symlinks are not allowed: %s" % full)
        for fn in fnames:
            full = os.path.join(cur, fn)
            if os.path.islink(full):
                raise WharfError("symlinks are not allowed: %s" % full)
            rel = fn if rel_cur == "." else "%s/%s" % (rel_cur, fn)
            rel = rel.replace(os.sep, "/")
            with open(full, "rb") as f:
                data = f.read()
            mode = 0o755 if os.stat(full).st_mode & 0o111 else 0o644
            files[rel] = (data, mode)
    for g in gzip_list:
        if g not in files:
            raise WharfError("gzip entry %s not found under %s" % (g, root_dir))
        data, mode = files.pop(g)
        files[g + ".gz"] = (gzip.compress(data, 9, mtime=0), mode)
    for rel in files:
        parts = rel.split("/")[:-1]
        for i in range(1, len(parts) + 1):
            dirs.add("/".join(parts[:i]))
    return files, dirs


def render_control(fields):
    lines = []
    for key in CONTROL_ORDER:
        if key not in fields or fields[key] in ("", None):
            continue
        value = str(fields[key])
        if key == "Description":
            first, *rest = value.split("\n")
            lines.append("Description: " + first)
            lines.extend(" " + (r if r.strip() else ".") for r in rest)
        else:
            lines.append("%s: %s" % (key, value))
    return "\n".join(lines) + "\n"


def build_package(plugin, pkg, outdir, mtime=None):
    mtime = epoch() if mtime is None else mtime
    pdir = plugin["_dir"]
    base = os.path.join(pdir, pkg["dir"]) if pkg.get("dir") else None
    files, dirs = ({}, set())
    scripts = {}
    if base:
        files, dirs = _collect_data(os.path.join(base, "root"), pkg.get("gzip", []))
        ctl = os.path.join(base, "CONTROL")
        if os.path.isdir(ctl):
            for fn in sorted(os.listdir(ctl)):
                if fn not in SCRIPT_NAMES:
                    raise WharfError("unexpected file in CONTROL: %s" % fn)
                with open(os.path.join(ctl, fn), "rb") as f:
                    scripts[fn] = f.read()
    installed = sum(len(d) for d, _ in files.values())
    fields = {
        "Package": pkg["name"],
        "Version": pkg["version"],
        "Depends": ", ".join(pkg.get("depends", [])),
        "Source": "https://github.com/0xfe10/wharf/tree/main/plugins/" + plugin["name"],
        "Section": pkg.get("section", "wharf"),
        "Maintainer": MAINTAINER,
        "Architecture": pkg.get("architecture", "all"),
        "Installed-Size": installed,
        "Description": pkg["description"],
    }
    ctl_entries = [("./control", render_control(fields).encode(), 0o644, False)]
    for fn, data in sorted(scripts.items()):
        ctl_entries.append(("./" + fn, data, 0o644 if fn == "conffiles" else 0o755, False))
    data_entries = [("./", None, 0o755, True)]
    for d in sorted(dirs):
        data_entries.append(("./" + d, None, 0o755, True))
    for rel in sorted(files):
        data, mode = files[rel]
        data_entries.append(("./" + rel, data, mode, False))
    outer = [
        ("./debian-binary", b"2.0\n", 0o644, False),
        ("./data.tar.gz", _tar_bytes(data_entries, mtime), 0o644, False),
        ("./control.tar.gz", _tar_bytes(ctl_entries, mtime), 0o644, False),
    ]
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, "%s_%s_%s.ipk" % (pkg["name"], pkg["version"], fields["Architecture"]))
    with open(out, "wb") as f:
        f.write(_tar_bytes(outer, mtime))
    return out


# ------------------------------------------------------------------ ipk reading

def parse_control(text):
    fields = {}
    last = None
    for line in text.splitlines():
        if not line.strip():
            continue
        if line[0] in " \t" and last:
            fields[last] += "\n" + line[1:]
            continue
        key, _, value = line.partition(":")
        last = key.strip()
        fields[last] = value.strip()
    return fields


def read_ipk(path):
    """Return dict(control, scripts, data) for a tar.gz-style ipk."""
    with tarfile.open(path, "r:gz") as outer:
        names = {m.name.lstrip("./"): m for m in outer.getmembers() if m.isfile()}
        for need in ("debian-binary", "control.tar.gz", "data.tar.gz"):
            if need not in names:
                raise WharfError("%s: missing %s" % (path, need))
        if outer.extractfile(names["debian-binary"]).read().strip() != b"2.0":
            raise WharfError("%s: bad debian-binary" % path)
        ctl_blob = outer.extractfile(names["control.tar.gz"]).read()
        data_blob = outer.extractfile(names["data.tar.gz"]).read()
    control, scripts = None, {}
    with tarfile.open(fileobj=io.BytesIO(ctl_blob), mode="r:gz") as t:
        for m in t.getmembers():
            if not m.isfile():
                continue
            if "/" in m.name.lstrip("./"):
                raise WharfError("%s: control member has a path prefix: %s" % (path, m.name))
            body = t.extractfile(m).read()
            if m.name.lstrip("./") == "control":
                control = parse_control(body.decode("utf-8"))
            else:
                scripts[m.name.lstrip("./")] = body
    if control is None:
        raise WharfError("%s: control file missing" % path)
    data = []
    with tarfile.open(fileobj=io.BytesIO(data_blob), mode="r:gz") as t:
        for m in t.getmembers():
            data.append({"name": m.name, "dir": m.isdir(), "mode": m.mode, "size": m.size,
                         "uid": m.uid, "gid": m.gid})
    return {"control": control, "scripts": scripts, "data": data}


# ------------------------------------------------------------------- feed index

def make_feed(feed_dir):
    """Write Packages and Packages.gz for every .ipk in feed_dir. Returns stanza count."""
    stanzas = []
    for fn in sorted(os.listdir(feed_dir)):
        if not fn.endswith(".ipk"):
            continue
        path = os.path.join(feed_dir, fn)
        control = read_ipk(path)["control"]
        control = dict(control)
        control["Filename"] = fn
        control["Size"] = str(os.path.getsize(path))
        control["SHA256sum"] = sha256_file(path)
        keys = [k for k in CONTROL_ORDER if k in control]
        keys += [k for k in ("Filename", "Size", "SHA256sum")]
        out = []
        for k in keys:
            v = control[k]
            if k == "Description":
                first, *rest = v.split("\n")
                out.append("Description: " + first)
                out.extend(" " + (r if r.strip() else ".") for r in rest)
            else:
                out.append("%s: %s" % (k, v))
        stanzas.append("\n".join(out) + "\n")
    text = "\n".join(stanzas)
    with open(os.path.join(feed_dir, "Packages"), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    with open(os.path.join(feed_dir, "Packages.gz"), "wb") as f:
        f.write(gzip.compress(text.encode("utf-8"), 9, mtime=0))
    return len(stanzas)


# ------------------------------------------------------------- upstream fetching

def _open(url, token=None):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise WharfError("refusing non-https URL: %s" % url)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
    if token and parsed.hostname == "api.github.com":
        req.add_header("Authorization", "Bearer " + token)
    return urllib.request.urlopen(req, timeout=60)


def download(url, dest, sha256, size=None):
    """Download url to dest, failing (and removing the file) unless sha256 matches."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    h = hashlib.sha256()
    total = 0
    with _open(url) as r, open(tmp, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_DOWNLOAD:
                raise WharfError("download exceeds size limit: %s" % url)
            h.update(chunk)
            f.write(chunk)
    if h.hexdigest() != sha256 or (size is not None and total != size):
        os.remove(tmp)
        raise WharfError("checksum/size mismatch for %s (got sha256 %s, %d bytes)" % (url, h.hexdigest(), total))
    os.replace(tmp, dest)


def lock_path(plugin):
    return os.path.join(plugin["_dir"], "upstream.lock.json")


def load_lock(plugin):
    try:
        with open(lock_path(plugin), encoding="utf-8") as f:
            lock = json.load(f)
    except (OSError, ValueError) as e:
        raise WharfError("cannot read lock for %s: %s (run tools/fetch-upstream --update)" % (plugin["name"], e))
    for key in ("tag", "version", "asset", "url", "sha256", "size"):
        if key not in lock:
            raise WharfError("lock for %s lacks %s" % (plugin["name"], key))
    if not re.match(r"^[0-9a-f]{64}$", lock["sha256"]):
        raise WharfError("lock for %s has a bad sha256" % plugin["name"])
    return lock


def verify_upstream_ipk(plugin, path, lock=None):
    up = plugin["upstream"]
    control = read_ipk(path)["control"]
    if control.get("Package") != up["package"]:
        raise WharfError("%s: unexpected package %r" % (path, control.get("Package")))
    if control.get("Architecture") != "all":
        raise WharfError("%s: expected an architecture-independent package" % path)
    if lock and control.get("Version") != lock["version"]:
        raise WharfError("%s: version %s does not match lock %s" % (path, control.get("Version"), lock["version"]))
    return control


def fetch_locked(plugin, dest_dir):
    """Download the pinned upstream asset (verified against the lock) and return its path."""
    lock = load_lock(plugin)
    asset = os.path.basename(lock["asset"])
    if asset != lock["asset"] or not re.match(plugin["upstream"]["asset"], asset):
        raise WharfError("lock asset name %r does not match the plugin's asset pattern" % lock["asset"])
    prefix = "https://github.com/%s/releases/download/" % plugin["upstream"]["repo"]
    if not lock["url"].startswith(prefix):
        raise WharfError("lock url is not a release download of %s" % plugin["upstream"]["repo"])
    dest = os.path.join(dest_dir, asset)
    if not (os.path.isfile(dest) and sha256_file(dest) == lock["sha256"]):
        download(lock["url"], dest, lock["sha256"], lock["size"])
    verify_upstream_ipk(plugin, dest, lock)
    return dest


def latest_release(plugin):
    up = plugin["upstream"]
    url = "https://api.github.com/repos/%s/releases/latest" % up["repo"]
    with _open(url, os.environ.get("GITHUB_TOKEN")) as r:
        rel = json.load(r)
    rx = re.compile(up["asset"])
    matches = [a for a in rel.get("assets", []) if rx.match(a["name"])]
    if len(matches) != 1:
        raise WharfError("expected exactly one asset matching %s, found %d" % (up["asset"], len(matches)))
    a = matches[0]
    digest = a.get("digest") or ""
    if not digest.startswith("sha256:"):
        raise WharfError("release asset %s has no sha256 digest" % a["name"])
    return {"tag": rel["tag_name"], "asset": a["name"], "url": a["browser_download_url"],
            "sha256": digest[len("sha256:"):], "size": a["size"]}


def update_lock(plugin, write=True, tmp_dir=None):
    """Compare the lock with the latest upstream release. Returns (changed, old, new)."""
    new = latest_release(plugin)
    try:
        old = load_lock(plugin)
    except WharfError:
        old = None
    if old and old["sha256"] == new["sha256"]:
        return False, old["tag"], new["tag"]
    if write:
        import tempfile
        with tempfile.TemporaryDirectory(dir=tmp_dir) as td:
            path = os.path.join(td, new["asset"])
            download(new["url"], path, new["sha256"], new["size"])
            version = verify_upstream_ipk(plugin, path)["Version"]
        new["version"] = version
        ordered = {k: new[k] for k in ("tag", "version", "asset", "url", "sha256", "size")}
        with open(lock_path(plugin), "w", encoding="utf-8", newline="\n") as f:
            json.dump(ordered, f, indent=2)
            f.write("\n")
    return True, (old or {}).get("tag"), new["tag"]
