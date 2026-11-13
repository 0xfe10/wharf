#!/usr/bin/env python3
"""Check that every dependency of the wharf packages can be satisfied from GL.iNet's
own package feeds plus the wharf feed, by walking the dependency closure.

  check-glinet-deps.py [--ours site/feed/Packages] [--package wharf-glinet-openclash]

The default GL.iNet feeds are those of the Mudi 7 (GL-E5800) on firmware 4.10.0
(read from its /etc/opkg/distfeeds.conf). Packages already installed on the router
are not in any feed, so a missing package is reported as a warning to look at on the
device, not as proof that the install fails. Uses the network; Python stdlib only.
"""
import argparse
import gzip
import io
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import wharflib as w  # noqa: E402

GL_BASE = "https://fw.gl-inet.com/releases/sdx72_v1.2/rg650v"
GL_FEEDS = [
    GL_BASE + "/kmod-5.15.170/aarch64_cortex-a53/kmod",
    GL_BASE + "/packages/aarch64_cortex-a53/glinet",
    GL_BASE + "/packages/aarch64_cortex-a53/packages",
]
# Never feed packages: provided by the C library and the running kernel.
VIRTUAL = {"libc", "kernel"}
# Part of the GL.iNet firmware image itself, so installed on the router but listed in no
# feed (the installed gl-sdk4-ui-adguardhome etc. depend on it). Checked by hand on a
# Mudi 7 running 4.10.0 through `opkg list-installed`, not by this script.
FIRMWARE = {"gl-sdk4-ui-core"}


def read(url_or_path, gz=False):
    if re.match(r"^https?://", url_or_path):
        req = urllib.request.Request(url_or_path, headers={"User-Agent": w.UA})
        data = urllib.request.urlopen(req, timeout=90).read()
    else:
        with open(url_or_path, "rb") as f:
            data = f.read()
    return gzip.decompress(data).decode("utf-8") if gz else data.decode("utf-8")


def alternatives(depends):
    """'a (>= 1), b | c' -> [['a'], ['b', 'c']]"""
    out = []
    for part in (depends or "").split(","):
        names = [re.sub(r"\s*\(.*\)", "", alt).strip() for alt in part.split("|")]
        names = [n for n in names if n]
        if names:
            out.append(names)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ours", default="https://github.com/0xfe10/wharf/releases/latest/download/Packages")
    ap.add_argument("--package", default="wharf-glinet-openclash")
    ap.add_argument("--feed", action="append", help="GL.iNet feed base URL (repeatable)")
    args = ap.parse_args()

    available = {}
    for feed in args.feed or GL_FEEDS:
        for st in w.parse_packages(read(feed + "/Packages.gz", gz=True)):
            available[st["Package"]] = ("glinet", st)
            for prov in (st.get("Provides") or "").split(","):
                if prov.strip():
                    available.setdefault(re.sub(r"\s*\(.*\)", "", prov).strip(), ("glinet", st))
    for st in w.parse_packages(read(args.ours)):
        available[st["Package"]] = ("wharf", st)
    if args.package not in available:
        sys.exit("error: %s not found in the wharf feed" % args.package)

    seen, missing, assumed, queue = set(), [], set(), [args.package]
    while queue:
        name = queue.pop()
        if name in seen:
            continue
        seen.add(name)
        for alts in alternatives(available[name][1].get("Depends")):
            usable = [a for a in alts if a in available]
            if usable:
                queue.append(usable[0])
            elif set(alts) & VIRTUAL:
                pass
            elif set(alts) & FIRMWARE:
                assumed.add(" | ".join(alts))
            else:
                missing.append((name, " | ".join(alts)))
    print("closure of %s: %d packages" % (args.package, len(seen)))
    from_wharf = sorted(n for n in seen if available[n][0] == "wharf")
    print("from the wharf feed: " + ", ".join(from_wharf))
    if assumed:
        print("assumed to be part of the firmware (not in any feed): " + ", ".join(sorted(assumed)))
    for needed_by, dep in missing:
        print("UNRESOLVED %s (needed by %s)" % (dep, needed_by), file=sys.stderr)
    if missing:
        sys.exit(1)
    print("all dependencies are available from the GL.iNet feeds or the wharf feed")


if __name__ == "__main__":
    main()
