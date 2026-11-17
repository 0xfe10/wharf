# Using the wharf feed

Feed URL (always the newest release):

```
https://0xfe10.github.io/wharf
```

The same files are attached to each GitHub release `vX.Y.Z`
(`https://github.com/0xfe10/wharf/releases/download/vX.Y.Z` pins a version), but do not use release
URLs as the feed on GL.iNet routers: their download client cannot read the large response headers
of `github.com` (see [issue #1](https://github.com/0xfe10/wharf/issues/1)).

## GL.iNet admin panel

0. **Firmware 4.10.2 and newer only: import the signing key once** (see [Signature checking](#signature-checking)).
   The panel has no key import (its Packages page only has the sources form), so this one step needs SSH.
   Firmware 4.10.0 does not check signatures; skip this step there.
1. Applications > Packages > **Manage sources**.
2. Name `wharf`, URL `https://0xfe10.github.io/wharf`, then click the **+** icon next to the fields (the entry must appear in
   the list below), then **Apply**.
3. Click **Refresh**, search `wharf`, install `wharf-openclash-glinet`
   (it pulls in `luci-app-openclash` and LuCI; LuCI is enabled automatically).
4. A new **OpenClash** entry appears under Applications.

## SSH / any OpenWrt

```sh
echo 'src/gz wharf https://0xfe10.github.io/wharf' >> /etc/opkg/customfeeds.conf
opkg update
opkg install wharf-openclash-glinet            # GL.iNet 4.x (panel entry + LuCI + OpenClash)
opkg install luci-compat luci-app-openclash    # any other OpenWrt (LuCI > Services > OpenClash)
```

`wharf-openclash-glinet` depends on `gl-sdk4-ui-core`, so it cannot be installed
on non-GL.iNet systems even though it is listed.

## Signature checking

From v1.0.1 the feed index (`Packages`) is signed with usign; the signature is
`Packages.sig` next to it. Stock OpenWrt checks signatures, so import the public
key once:

```sh
wget -O /etc/opkg/keys/3b9c3e21277942f0 https://0xfe10.github.io/wharf/wharf-usign.pub
```

The key file name must be the key fingerprint, `3b9c3e21277942f0`. Compare it
with `keys/wharf-usign.pub` in this repository before trusting it. The same file
is attached to every release as `wharf-usign.pub`.

**GL.iNet firmware:** 4.10.0 does not check signatures (no `check_signature` in `/etc/opkg.conf`), so
the feed works without the key. **4.10.2 does** (`option check_signature`): without the key,
`opkg update` / **Refresh** rejects the wharf feed. The panel cannot import a key, so do it once over SSH
with the command above. A chicken-and-egg problem no package can solve: `wharf-openclash-glinet` ships the
key too, but you need it to install the package in the first place.

From `wharf-openclash-glinet` 1.2.0 the package copies the key into `/etc/opkg/keys/` itself (and leaves it
there if you remove the package: that is your trust decision, not the package's).

## Firmware upgrades (GL.iNet)

A GL.iNet firmware upgrade keeps only what the *old* system lists in `/lib/upgrade/keep.d/`, then tries to
reinstall the packages from `/etc/backup/installed_packages.txt` using the feeds in
`/etc/opkg/customfeeds.conf`. Seen on a Mudi 7 (GL-E5800) going from 4.10.0 to 4.10.2: `/etc/openclash` survived,
but the wharf feed line was gone, so `wharf-openclash-glinet`, `luci-app-openclash` and `ruby` were not restored.
`/etc/init.d/openclash` vanished while dnsmasq still forwarded all DNS to OpenClash (`127.0.0.1#7874`), so the
whole LAN lost name resolution (pinging IP addresses still worked).

From `wharf-openclash-glinet` 1.2.0 the package keeps, across upgrades:

| Kept | Why |
|---|---|
| `/etc/openclash/`, `/etc/config/openclash` | OpenClash core, subscription and settings (as before) |
| `/etc/opkg/customfeeds.conf` | the wharf feed, so GL.iNet can reinstall the packages from it |
| `/etc/opkg/keys/3b9c3e21277942f0` | the signing key, needed on 4.10.2 and newer (the whole `keys/` directory is also kept by GL.iNet) |
| the boot guard (`/etc/init.d/wharf-openclash-guard`, its `/etc/rc.d/S18` link, `/usr/libexec/wharf-openclash/heal-dns`) | see below |

**Boot guard.** If, after an upgrade, OpenClash's service script `/etc/init.d/openclash` is missing but dnsmasq still
forwards to `127.0.0.1#<OpenClash dns port>` and nothing listens there, the guard (start order 18, before dnsmasq)
undoes what OpenClash itself had changed, the way OpenClash's own stop does: it removes that one forwarder (and puts back
the servers OpenClash saved), turns `noresolv` back off if no upstream server is left (or OpenClash saved it as off),
restores the cache size / AAAA filter OpenClash saved, deletes OpenClash's `/tmp/dnsmasq.d` snippets and its
firewall include. It never touches other DNS settings, does nothing while OpenClash is installed or something
listens on that port, and logs to syslog (`logread -e wharf-openclash-guard`). When OpenClash is reinstalled later it
sets up its own DNS redirect again. You can run it by hand: `/usr/libexec/wharf-openclash/heal-dns run`
(also restarts dnsmasq).

Limits you should know:

- GL.iNet reads the keep lists of the **old** system when it upgrades. These protections only apply to routers
  that already have `wharf-openclash-glinet` 1.2.0 or newer installed **before** the upgrade. Routers on 1.1.x are not
  protected: update the adapter first (Applications > Packages > Refresh, then update).
- The guard only repairs DNS. Whether GL.iNet then reinstalls the packages depends on its own restore step.
  If it does not, install `wharf-openclash-glinet` again from the panel.
- Nothing here can survive a factory reset or a firmware flash with "keep settings" turned off.

## Removing

`opkg remove wharf-openclash-glinet` removes only the panel entry. LuCI and
OpenClash stay. Removing `luci-app-openclash` **deletes `/etc/openclash` and
`/etc/config/openclash`** (upstream behaviour); back up first.

## Reachability

The feed is downloaded by the router itself, before any proxy is running, so `github.io` must be
reachable from its network. A release is a set of static files: you can mirror its assets to any web
server you control and add that URL instead (the signature stays valid). Packages are signed: only
use mirrors you control.
