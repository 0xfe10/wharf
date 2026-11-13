# Using the wharf feed

Feed URL (always the newest release):

```
https://github.com/0xfe10/wharf/releases/latest/download
```

Each GitHub release `vX.Y.Z` holds every `.ipk` plus `Packages`, `Packages.gz`, `Packages.sig` and
`wharf-usign.pub`; `https://github.com/0xfe10/wharf/releases/download/vX.Y.Z` pins a version.

## GL.iNet admin panel

1. Applications > Packages > **Manage sources**.
2. Name `wharf`, URL `https://github.com/0xfe10/wharf/releases/latest/download`, then click the **+** icon next to the fields (the entry must appear in
   the list below), then **Apply**.
3. Click **Refresh**, search `wharf`, install `wharf-glinet-openclash`
   (it pulls in `wharf-openclash`, `luci-app-openclash` and LuCI; LuCI is enabled automatically).
4. A new **OpenClash** entry appears under Applications.

## SSH / any OpenWrt

```sh
echo 'src/gz wharf https://github.com/0xfe10/wharf/releases/latest/download' >> /etc/opkg/customfeeds.conf
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
wget -O /etc/opkg/keys/3b9c3e21277942f0 https://github.com/0xfe10/wharf/releases/latest/download/wharf-usign.pub
```

The key file name must be the key fingerprint, `3b9c3e21277942f0`. Compare it
with `keys/wharf-usign.pub` in this repository before trusting it. The same file
is attached to every release as `wharf-usign.pub`.

## Removing

`opkg remove wharf-glinet-openclash` removes only the panel entry. LuCI and
OpenClash stay. Removing `luci-app-openclash` **deletes `/etc/openclash` and
`/etc/config/openclash`** (upstream behaviour); back up first.

## Reachability

The feed is downloaded by the router itself. Release downloads start at `github.com` (and continue on
GitHub's asset hosts). In some networks `github.com` is blocked while the router has no proxy yet; then
`opkg update` fails. Options: get a proxy running for the router first (for example OpenClash installed
by other means), or mirror all assets of a release to a web server you control and add that URL instead
(a release is a flat set of static files; the signature stays valid). Packages are signed: only use
mirrors you control.
