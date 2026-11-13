# Using the wharf feeds

Feed base: `https://github.com/0xfe10/wharf/releases/download/feed-<feed>` with `<feed>` = `generic` or `glinet`.
Each feed is a GitHub release whose assets are the `.ipk` files plus `Packages` and `Packages.gz`.
The feeds exist after the first successful CI run on `main`.

## GL.iNet admin panel

1. Applications > Plugins > scroll to the custom software source section > add:
   - name `wharf_generic`, URL `https://github.com/0xfe10/wharf/releases/download/feed-generic`
   - name `wharf_glinet`, URL `https://github.com/0xfe10/wharf/releases/download/feed-glinet`
2. Refresh the plugin list, search `wharf`, install `wharf-glinet-openclash`
   (it pulls in `wharf-openclash`, `luci-app-openclash` and LuCI).
3. A new **OpenClash** entry appears under Applications.

If the plugin list does not show the packages after refreshing, use SSH (below)
and tell us; the list is generated from `opkg` by GL.iNet's `update_plugins_db`.

## SSH / any OpenWrt

```sh
cat >> /etc/opkg/customfeeds.conf <<'EOF2'
src/gz wharf_generic https://github.com/0xfe10/wharf/releases/download/feed-generic
src/gz wharf_glinet https://github.com/0xfe10/wharf/releases/download/feed-glinet
EOF2
opkg update
opkg install wharf-glinet-openclash   # GL.iNet 4.x
opkg install wharf-openclash          # any other OpenWrt (LuCI > Services > OpenClash)
```

## Signature checking (stock OpenWrt)

The feeds are **unsigned**. GL.iNet firmware does not enable `check_signature`
in `/etc/opkg.conf`, so it works there. Stock OpenWrt does, and `opkg update`
will fail with "Signature file download failed" for these feeds. On stock
OpenWrt you must remove the `option check_signature` line from `/etc/opkg.conf`
(this lowers security for all feeds) until the feeds are signed with usign.

## Removing

`opkg remove wharf-glinet-openclash` removes only the panel entry. LuCI and
OpenClash stay. Removing `luci-app-openclash` **deletes `/etc/openclash` and
`/etc/config/openclash`** (upstream behaviour); back up first.

## Reachability

The feed is downloaded by the router itself, before any proxy is running. If
`github.com` is not reachable from your network, `opkg update` fails. Releases
are static files, so you can mirror a feed (every asset of the release) to any
web server or object storage and add that URL instead. Packages are unsigned:
only use mirrors you control.
