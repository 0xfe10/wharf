import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import wharflib as w  # noqa: E402

EPOCH = "1700000000"


def has_gnu_tar():
    try:
        out = subprocess.run(["tar", "--version"], capture_output=True, text=True).stdout
    except OSError:
        return False
    return "GNU tar" in out and shutil.which("jq") is not None


NEEDS_GNU = unittest.skipUnless(has_gnu_tar(), "packaging needs GNU tar and jq (runs in CI)")


def tool(name, *args):
    env = dict(os.environ, SOURCE_DATE_EPOCH=EPOCH)
    return subprocess.run([os.path.join(ROOT, "tools", name)] + list(args),
                          capture_output=True, text=True, env=env)


def make_plugin(tmp, extra_pkg=None):
    pdir = os.path.join(tmp, "demo")
    os.makedirs(os.path.join(pdir, "t", "root", "www", "views"), exist_ok=True)
    os.makedirs(os.path.join(pdir, "t", "CONTROL"), exist_ok=True)
    with open(os.path.join(pdir, "t", "root", "www", "views", "v.js"), "w") as f:
        f.write("module.exports = {}\n")
    with open(os.path.join(pdir, "t", "CONTROL", "postinst"), "w") as f:
        f.write("#!/bin/sh\nexit 0\n")
    pkg = {"name": "wharf-demo", "version": "1.0.0-1", "feed": "generic", "dir": "t",
           "gzip": ["www/views/v.js"], "depends": ["a", "b"],
           "description": "Demo\nSecond line"}
    pkg.update(extra_pkg or {})
    with open(os.path.join(pdir, "plugin.json"), "w") as f:
        json.dump({"name": "demo", "packages": [pkg]}, f)
    return pdir


