"""Runs the router-side heal-dns script against stub commands (a stateful uci, netstat,
logger and init scripts), so the cleanup rules are exercised without a router."""
import json
import os
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GLINET = os.path.join(HERE, "..", "plugins", "openclash", "glinet")
SCRIPT = os.path.join(GLINET, "root", "usr", "libexec", "wharf-openclash", "heal-dns")
INITSCRIPT = os.path.join(GLINET, "root", "etc", "init.d", "wharf-openclash-guard")

# Minimal stateful uci: get / set / add_list / del_list / delete / commit on "a.b.c" keys.
# Values are lists; `get` joins them with spaces like the real uci does.
UCI = r'''#!/usr/bin/env python3
import json, os, sys
state_file = os.path.join(os.environ["T"], "uci.json")
state = json.load(open(state_file))
args = [a for a in sys.argv[1:] if a != "-q"]
cmd, rest = args[0], args[1:]
def save():
    json.dump(state, open(state_file, "w"))
if cmd == "get":
    key = rest[0]
    if key in state:
        print(" ".join(state[key])); sys.exit(0)
    if any(k.startswith(key + ".") for k in state):
        print(key.split(".")[0]); sys.exit(0)
    sys.exit(1)
elif cmd == "set":
    key, val = rest[0].split("=", 1)
    state[key] = [val]; save()
elif cmd == "add_list":
    key, val = rest[0].split("=", 1)
    state.setdefault(key, []).append(val); save()
elif cmd == "del_list":
    key, val = rest[0].split("=", 1)
    if val in state.get(key, []):
        state[key].remove(val)
        if not state[key]:
            del state[key]
    save()
elif cmd == "delete":
    key = rest[0]
    for k in [k for k in state if k == key or k.startswith(key + ".")]:
        del state[k]
    save()
elif cmd == "commit":
    open(os.path.join(os.environ["T"], "commits"), "a").write(rest[0] + "\n")
else:
    sys.exit(2)
'''

STUBS = {
    "uci": UCI,
    "netstat": '#!/bin/sh\n[ -e "$T/listening" ] && cat "$T/listening"\nexit 0\n',
    "logger": '#!/bin/sh\necho "$*" >> "$T/syslog"\n',
}

D = "dhcp.@dnsmasq[0]."


