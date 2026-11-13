# Using the wharf feeds

Feed base: `https://0xfe10.github.io/wharf/opkg/<feed>` with `<feed>` = `generic` or `glinet`.
The site root lists the packages currently published.

## GL.iNet admin panel

1. Applications > Plugins > scroll to the custom software source section > add:
   - name `wharf_generic`, URL `https://0xfe10.github.io/wharf/opkg/generic`
   - name `wharf_glinet`, URL `https://0xfe10.github.io/wharf/opkg/glinet`
2. Refresh the plugin list, search `wharf`, install `wharf-glinet-openclash`
   (it pulls in `wharf-openclash`, `luci-app-openclash` and LuCI).
3. A new **OpenClash** entry appears under Applications.

If the plugin list does not show the packages after refreshing, use SSH (below)
and tell us; the list is generated from `opkg` by GL.iNet's `update_plugins_db`.

## SSH / any OpenWrt

```sh
cat >> /etc/opkg/customfeeds.conf <<'EOF2'
src/gz wharf_generic https://0xfe10.github.io/wharf/opkg/generic
src/gz wharf_glinet https://0xfe10.github.io/wharf/opkg/glinet
EOF2
opkg update
opkg install wharf-glinet-openclash   # GL.iNet 4.x
opkg install wharf-openclash          # any other OpenWrt (LuCI > Services > OpenClash)
```

## Removing

`opkg remove wharf-glinet-openclash` removes only the panel entry. LuCI and
OpenClash stay. Removing `luci-app-openclash` **deletes `/etc/openclash` and
`/etc/config/openclash`** (upstream behaviour); back up first.