@NEEDS_GNU
class BuildTests(unittest.TestCase):
    def build(self, tmp, out="out", **extra):
        pdir = make_plugin(tmp, extra or None)
        r = tool("build-pkg", pdir, "wharf-demo", os.path.join(tmp, out))
        return pdir, r

    def test_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, r = self.build(tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            path = r.stdout.strip()
            self.assertTrue(path.endswith("wharf-demo_1.0.0-1_all.ipk"))
            info = w.read_ipk(path)
            c = info["control"]
            self.assertEqual(c["Package"], "wharf-demo")
            self.assertEqual(c["Depends"], "a, b")
            self.assertEqual(c["Architecture"], "all")
            self.assertEqual(c["Description"], "Demo\nSecond line")
            self.assertIn("postinst", info["scripts"])
            names = [d["name"] for d in info["data"]]
            self.assertIn("./www/views/v.js.gz", names)
            self.assertNotIn("./www/views/v.js", names)
            self.assertTrue(all(n in (".", "./") or n.startswith("./") for n in names))
            self.assertTrue(all(d["uid"] == 0 and d["gid"] == 0 for d in info["data"]))

    def test_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, a = self.build(tmp, "a")
            _, b = self.build(tmp, "b")
            self.assertEqual(w.sha256_file(a.stdout.strip()), w.sha256_file(b.stdout.strip()))

    def test_feed_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, r = self.build(tmp, "feed")
            ipk = r.stdout.strip()
            m = tool("make-feed", os.path.join(tmp, "feed"))
            self.assertEqual(m.returncode, 0, m.stderr)
            text = open(os.path.join(tmp, "feed", "Packages")).read()
            stanza = w.parse_control(text)
            self.assertEqual(stanza["Package"], "wharf-demo")
            self.assertEqual(stanza["Filename"], os.path.basename(ipk))
            self.assertEqual(int(stanza["Size"]), os.path.getsize(ipk))
            self.assertEqual(stanza["SHA256sum"], w.sha256_file(ipk))
            self.assertEqual(gzip.open(os.path.join(tmp, "feed", "Packages.gz"), "rt").read(), text)

    def test_missing_gzip_entry_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, r = self.build(tmp, gzip=["nope.js"])
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("not found", r.stderr)

    def test_unsafe_path_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, r = self.build(tmp, gzip=["../x"])
            self.assertNotEqual(r.returncode, 0)

    def test_unknown_package_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = make_plugin(tmp)
            r = tool("build-pkg", pdir, "nope", os.path.join(tmp, "o"))
            self.assertNotEqual(r.returncode, 0)


class SpecTests(unittest.TestCase):
    def test_rejects_bad_specs(self):
        for extra in ({"version": "v1"}, {"dir": "../x"}, {"gzip": ["/etc/passwd"]}):
            with tempfile.TemporaryDirectory() as tmp:
                pdir = make_plugin(tmp, extra)
                with self.assertRaises(w.WharfError, msg=str(extra)):
                    w.load_plugin(pdir)


class RepoTests(unittest.TestCase):
    def test_plugins_load_and_locks_valid(self):
        plugins = w.iter_plugins()
        self.assertTrue(plugins)
        for p in plugins:
            if p.get("upstream"):
                lock = w.load_lock(p)
                self.assertTrue(lock["url"].startswith(
                    "https://github.com/%s/releases/download/" % p["upstream"]["repo"]))
                self.assertRegex(lock["asset"], p["upstream"]["asset"])

    def test_scripts_have_valid_shell_syntax(self):
        base = os.path.join(ROOT, "plugins", "openclash", "glinet")
        scripts = [os.path.join(base, "CONTROL", n) for n in sorted(os.listdir(os.path.join(base, "CONTROL")))]
        scripts.append(os.path.join(base, "root", "usr", "libexec", "wharf-openclash", "setup-luci"))
        scripts += [os.path.join(ROOT, "tools", n) for n in ("build-pkg", "build-ipk", "make-feed", "build-usign", "sign-feed")]
        scripts.append(os.path.join(ROOT, "tests", "opkg-install.sh"))
        for s in scripts:
            r = subprocess.run(["sh", "-n", s], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, "%s: %s" % (s, r.stderr))

    def test_menu_json_and_view_pairing(self):
        base = os.path.join(ROOT, "plugins", "openclash", "glinet", "root")
        with open(os.path.join(base, "usr/share/oui/menu.d/wharf-openclash.json")) as f:
            menu = json.load(f)
        self.assertTrue(os.path.isfile(os.path.join(base, "www/views/gl-sdk4-ui-%s.common.js" % menu["view"])))
        self.assertEqual(menu["parent"], "applications")

    def test_glinet_sources_stay_in_allowed_paths(self):
        # Static check of the source tree (works on any OS): the adapter may only
        # install under these paths so it can never overwrite firmware files.
        allowed = ("usr/share/oui/menu.d/", "www/views/", "lib/upgrade/keep.d/", "usr/libexec/wharf-openclash/")
        base = os.path.join(ROOT, "plugins", "openclash", "glinet", "root")
        for cur, _, files in os.walk(base):
            for fn in files:
                rel = os.path.relpath(os.path.join(cur, fn), base).replace(os.sep, "/")
                self.assertTrue(rel.startswith(allowed), rel)
                self.assertFalse(os.path.islink(os.path.join(cur, fn)), rel)

    @NEEDS_GNU
    def test_built_glinet_package_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = tool("build-ipk", "openclash", tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            info = w.read_ipk(os.path.join(tmp, "glinet", "wharf-openclash-glinet_1.1.0-1_all.ipk"))
            names = [d["name"] for d in info["data"]]
            for want in ("./www/views/gl-sdk4-ui-openclash.common.js.gz",
                         "./usr/share/oui/menu.d/wharf-openclash.json",
                         "./usr/libexec/wharf-openclash/setup-luci",
                         "./lib/upgrade/keep.d/wharf-openclash"):
                self.assertIn(want, names)
            mode = {d["name"]: d["mode"] for d in info["data"]}
            self.assertEqual(mode["./usr/libexec/wharf-openclash/setup-luci"], 0o755)
            self.assertIn("gl-sdk4-ui-core", info["control"]["Depends"])
            self.assertIn("postinst", info["scripts"])


@NEEDS_GNU
class VersionCheckTests(unittest.TestCase):
    def _published_and_built(self, tmp, change_content, bump):
        pdir = make_plugin(tmp)
        pub = os.path.join(tmp, "published")
        r = tool("build-pkg", pdir, "wharf-demo", pub)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(tool("make-feed", pub).returncode, 0)
        if change_content:
            with open(os.path.join(pdir, "t", "root", "www", "views", "v.js"), "w") as f:
                f.write("module.exports = { changed: true }\n")
        if bump:
            spec = os.path.join(pdir, "plugin.json")
            with open(spec) as f:
                data = json.load(f)
            data["packages"][0]["version"] = "1.0.1-1"
            with open(spec, "w") as f:
                json.dump(data, f)
        built = os.path.join(tmp, "built")
        env = dict(os.environ, SOURCE_DATE_EPOCH="1800000000")  # different timestamps on purpose
        r = subprocess.run([os.path.join(ROOT, "tools", "build-pkg"), pdir, "wharf-demo", built],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return pub, built

    def _check(self, pub, built):
        # the check only looks at packages named in plugins/*/plugin.json, so run it as a library
        names = {"wharf-demo"}
        with open(os.path.join(pub, "Packages")) as f:
            index = f.read()
        return w.check_package_versions(built, names, index, lambda fn: os.path.join(pub, fn))

    def test_same_content_new_timestamps_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            pub, built = self._published_and_built(tmp, change_content=False, bump=False)
            problems, notes = self._check(pub, built)
            self.assertEqual(problems, [])
            self.assertTrue(any("unchanged" in n for n in notes))

    def test_changed_content_same_version_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            pub, built = self._published_and_built(tmp, change_content=True, bump=False)
            problems, _ = self._check(pub, built)
            self.assertEqual(len(problems), 1)
            self.assertIn("bump", problems[0])

    def test_changed_content_with_bump_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            pub, built = self._published_and_built(tmp, change_content=True, bump=True)
            problems, notes = self._check(pub, built)
            self.assertEqual(problems, [])
            self.assertTrue(any("not published yet" in n for n in notes))


if __name__ == "__main__":
    unittest.main()
