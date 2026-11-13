#!/bin/sh
# Verifies the PUBLISHED release the way a router would consume it, inside an upstream
# OpenWrt container with signature checking on: the signature of Packages is checked with the
# public key from this repository, and opkg verifies size and sha256 of every package it
# downloads against that signed index.
#
# The files are fetched from the public URL on the host (curl follows GitHub's redirects) and
# served to the container locally, because CI containers could not reach github.com.
# NOT covered: opkg's own https client (uclient-fetch) following GitHub's redirects. That is
# only checked on a router: `opkg update` against the real URL (see docs/using-the-feed.md).
#   tests/opkg-published.sh [feed-url]     needs docker, curl, python3
set -eu
here=$(cd "$(dirname "$0")" && pwd)
url=${1:-https://github.com/0xfe10/wharf/releases/latest/download}
image=${OPENWRT_IMAGE:-openwrt/rootfs:x86-64-23.05.4}
port=${PORT:-8098}

work=$(mktemp -d)
srv=
trap 'kill $srv 2>/dev/null || true; rm -rf "$work"' EXIT
mkdir -p "$work/serve"

get() { curl -fsSL --retry 3 --connect-timeout 20 -o "$work/serve/$1" "$url/$1"; }
for f in Packages Packages.gz Packages.sig wharf-usign.pub; do get "$f"; done
# every package the index lists
for f in $(sed -n 's/^Filename: //p' "$work/serve/Packages"); do get "$f"; done
echo "fetched from $url:"; ls -l "$work/serve"
cmp "$work/serve/wharf-usign.pub" "$here/../keys/wharf-usign.pub" || { echo "release public key differs from keys/wharf-usign.pub"; exit 1; }

python3 -m http.server "$port" --bind 127.0.0.1 --directory "$work/serve" >/dev/null 2>&1 &
srv=$!
sleep 1

docker run --rm --network host -e PORT="$port" -v "$here/../keys/wharf-usign.pub:/tmp/wharf-usign.pub:ro" "$image" sh -eu -c '
mkdir -p /var/lock /var/run /tmp/dl
. /etc/openwrt_release
printf "arch all 100\narch noarch 100\narch %s 200\n" "$DISTRIB_ARCH" >> /etc/opkg.conf
grep -q "^option check_signature" /etc/opkg.conf || echo "option check_signature" >> /etc/opkg.conf
fp=$(usign -F -p /tmp/wharf-usign.pub)
echo "key fingerprint: $fp"
cp /tmp/wharf-usign.pub /etc/opkg/keys/$fp
echo "src/gz wharf http://127.0.0.1:$PORT" >> /etc/opkg/customfeeds.conf

out=$(opkg update 2>&1) || true
echo "$out" | grep -i "wharf" || true
echo "$out" | grep -qi "signature check failed" && { echo "signature check failed"; exit 1; }
echo "$out" | grep -q "Updated list of available packages in /var/opkg-lists/wharf" || { echo "wharf feed was not updated"; echo "$out"; exit 1; }
for p in luci-app-openclash wharf-openclash wharf-glinet-openclash; do
  opkg list | grep -q "^$p - " || { echo "missing from feed: $p"; exit 1; }
done
opkg info wharf-glinet-openclash | grep -E "^(Package|Version|Depends):"

cd /tmp/dl
# The GL.iNet adapter must be refused on a system without GL.iNet firmware
# (gl-sdk4-ui-core is part of that firmware), so it cannot be installed there by mistake.
if err=$(opkg download wharf-glinet-openclash 2>&1); then echo "GL.iNet adapter was accepted on plain OpenWrt"; exit 1; fi
echo "$err" | grep -q "cannot find dependency gl-sdk4-ui-core" || { echo "unexpected error:"; echo "$err"; exit 1; }
echo "GL.iNet adapter correctly refused without gl-sdk4-ui-core"
opkg download wharf-openclash
opkg download luci-app-openclash
ls -l /tmp/dl
test "$(wc -c < /tmp/dl/luci-app-openclash_*_all.ipk)" -gt 1000000
echo "published feed OK"
'
