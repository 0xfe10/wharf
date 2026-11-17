# OpenClash

| Package | What it is |
|---|---|
| `luci-app-openclash` | Upstream [vernesong/OpenClash](https://github.com/vernesong/OpenClash) ipk, mirrored unchanged (pinned in `upstream.lock.json`, sha256-verified) |
| `wharf-openclash-glinet` | GL.iNet 4.x adapter: **Applications > OpenClash** panel entry, LuCI enabled on 8080/8443, `/etc/openclash`, the wharf feed and its signing key kept across firmware upgrades, boot guard that repairs DNS if an upgrade removes OpenClash |

## How the GL.iNet entry works

GL.iNet's panel (OUI) lists menu entries from `/usr/share/oui/menu.d/*.json`
and loads each page from `/www/views/gl-sdk4-ui-<view>.common.js(.gz)`. The page
shipped here is a small status page with buttons that open OpenClash's own
LuCI page (`:8080`/`:8443`) and the Zashboard dashboard (`:9090`). There is no iframe:
LuCI would be cross-origin and mixed-content (https panel, http LuCI).

`postinst` (runs on the router) reloads nginx and starts
`/usr/libexec/wharf-openclash/setup-luci` detached. That script brings LuCI up
with GL.iNet's own `/usr/bin/init_luci.sh web`, which calls opkg and therefore
cannot run while the installing opkg holds its lock. Instead of a fixed delay it:

- waits (up to 10 min) until no `opkg` process and no `/tmp/luci.lock` exist,
- skips everything if LuCI is already initialised and listening on 8080,
- runs `init_luci.sh`, then checks that LuCI really listens; retries up to 3 times,
- is idempotent and can be re-run by hand if it failed.

Check the outcome: `cat /tmp/wharf-openclash-luci.status` (`running`, `ok` or
`failed: ...`), details in `/tmp/wharf-openclash-luci.log`.

## Firmware upgrades (1.2.0 and newer)

What happened on a Mudi 7 going from firmware 4.10.0 to 4.10.2: `/etc/openclash` survived (kept by this package), but
`/etc/opkg/customfeeds.conf` did not, so GL.iNet could not reinstall `wharf-openclash-glinet`, `luci-app-openclash` and
`ruby` from `/etc/backup/installed_packages.txt`. dnsmasq still forwarded to `127.0.0.1#7874` while
`/etc/init.d/openclash` was gone: no DNS for the LAN, internet by IP address still worked. Firmware 4.10.2 also checks
package signatures, 4.10.0 did not.

The adapter now:

- keeps `/etc/opkg/customfeeds.conf` and the signing key `/etc/opkg/keys/3b9c3e21277942f0` (`keep.d`),
- ships the key (taken from `keys/` at build time, file name = usign fingerprint); its `postinst` copies it into
  `/etc/opkg/keys/` and adds `src/gz wharf https://0xfe10.github.io/wharf` if no source with that URL exists,
- installs a boot guard, `/etc/init.d/wharf-openclash-guard` (start order 18, dnsmasq is 19), that runs
  `/usr/libexec/wharf-openclash/heal-dns`: when `/etc/init.d/openclash` is missing, dnsmasq forwards to
  `127.0.0.1#<OpenClash dns_port>` and nothing listens there, it removes that forwarder (restoring the servers OpenClash
  saved), resets `noresolv`/`resolvfile`, `cachesize` and `filter_aaaa` only where OpenClash changed them, and deletes
  OpenClash's `/tmp/dnsmasq.d` snippets and firewall include. Everything else is left alone. Log:
  `/tmp/wharf-openclash-guard.log`. By hand: `heal-dns run` (also restarts dnsmasq).

Limits: GL.iNet reads the keep lists of the **old** system, so only routers that already run adapter 1.2.0+ before the
upgrade are protected. The guard repairs DNS; whether the packages are reinstalled afterwards is GL.iNet's restore step.
New users on 4.10.2 must import the key once over SSH, the panel has no way to do it
([docs/using-the-feed.md](../../docs/using-the-feed.md#signature-checking)).

### What was verified for 1.2.0 (Mudi 7, firmware 4.10.2)

On the real router:

- Update 1.1.1-1 to 1.2.0-1 through the panel (Applications > Packages > Refresh > Update) from the signed Pages feed:
  key file identical to `keys/`, exactly one feed line, guard enabled, LuCI on 8080, OpenClash kept running.
- `sysupgrade -l` lists the feed, the key, the guard script, its `/etc/rc.d/S18` link and `heal-dns`; a tar built from that
  list keeps the link as a link. (The archive was not restored.)
- Dry run of `heal-dns` on the router (its own `uci`, `netstat`, busybox) against config copies: cleans up when nothing
  listens on the OpenClash port, refuses while clash listens; the live config was unchanged.
- Boot test: with `/etc/init.d/openclash` moved aside, clash killed and dnsmasq still pointing at `127.0.0.1#7874`
  (the incident state), a reboot ran the guard before dnsmasq (log shows `(boot)`) and DNS resolved afterwards with no
  manual step. OpenClash was then restored and recreated its own DNS redirect.

**Not verified:** a real firmware upgrade (it would reflash the router). So it is unknown whether GL.iNet's own restore
step reinstalls the packages (`/etc/backup/installed_packages.txt` was empty on the router when checked) and whether it
restores the `/etc/rc.d` link as `sysupgrade -l` suggests. That the panel has no key import comes from reading its
Packages page code, not from a router without the key. Routers still on 1.1.x are not protected.

## Things to know

- Dependencies (`dnsmasq-full`, `ruby`, `kmod-tun`, ...) come from the router's
  own feeds. On the Mudi 7 (GL-E5800, firmware 4.10.0) they were present or
  available when checked.
- The OpenClash core is downloaded on first start (needs working internet).
- Removing `luci-app-openclash` deletes `/etc/openclash` and `/etc/config/openclash`.
- Do not run OpenClash together with GL.iNet's VPN features or another
  transparent proxy (e.g. Clash TUN on the router's clients) without checking
  for firewall/routing conflicts.

## Checked without a router (done in CI)

- Package format, feed index, install and clean removal in an OpenWrt container, with
  signature checking on (a tampered index is rejected).
- The release is verified after publishing against the real URL: https and GitHub redirects,
  signature with the public key in `keys/`, checksum-verified download of every package.
- Every dependency of `wharf-openclash-glinet` (117 packages) exists in the GL.iNet feeds of
  the Mudi 7 (firmware 4.10.0) or the wharf feed: `python3 tests/check-glinet-deps.py`.
  `gl-sdk4-ui-core` is part of the firmware image and in no feed.
- The panel page is evaluated like the panel does (`tests/view-eval.js`); its links follow
  OpenClash's own URL scheme (`/cgi-bin/luci/admin/services/openclash`), taken from the OpenClash 0.48.002 sources. Zashboard
  ignores address parameters in its URL (verified), so the page tells the user to enter Host and Dashboard Secret.
- `setup-luci` (waiting for opkg, retrying, status file) against stub commands.

What no CI can check: GL.iNet's own firmware code (plugin list, menu loading, `init_luci.sh`,
`opkg` behind the panel).

## Verification checklist (needs a real router)

Not yet done. Work through in order; each step says how to roll back.

1. In the panel: Applications > Packages > Manage sources, add `wharf` = `https://0xfe10.github.io/wharf` (click **+**, then Apply), Refresh. Do `wharf-*` packages appear in the plugin list?
   *(No: use SSH `opkg update; opkg list | grep wharf` and report.)*
2. Install `wharf-openclash-glinet`. Does the install finish, do the panel and
   internet keep working? *(Roll back: `opkg remove wharf-openclash-glinet`.)*
3. Is there an **Applications > OpenClash** menu entry and does the page load?
   *(Remove the package; if the panel misbehaves delete
   `/usr/share/oui/menu.d/wharf-openclash.json` and
   `/www/views/gl-sdk4-ui-openclash.common.js.gz`, then `/etc/init.d/nginx reload`.)*
4. Does `http://<router>:8080` (LuCI) open and does the settings button work?
   Check `cat /tmp/wharf-openclash-luci.status` and the log; if it says
   `failed`, send the log and re-run `/usr/libexec/wharf-openclash/setup-luci`.
5. In LuCI import a subscription, start OpenClash, open the Zashboard button (Host = the router, Password = the Dashboard Secret).
6. After a firmware upgrade: are the packages reinstalled and is `/etc/openclash` kept?
7. Does anything conflict with GL.iNet VPN / firewall features while OpenClash runs?
