import gzip
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import wharflib as w  # noqa: E402

EPOCH = 1700000000


def make_plugin(tmp, extra_pkg=None):
    pdir = os.path.join(tmp, "demo")
    os.makedirs(os.path.join(pdir, "t", "root", "www", "views"))
    os.makedirs(os.path.join(pdir, "t", "CONTROL"))
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
    return w.load_plugin(pdir)


class BuildTests(unittest.TestCase):
    def test_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = make_plugin(tmp)
            path = w.build_package(plugin, plugin["packages"][0], os.path.join(tmp, "out"), EPOCH)
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
            self.assertTrue(all(n == "." or n.startswith("./") for n in names))
            self.assertTrue(all(d["uid"] == 0 and d["gid"] == 0 for d in info["data"]))

    def test_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = make_plugin(tmp)
            a = w.build_package(plugin, plugin["packages"][0], os.path.join(tmp, "a"), EPOCH)
            b = w.build_package(plugin, plugin["packages"][0], os.path.join(tmp, "b"), EPOCH)
            self.assertEqual(w.sha256_file(a), w.sha256_file(b))

    def test_feed_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = make_plugin(tmp)
            out = os.path.join(tmp, "feed")
            ipk = w.build_package(plugin, plugin["packages"][0], out, EPOCH)
            self.assertEqual(w.make_feed(out), 1)
            text = open(os.path.join(out, "Packages")).read()
            stanza = w.parse_control(text)
            self.assertEqual(stanza["Filename"], os.path.basename(ipk))
            self.assertEqual(int(stanza["Size"]), os.path.getsize(ipk))
            self.assertEqual(stanza["SHA256sum"], w.sha256_file(ipk))
            self.assertEqual(gzip.open(os.path.join(out, "Packages.gz"), "rt").read(), text)

    def test_rejects_bad_specs(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(w.WharfError):
                make_plugin(tmp, {"version": "v1"})
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(w.WharfError):
                make_plugin(tmp, {"dir": "../x"})

    def test_missing_gzip_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = make_plugin(tmp, {"gzip": ["nope.js"]})
            with self.assertRaises(w.WharfError):
                w.build_package(plugin, plugin["packages"][0], os.path.join(tmp, "o"), EPOCH)


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

    def test_glinet_package_only_touches_allowed_paths(self):
        allowed = ("./usr/share/oui/menu.d/", "./www/views/", "./lib/upgrade/keep.d/")
        plugin = w.load_plugin(os.path.join(ROOT, "plugins", "openclash"))
        with tempfile.TemporaryDirectory() as tmp:
            for pkg in plugin["packages"]:
                path = w.build_package(plugin, pkg, tmp, EPOCH)
                info = w.read_ipk(path)
                for d in info["data"]:
                    if d["dir"]:
                        continue
                    self.assertTrue(d["name"].startswith(allowed), d["name"])
                    self.assertNotIn("..", d["name"])
                if pkg["name"] == "wharf-glinet-openclash":
                    names = [d["name"] for d in info["data"]]
                    self.assertIn("./www/views/gl-sdk4-ui-openclash.common.js.gz", names)
                    self.assertIn("./usr/share/oui/menu.d/wharf-openclash.json", names)
                    self.assertIn("gl-sdk4-ui-core", info["control"]["Depends"])
                    self.assertIn("postinst", info["scripts"])

    def test_menu_json_and_view_pairing(self):
        base = os.path.join(ROOT, "plugins", "openclash", "glinet", "root")
        with open(os.path.join(base, "usr/share/oui/menu.d/wharf-openclash.json")) as f:
            menu = json.load(f)
        self.assertTrue(os.path.isfile(os.path.join(
            base, "www/views/gl-sdk4-ui-%s.common.js" % menu["view"])))
        self.assertEqual(menu["parent"], "applications")

    def test_cli_build_all_offline_pieces(self):
        # build-ipk for the plugin's own packages (no network needed)
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build-ipk"),
                                "--plugin", "openclash", "--out", tmp],
                               capture_output=True, text=True, env=dict(os.environ, SOURCE_DATE_EPOCH=str(EPOCH)))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(os.path.isfile(os.path.join(tmp, "glinet", "wharf-glinet-openclash_1.0.0-1_all.ipk")))
            self.assertTrue(os.path.isfile(os.path.join(tmp, "generic", "wharf-openclash_1.0.0-1_all.ipk")))


if __name__ == "__main__":
    unittest.main()