class HealDns(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.t = self._td.name
        self.bin = os.path.join(self.t, "bin")
        self.initd = os.path.join(self.t, "init.d")
        self.dnsmasq_d = os.path.join(self.t, "dnsmasq.d")
        for d in (self.bin, self.initd, self.dnsmasq_d):
            os.makedirs(d)
        for name, body in STUBS.items():
            self._exe(os.path.join(self.bin, name), body)
        for name in ("dnsmasq", "firewall"):
            self._exe(os.path.join(self.initd, name), '#!/bin/sh\necho "%s $1" >> "$T/initd_calls"\n' % name)
        with open(os.path.join(self.t, "resolv.auto"), "w") as f:
            f.write("nameserver 192.0.2.53\n")
        self.state = {}
        # the state OpenClash leaves behind: forwarder to itself, noresolv, its snippets and include
        self.leftover()

    def tearDown(self):
        self._td.cleanup()

    @staticmethod
    def _exe(path, body):
        with open(path, "w") as f:
            f.write(body)
        os.chmod(path, 0o755)

    def leftover(self):
        self.state.update({
            D + "server": ["127.0.0.1#7874"],
            D + "noresolv": ["1"],
            D + "localuse": ["1"],
            D + "cachesize": ["0"],
            D + "filter_aaaa": ["0"],
            "firewall.openclash": ["include"],
            "firewall.openclash.path": ["/var/etc/openclash.include"],
            "openclash.config.redirect_dns": ["1"],
            "openclash.config.cachesize_dns": ["1"],
            "openclash.config.dnsmasq_cachesize": ["150"],
            "openclash.config.dnsmasq_noresolv": ["0"],
        })
        for n in ("dnsmasq_openclash_custom_domain.conf", "dnsmasq_openclash_chnroute_pass.conf", "other.conf"):
            open(os.path.join(self.dnsmasq_d, n), "w").close()

    def run_script(self, mode="boot"):
        with open(os.path.join(self.t, "uci.json"), "w") as f:
            json.dump(self.state, f)
        env = dict(os.environ, T=self.t, PATH=self.bin + os.pathsep + os.environ["PATH"],
                   WHARF_INITD=self.initd, WHARF_DNSMASQ_D=self.dnsmasq_d,
                   WHARF_GUARD_LOG=os.path.join(self.t, "guard.log"),
                   WHARF_RESOLV_CANDIDATES=os.path.join(self.t, "nope") + " " + os.path.join(self.t, "resolv.auto"))
        r = subprocess.run(["sh", SCRIPT, mode], env=env, capture_output=True, text=True, timeout=30)
        with open(os.path.join(self.t, "uci.json")) as f:
            self.after = json.load(f)
        return r

    def openclash_installed(self):
        self._exe(os.path.join(self.initd, "openclash"), "#!/bin/sh\n")

    def calls(self):
        try:
            with open(os.path.join(self.t, "initd_calls")) as f:
                return f.read().split("\n")[:-1]
        except OSError:
            return []

    def test_cleans_leftovers_when_openclash_is_gone(self):
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn(D + "server", self.after)
        self.assertEqual(self.after[D + "noresolv"], ["0"])
        self.assertEqual(self.after[D + "resolvfile"], [os.path.join(self.t, "resolv.auto")])
        self.assertEqual(self.after[D + "cachesize"], ["150"])          # OpenClash had saved it
        self.assertEqual(self.after["openclash.config.redirect_dns"], ["0"])
        self.assertNotIn("firewall.openclash", self.after)
        self.assertEqual(sorted(os.listdir(self.dnsmasq_d)), ["other.conf"])
        with open(os.path.join(self.t, "guard.log")) as f:
            self.assertIn("cleaning up", f.read())
        with open(os.path.join(self.t, "syslog")) as f:
            self.assertIn("wharf-openclash-guard", f.read())

    def test_boot_does_not_restart_but_run_does(self):
        self.run_script("boot")
        self.assertEqual(self.calls(), [])
        self.leftover()
        self.run_script("run")
        self.assertEqual(self.calls(), ["dnsmasq restart", "firewall reload"])

    def test_nothing_happens_while_openclash_is_installed(self):
        self.openclash_installed()
        before = dict(self.state)
        self.run_script()
        self.assertEqual(self.after, before)
        self.assertEqual(len(os.listdir(self.dnsmasq_d)), 3)

    def test_nothing_happens_while_something_listens(self):
        with open(os.path.join(self.t, "listening"), "w") as f:
            f.write("tcp 0 0 127.0.0.1:7874 0.0.0.0:* LISTEN\n")
        before = dict(self.state)
        self.run_script()
        self.assertEqual(self.after, before)

    def test_foreign_dns_settings_are_not_touched(self):
        # a forwarder to some other local resolver is not OpenClash's
        self.state[D + "server"] = ["127.0.0.1#5353", "/corp.example/10.0.0.1"]
        self.state[D + "noresolv"] = ["1"]
        before = dict(self.state)
        self.run_script()
        self.assertEqual(self.after, before)
        self.assertEqual(len(os.listdir(self.dnsmasq_d)), 3)

    def test_other_servers_and_foreign_firewall_include_survive(self):
        self.state[D + "server"] = ["/corp.example/10.0.0.1", "127.0.0.1#7874"]
        self.state["firewall.openclash.path"] = ["/etc/something-else.include"]
        del self.state["openclash.config.dnsmasq_noresolv"]               # original value unknown
        self.run_script()
        self.assertEqual(self.after[D + "server"], ["/corp.example/10.0.0.1"])
        self.assertEqual(self.after[D + "noresolv"], ["1"])             # an upstream remains: leave it
        self.assertIn("firewall.openclash", self.after)

    def test_saved_noresolv_off_is_restored_even_with_servers(self):
        # OpenClash saved noresolv=0: it was off before OpenClash set it to 1
        self.state[D + "server"] = ["/corp.example/10.0.0.1", "127.0.0.1#7874"]
        self.run_script()
        self.assertEqual(self.after[D + "noresolv"], ["0"])
        self.assertEqual(self.after[D + "server"], ["/corp.example/10.0.0.1"])

    def test_saved_upstream_servers_are_restored(self):
        self.state["openclash.config.dnsmasq_server"] = ["9.9.9.9", "1.1.1.1"]
        self.state["openclash.config.dnsmasq_noresolv"] = ["1"]
        self.run_script()
        self.assertEqual(self.after[D + "server"], ["9.9.9.9", "1.1.1.1"])
        self.assertEqual(self.after[D + "noresolv"], ["1"])
        self.assertNotIn("openclash.config.dnsmasq_server", self.after)

    def test_custom_dns_port_from_openclash_config(self):
        self.state["openclash.config.dns_port"] = ["1053"]
        self.state[D + "server"] = ["127.0.0.1#1053"]
        self.run_script()
        self.assertNotIn(D + "server", self.after)

    def test_second_run_changes_nothing(self):
        self.run_script()
        first = dict(self.after)
        self.state = first
        self.run_script()
        self.assertEqual(self.after, first)

    def test_without_openclash_config_it_still_repairs_dns(self):
        # /etc/config/openclash missing: no saved values, defaults apply
        for k in [k for k in self.state if k.startswith("openclash.")]:
            del self.state[k]
        self.run_script()
        self.assertNotIn(D + "server", self.after)
        self.assertEqual(self.after[D + "noresolv"], ["0"])

    def test_init_script_runs_heal_before_dnsmasq(self):
        with open(INITSCRIPT) as f:
            text = f.read()
        self.assertTrue(text.startswith("#!/bin/sh /etc/rc.common"))
        self.assertIn("START=18", text)              # dnsmasq is START=19
        self.assertIn("heal-dns boot", text)
        self.assertEqual(subprocess.run(["sh", "-n", INITSCRIPT]).returncode, 0)


if __name__ == "__main__":
    unittest.main()
