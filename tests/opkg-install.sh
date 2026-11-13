#!/bin/sh
# Installs and removes the built GL.iNet package inside an upstream OpenWrt
# container, against the generated feeds, with real dependency resolution.
# Needs docker, GNU tar and jq. It validates package format, feed index, install
# and clean removal; it cannot validate behaviour on GL.iNet firmware itself.
#
# Dependencies that only exist on real systems are replaced by empty stub
# packages: gl-sdk4-ui-core (GL.iNet firmware) and wharf-openclash (so the
# 10 MB upstream OpenClash with its own dependency tree is not installed).
#   tests/opkg-install.sh [site-dir]
set -eu
here=$(cd "$(dirname "$0")" && pwd)
site=$(cd "${1:-site}" && pwd)
image=${OPENWRT_IMAGE:-openwrt/rootfs:x86-64-23.05.4}
port=${PORT:-8099}

work=$(mktemp -d)
srv=
trap 'kill $srv 2>/dev/null || true; rm -rf "$work"' EXIT

mkdir -p "$work/serve" "$work/stub/stub"
cp -R "$site/opkg" "$work/serve/opkg"
cat > "$work/stub/stub/plugin.json" <<'JSON'
{"name":"stub","packages":[
 {"name":"wharf-openclash","version":"999","feed":"stubs","description":"test stub"},
 {"name":"gl-sdk4-ui-core","version":"1","feed":"stubs","description":"test stub"}]}
JSON
for p in wharf-openclash gl-sdk4-ui-core; do
	"$here/../tools/build-pkg" "$work/stub/stub" "$p" "$work/serve/opkg/stubs" >/dev/null
done
"$here/../tools/make-feed" "$work/serve/opkg/stubs" >/dev/null

python3 -m http.server "$port" --bind 127.0.0.1 --directory "$work/serve" >/dev/null 2>&1 &
srv=$!
sleep 1

docker run --rm --network host -e PORT="$port" "$image" sh -eu -c '
mkdir -p /var/lock /var/run
. /etc/openwrt_release
# Stock OpenWrt enables check_signature; GL.iNet firmware does not. Mimic GL.iNet.
sed -i "/check_signature/d" /etc/opkg.conf
printf "arch all 100\narch noarch 100\narch %s 200\n" "$DISTRIB_ARCH" >> /etc/opkg.conf
cat >> /etc/opkg/customfeeds.conf <<EOF2
src/gz wharf_generic http://127.0.0.1:$PORT/opkg/generic
src/gz wharf_glinet http://127.0.0.1:$PORT/opkg/glinet
src/gz wharf_stubs http://127.0.0.1:$PORT/opkg/stubs
EOF2
opkg update

for p in luci-app-openclash wharf-openclash wharf-glinet-openclash; do
  opkg list | grep -q "^$p - " || { echo "missing from feed: $p"; exit 1; }
done
opkg info luci-app-openclash | grep -q "^Depends:.*dnsmasq-full"
opkg info wharf-glinet-openclash | grep -q "^Depends:.*gl-sdk4-ui-core"

# Pretend to be a GL.iNet system for the paths we install into.
mkdir -p /usr/share/oui/menu.d /www/views /lib/upgrade/keep.d
opkg install wharf-glinet-openclash
test -f /usr/share/oui/menu.d/wharf-openclash.json
test -f /www/views/gl-sdk4-ui-openclash.common.js.gz
gzip -t /www/views/gl-sdk4-ui-openclash.common.js.gz
test -x /usr/libexec/wharf-openclash/setup-luci
test -f /lib/upgrade/keep.d/wharf-openclash

opkg remove wharf-glinet-openclash
test ! -e /usr/share/oui/menu.d/wharf-openclash.json
test ! -e /www/views/gl-sdk4-ui-openclash.common.js.gz
test ! -e /usr/libexec/wharf-openclash/setup-luci
test ! -e /lib/upgrade/keep.d/wharf-openclash
echo "opkg round-trip OK"
'
