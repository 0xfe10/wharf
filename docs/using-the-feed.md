# Using the wharf feed

Feed URL (always the newest release):

```
https://0xfe10.github.io/wharf
```

The same files are attached to each GitHub release `vX.Y.Z`. If `github.com` is reachable from your
network, `https://0xfe10.github.io/wharf` works too, and `https://github.com/0xfe10/wharf/releases/download/vX.Y.Z` pins a
version. Prefer the Pages URL: release downloads begin at `github.com`, which some networks block
while `github.io` works.

## GL.iNet admin panel

1. Applications > Packages > **Manage sources**.
2. Name `wharf`, URL `https://0xfe10.github.io/wharf`, then click the **+** icon next to the fields (the entry must appear in
   the list below), then **Apply**.
3. Click **Refresh**, search `wharf`, install `wharf-glinet-openclash`
   (it pulls in `wharf-openclash`, `luci-app-openclash` and LuCI; LuCI is enabled automatically).
4. A new **OpenClash** entry appears under Applications.

## SSH / any OpenWrt

```sh
echo 'src/gz wharf https://0xfe10.github.io/wharf' >> /etc/opkg/customfeeds.conf
opkg update
opkg install wharf-glinet-openclash   # GL.iNet 4.x
opkg install wharf-openclash          # any other OpenWrt (LuCI > Services > OpenClash)
```

`wharf-glinet-openclash` depends on `gl-sdk4-ui-core`, so it cannot be installed
on non-GL.iNet systems even though it is listed.

## Signature checking

From v1.0.1 the feed index (`Packages`) is signed with usign; the signature is
`Packages.sig` next to it. Stock OpenWrt checks signatures, so import the public
key once (GL.iNet firmware does not check signatures and works without it):

```sh
wget -O /etc/opkg/keys/3b9c3e21277942f0 https://0xfe10.github.io/wharf/wharf-usign.pub
```

The key file name must be the key fingerprint, `3b9c3e21277942f0`. Compare it
with `keys/wharf-usign.pub` in this repository before trusting it. The same file
is attached to every release as `wharf-usign.pub`.

## Removing

`opkg remove wharf-glinet-openclash` removes only the panel entry. LuCI and
OpenClash stay. Removing `luci-app-openclash` **deletes `/etc/openclash` and
`/etc/config/openclash`** (upstream behaviour); back up first.

## Reachability

The feed is downloaded by the router itself, before any proxy is running. If
`github.io` is not reachable from your network, `opkg update` fails. A release
is a set of static files: you can mirror its assets to any web server or object
storage and add that URL instead. Packages are unsigned: only use mirrors you control.
