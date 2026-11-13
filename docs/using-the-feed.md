# Using the wharf feed

Feed URL (always the newest release):

```
https://github.com/0xfe10/wharf/releases/latest/download
```

Each GitHub release `vX.Y.Z` contains every `.ipk` plus `Packages` and
`Packages.gz`. A specific version is also available as
`https://github.com/0xfe10/wharf/releases/download/vX.Y.Z` if you want to pin it.

## GL.iNet admin panel

1. Applications > Plugins > scroll to the custom software source section > add
   name `wharf`, URL `https://github.com/0xfe10/wharf/releases/latest/download`.
2. Refresh the plugin list, search `wharf`, install `wharf-glinet-openclash`
   (it pulls in `wharf-openclash`, `luci-app-openclash` and LuCI).
3. A new **OpenClash** entry appears under Applications.

If the plugin list does not show the packages after refreshing, use SSH (below)
and tell us; the list is generated from `opkg` by GL.iNet's `update_plugins_db`.

## SSH / any OpenWrt

```sh
echo 'src/gz wharf https://github.com/0xfe10/wharf/releases/latest/download' >> /etc/opkg/customfeeds.conf
opkg update
opkg install wharf-glinet-openclash   # GL.iNet 4.x
opkg install wharf-openclash          # any other OpenWrt (LuCI > Services > OpenClash)
```

`wharf-glinet-openclash` depends on `gl-sdk4-ui-core`, so it cannot be installed
on non-GL.iNet systems even though it is listed.

## Signature checking (stock OpenWrt)

The feed is **unsigned**. GL.iNet firmware does not enable `check_signature`
in `/etc/opkg.conf`, so it works there. Stock OpenWrt does, and `opkg update`
will fail with "Signature file download failed". On stock OpenWrt you must remove
the `option check_signature` line from `/etc/opkg.conf` (this lowers security for
all feeds) until the feed is signed with usign.

## Removing

`opkg remove wharf-glinet-openclash` removes only the panel entry. LuCI and
OpenClash stay. Removing `luci-app-openclash` **deletes `/etc/openclash` and
`/etc/config/openclash`** (upstream behaviour); back up first.

## Reachability

The feed is downloaded by the router itself, before any proxy is running. If
`github.com` is not reachable from your network, `opkg update` fails. A release
is a set of static files: you can mirror its assets to any web server or object
storage and add that URL instead. Packages are unsigned: only use mirrors you control.
