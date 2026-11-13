#!/bin/sh
# Installs and removes the built GL.iNet package inside an upstream OpenWrt
# container, against the generated feeds, with real dependency resolution.
# Needs docker, GNU tar and jq. It validates package format, feed index, install
# and clean removal; it cannot validate behaviour on GL.iNet firmware itself.
#
# Dependencies are resolved for real from the OpenWrt feeds, except two things a container
# cannot have, which are replaced by empty stub packages: gl-sdk4-ui-core (part of the
# GL.iNet firmware image) and kmod-tun (a kernel module).
#   tests/opkg-install.sh [site-dir]
set -eu
here=$(cd "$(dirname "$0")" && pwd)
site=$(cd "${1:-site}" && pwd)
image=${OPENWRT_IMAGE:-openwrt/rootfs:x86-64-23.05.4}
port=${PORT:-8099}

work=$(mktemp -d)
srv=
# With USIGN=<binary> the feeds are signed with a throwaway key and opkg keeps
# check_signature on (like stock OpenWrt); without it the check is off (like GL.iNet).
USIGN=${USIGN:-}
trap 'kill $srv 2>/dev/null || true; rm -rf "$work"' EXIT

mkdir -p "$work/serve" "$work/stub/stub"
cp -R "$site/feed" "$work/serve/feed"
cat > "$work/stub/stub/plugin.json" <<'JSON'
{"name":"stub","packages":[
 {"name":"kmod-tun","version":"999","feed":"stubs","description":"test stub"},
 {"name":"gl-sdk4-ui-core","version":"1","feed":"stubs","description":"test stub"}]}
JSON
for p in kmod-tun gl-sdk4-ui-core; do
	"$here/../tools/build-pkg" "$work/stub/stub" "$p" "$work/serve/stubs" >/dev/null
done
"$here/../tools/make-feed" "$work/serve/stubs" >/dev/null

fp=
if [ -n "$USIGN" ]; then
	"$USIGN" -G -s "$work/test.key" -p "$work/serve/key.pub" -c "wharf test key"
	fp=$("$USIGN" -F -p "$work/serve/key.pub")
	"$here/../tools/sign-feed" "$USIGN" "$work/test.key" "$work/serve/feed" "$work/serve/stubs"
	# tampered copy: modified index that no longer matches its signature
	cp -R "$work/serve/feed" "$work/serve/tampered"
	# opkg reads Packages.gz, so that is the file to modify (the signature stays the old one)
	gzip -dc "$work/serve/tampered/Packages.gz" > "$work/tampered.txt"
	echo "# tampered" >> "$work/tampered.txt"
	gzip -9 -n -c "$work/tampered.txt" > "$work/serve/tampered/Packages.gz"
fi

python3 -m http.server "$port" --bind 127.0.0.1 --directory "$work/serve" >/dev/null 2>&1 &
srv=$!
sleep 1

docker run --rm --network host -e PORT="$port" -e FP="$fp" "$image" sh -eu -c '
mkdir -p /var/lock /var/run
. /etc/openwrt_release
# Stock OpenWrt enables check_signature; GL.iNet firmware does not. Mimic GL.iNet.
if [ -n "$FP" ]; then
  wget -q -O /etc/opkg/keys/$FP http://127.0.0.1:$PORT/key.pub
  grep -q check_signature /etc/opkg.conf || echo "option check_signature" >> /etc/opkg.conf
else
  sed -i "/check_signature/d" /etc/opkg.conf
fi
printf "arch all 100\narch noarch 100\narch %s 200\n" "$DISTRIB_ARCH" >> /etc/opkg.conf
cat >> /etc/opkg/customfeeds.conf <<EOF2
src/gz wharf http://127.0.0.1:$PORT/feed
src/gz wharf_stubs http://127.0.0.1:$PORT/stubs
EOF2
opkg update

for p in luci-app-openclash wharf-openclash-glinet; do
  opkg list | grep -q "^$p - " || { echo "missing from feed: $p"; exit 1; }
done
opkg info luci-app-openclash | grep -q "^Depends:.*dnsmasq-full"
opkg info wharf-openclash-glinet | grep -q "^Depends:.*gl-sdk4-ui-core"

# Pretend to be a GL.iNet system for the paths we install into.
mkdir -p /usr/share/oui/menu.d /www/views /lib/upgrade/keep.d
# dnsmasq-full replaces the stock dnsmasq (as on GL.iNet firmware, where it is already installed)
opkg remove dnsmasq
opkg install wharf-openclash-glinet
opkg list-installed | grep -E "^(luci-app-openclash|luci-compat|luci|ruby|dnsmasq-full) "
opkg list-installed | grep -q "^luci-app-openclash "
opkg list-installed | grep -q "^luci-compat "
test -f /usr/share/oui/menu.d/wharf-openclash.json
test -f /www/views/gl-sdk4-ui-openclash.common.js.gz
gzip -t /www/views/gl-sdk4-ui-openclash.common.js.gz
test -x /usr/libexec/wharf-openclash/setup-luci
test -f /lib/upgrade/keep.d/wharf-openclash

opkg remove wharf-openclash-glinet
# removing the adapter leaves OpenClash itself installed
opkg list-installed | grep -q "^luci-app-openclash "
test ! -e /usr/share/oui/menu.d/wharf-openclash.json
test ! -e /www/views/gl-sdk4-ui-openclash.common.js.gz
test ! -e /usr/libexec/wharf-openclash/setup-luci
test ! -e /lib/upgrade/keep.d/wharf-openclash
if [ -n "$FP" ]; then
  # a modified index must be rejected
  echo "src/gz tampered http://127.0.0.1:$PORT/tampered" > /etc/opkg/customfeeds.conf
  # opkg update may exit 0 even when a signature check fails, so check its output
  # and that nothing from the tampered feed became installable.
  out=$(opkg update 2>&1 || true)
  echo "$out" | grep "tampered" || true
  echo "$out" | grep -q "Signature check failed" || { echo "tampered feed was not rejected"; exit 1; }
  if opkg list | grep -q "^wharf-openclash-glinet "; then echo "tampered package list was kept"; exit 1; fi
  echo "tampered feed rejected"
fi
echo "opkg round-trip OK"
'
