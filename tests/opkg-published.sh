#!/bin/sh
# Uses the PUBLISHED feed the way a router does, inside an upstream OpenWrt container:
# https download through GitHub's redirects, signature verification with the public key
# from this repository, package download with checksum verification by opkg.
# Needs docker. Run it after a release.
#   tests/opkg-published.sh [feed-url]
set -eu
here=$(cd "$(dirname "$0")" && pwd)
url=${1:-https://github.com/0xfe10/wharf/releases/latest/download}
image=${OPENWRT_IMAGE:-openwrt/rootfs:x86-64-23.05.4}

docker run --rm --network host -e URL="$url" -v "$here/../keys/wharf-usign.pub:/tmp/wharf-usign.pub:ro" "$image" sh -eu -c '
mkdir -p /var/lock /var/run /tmp/dl
. /etc/openwrt_release
printf "arch all 100\narch noarch 100\narch %s 200\n" "$DISTRIB_ARCH" >> /etc/opkg.conf
grep -q "^option check_signature" /etc/opkg.conf || echo "option check_signature" >> /etc/opkg.conf
fp=$(usign -F -p /tmp/wharf-usign.pub)
echo "key fingerprint: $fp"
cp /tmp/wharf-usign.pub /etc/opkg/keys/$fp
echo "src/gz wharf $URL" >> /etc/opkg/customfeeds.conf

echo "--- diagnostics"
nslookup github.com 2>&1 | tail -4 || true
wget -O /tmp/diag.gz "$URL/Packages.gz" 2>&1 | tail -4 || true
echo "index bytes: $(wc -c < /tmp/diag.gz 2>/dev/null || echo none)"
echo "--- end diagnostics"
out=$(opkg update 2>&1) || true
echo "$out" | grep -i "wharf" || true
echo "$out" | grep -qi "signature check failed" && { echo "signature check failed"; exit 1; }
echo "$out" | grep -q "Updated list of available packages in /var/opkg-lists/wharf" || { echo "wharf feed was not updated"; echo "$out"; exit 1; }
for p in luci-app-openclash wharf-openclash wharf-glinet-openclash; do
  opkg list | grep -q "^$p - " || { echo "missing from feed: $p"; exit 1; }
done
opkg info wharf-glinet-openclash | grep -E "^(Package|Version|Depends):"

cd /tmp/dl
# opkg verifies size and sha256 from the signed index while downloading
opkg download wharf-glinet-openclash
opkg download luci-app-openclash
ls -l /tmp/dl
test -s /tmp/dl/wharf-glinet-openclash_*_all.ipk
test "$(wc -c < /tmp/dl/luci-app-openclash_*_all.ipk)" -gt 1000000
echo "published feed OK"
'
