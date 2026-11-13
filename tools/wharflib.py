"""Shared helpers: plugin spec validation, ipk reading (for tests/verification) and
upstream fetching. Packaging itself is done by tools/build-pkg and tools/make-feed (sh)."""
import hashlib
import io
import json
import os
import re
import tarfile
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9.+_-]*$")
VERSION_RE = re.compile(r"^[0-9][A-Za-z0-9.+~_-]*$")
MAX_DOWNLOAD = 200 * 1024 * 1024
UA = "wharf-build/1.0 (+https://github.com/0xfe10/wharf)"


class WharfError(Exception):
    pass


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


# ------------------------------------------------------ version-bump verification

def parse_packages(text):
    """Parse a Packages index into a list of control dicts."""
    out = []
    for block in re.split(r"\n\n+", text.strip()):
        st = parse_control(block) if block.strip() else {}
        if "Package" in st:
            out.append(st)
    return out


def content_digest(path):
    """sha256 over everything that matters in an ipk (control file and scripts, every
    data entry's name/type/mode/content) but not timestamps, so two builds of the
    same sources always agree even when SOURCE_DATE_EPOCH differs."""
    h = hashlib.sha256()
    with tarfile.open(path, "r:gz") as outer:
        members = {m.name.lstrip("./"): m for m in outer.getmembers() if m.isfile()}
        blobs = {n: outer.extractfile(members[n]).read() for n in ("control.tar.gz", "data.tar.gz")}
    for label in ("control.tar.gz", "data.tar.gz"):
        h.update(label.encode() + b"\0")
        with tarfile.open(fileobj=io.BytesIO(blobs[label]), mode="r:gz") as t:
            for m in sorted(t.getmembers(), key=lambda m: m.name):
                body = t.extractfile(m).read() if m.isfile() else b""
                h.update(("%s|%s|%o|%d|" % (m.name, m.type.decode(), m.mode & 0o7777, len(body))).encode())
                h.update(hashlib.sha256(body).digest())
    return h.hexdigest()


def check_package_versions(built_dir, own_names, published_index, fetch_ipk):
    """A package name+version that is already published must have identical content.

    Returns (problems, notes). fetch_ipk(filename) must return a local path to the
    published ipk."""
    published = {(st["Package"], st["Version"]): st for st in parse_packages(published_index)}
    problems, notes = [], []
    for fn in sorted(os.listdir(built_dir)):
        if not fn.endswith(".ipk"):
            continue
        path = os.path.join(built_dir, fn)
        ctl = read_ipk(path)["control"]
        name, version = ctl["Package"], ctl["Version"]
        if name not in own_names:
            continue
        st = published.get((name, version))
        if st is None:
            notes.append("%s %s: not published yet" % (name, version))
            continue
        if content_digest(path) != content_digest(fetch_ipk(st["Filename"])):
            problems.append("%s %s is already published with different content: bump its version "
                            "in plugins/*/plugin.json" % (name, version))
        else:
            notes.append("%s %s: unchanged" % (name, version))
    return problems, notes


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
