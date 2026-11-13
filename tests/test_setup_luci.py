"""Runs the router-side setup-luci script against stub commands (pidof, netstat,
uci, init_luci.sh), so the wait-for-opkg / retry logic is exercised without a router."""
import os
import subprocess
import tempfile
import threading
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "plugins", "openclash", "glinet", "root",
                      "usr", "libexec", "wharf-openclash", "setup-luci")

STUBS = {
    "pidof": '#!/bin/sh\n[ -e "$T/opkg_busy" ]\n',
    "netstat": '#!/bin/sh\n[ -e "$T/listening" ] && echo "tcp 0 0 0.0.0.0:8080 0.0.0.0:* LISTEN"\nexit 0\n',
    "uci": '#!/bin/sh\n[ "$3" = "uhttpd.main.inited" ] && [ -e "$T/inited" ] && echo 1 && exit 0\nexit 1\n',
    # init_luci.sh stub: records calls; succeeds from attempt $SUCCEED_ON on (0 = never)
    "init_luci.sh": ('#!/bin/sh\nn=$(cat "$T/calls" 2>/dev/null || echo 0); n=$((n+1)); echo $n > "$T/calls"\n'
                     '[ -e "$T/opkg_busy" ] && echo busy >> "$T/ran_while_busy"\n'
                     '[ "$SUCCEED_ON" -gt 0 ] && [ "$n" -ge "$SUCCEED_ON" ] && touch "$T/inited" "$T/listening"\nexit 0\n'),
}


class SetupLuci(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.t = self._td.name
        self.bin = os.path.join(self.t, "bin")
        os.makedirs(self.bin)
        os.makedirs(os.path.join(self.t, "luci"))
        for name, body in STUBS.items():
            path = os.path.join(self.bin, name)
            with open(path, "w") as f:
                f.write(body)
            os.chmod(path, 0o755)

    def tearDown(self):
        self._td.cleanup()

    def run_script(self, succeed_on=1, **extra):
        env = dict(os.environ, T=self.t, SUCCEED_ON=str(succeed_on),
                   PATH=self.bin + os.pathsep + os.environ["PATH"],
                   WHARF_STATE_DIR=self.t, WHARF_INIT_LUCI=os.path.join(self.bin, "init_luci.sh"),
                   WHARF_LUCI_LIB=os.path.join(self.t, "luci"), WHARF_LUCI_LOCK=os.path.join(self.t, "luci.lock"),
                   WHARF_SETTLE="0", WHARF_POLL="1", WHARF_RETRY_PAUSE="0", WHARF_UP_TRIES="2",
                   WHARF_WAIT_OPKG="20")
        env.update({k: str(v) for k, v in extra.items()})
        return subprocess.run(["sh", SCRIPT], env=env, capture_output=True, text=True, timeout=60)

    def touch(self, name):
        open(os.path.join(self.t, name), "w").close()

    def status(self):
        with open(os.path.join(self.t, "wharf-openclash-luci.status")) as f:
            return f.read().strip()

    def calls(self):
        try:
            with open(os.path.join(self.t, "calls")) as f:
                return int(f.read())
        except OSError:
            return 0

    def test_already_up_does_nothing(self):
        self.touch("inited"); self.touch("listening")
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.status(), "ok")
        self.assertEqual(self.calls(), 0)

    def test_waits_for_opkg_to_finish(self):
        self.touch("opkg_busy")
        threading.Timer(3, lambda: os.remove(os.path.join(self.t, "opkg_busy"))).start()
        start = time.time()
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.status(), "ok")
        self.assertGreaterEqual(time.time() - start, 2.5)
        self.assertFalse(os.path.exists(os.path.join(self.t, "ran_while_busy")))

    def test_retries_until_it_works(self):
        r = self.run_script(succeed_on=2)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.status(), "ok")
        self.assertEqual(self.calls(), 2)

    def test_gives_up_after_attempts(self):
        r = self.run_script(succeed_on=0, WHARF_ATTEMPTS=2)
        self.assertEqual(r.returncode, 1)
        self.assertTrue(self.status().startswith("failed: LuCI did not come up"))
        self.assertEqual(self.calls(), 2)

    def test_opkg_stuck_times_out_without_running_init(self):
        self.touch("opkg_busy")
        r = self.run_script(WHARF_WAIT_OPKG=2)
        self.assertEqual(r.returncode, 1)
        self.assertIn("opkg stayed busy", self.status())
        self.assertEqual(self.calls(), 0)

    def test_second_instance_exits_quietly(self):
        os.makedirs(os.path.join(self.t, "wharf-openclash-setup.lock"))
        r = self.run_script()
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.calls(), 0)
        self.assertFalse(os.path.exists(os.path.join(self.t, "wharf-openclash-luci.status")))

    def test_missing_init_script(self):
        r = self.run_script(WHARF_INIT_LUCI=os.path.join(self.t, "nope.sh"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("not found", self.status())


if __name__ == "__main__":
    unittest.main()
