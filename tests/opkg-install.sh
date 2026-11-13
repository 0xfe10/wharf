#!/bin/sh
# Installs and removes the built GL.iNet package inside an upstream OpenWrt
# container, against the generated feeds. Needs docker and python3.
# This validates package format, feed index and clean removal; it cannot
# validate behaviour on GL.iNet firmware itself.
#   tests/opkg-install.sh [site-dir]
set -eu
site=$(cd "${1:-site}" && pwd)
image=${OPENWRT_IMAGE:-openwrt/rootfs:x86-64-23.05.4}
port=${PORT:-8099}

python3 -m http.server "$port" --bind 127.0.0.1 --directory "$site" >/dev/null 2>&1 &
srv=$!
trap 'kill $srv 2>/dev/null || true' EXIT
sleep 1

docker run --rm --network host -e PORT="$port" "$image" sh -eu -c '
mkdir -p /var/lock /var/run
cat > /etc/opkg/distfeeds.conf <<EOF2
src/gz wharf_generic http://127.0.0.1:$PORT/opkg/generic
src/gz wharf_glinet http://127.0.0.1:$PORT/opkg/glinet
EOF2
: > /etc/opkg/customfeeds.conf
# Stock OpenWrt enables check_signature; GL.iNet firmware does not. Mimic GL.iNet.
sed -i "/check_signature/d" /etc/opkg.conf
opkg update

for p in luci-app-openclash wharf-openclash wharf-glinet-openclash; do
  opkg list | grep -q "^$p - " || { echo "missing from feed: $p"; exit 1; }
done
opkg info wharf-glinet-openclash | grep -q "^Depends:.*gl-sdk4-ui-core"

# Pretend to be a GL.iNet system for the paths we install into.
mkdir -p /usr/share/oui/menu.d /www/views /lib/upgrade/keep.d
opkg install --force-depends wharf-glinet-openclash
test -f /usr/share/oui/menu.d/wharf-openclash.json
test -f /www/views/gl-sdk4-ui-openclash.common.js.gz
gzip -t /www/views/gl-sdk4-ui-openclash.common.js.gz
test -f /lib/upgrade/keep.d/wharf-openclash

opkg remove --force-depends wharf-glinet-openclash
test ! -e /usr/share/oui/menu.d/wharf-openclash.json
test ! -e /www/views/gl-sdk4-ui-openclash.common.js.gz
test ! -e /lib/upgrade/keep.d/wharf-openclash

echo "--- informational: dependency resolution of the generic meta package"
opkg install --noaction wharf-openclash || true
echo "opkg round-trip OK"
'
