# OpenClash

| Package | What it is |
|---|---|
| `luci-app-openclash` | Upstream [vernesong/OpenClash](https://github.com/vernesong/OpenClash) ipk, mirrored unchanged (pinned in `upstream.lock.json`, sha256-verified) |
| `wharf-openclash-glinet` | GL.iNet 4.x adapter: **Applications > OpenClash** panel entry, LuCI enabled on 8080/8443, `/etc/openclash` kept across firmware upgrades |

## How the GL.iNet entry works

GL.iNet's panel (OUI) lists menu entries from `/usr/share/oui/menu.d/*.json`
and loads each page from `/www/views/gl-sdk4-ui-<view>.common.js(.gz)`. The page
shipped here is a small status page with buttons that open OpenClash's own
LuCI page (`:8080`/`:8443`) and its dashboards (`:9090`). There is no iframe:
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
  OpenClash's own URL scheme (`/cgi-bin/luci/admin/services/openclash`, `/ui/<dashboard>/#/setup?...`),
  taken from the OpenClash 0.48.002 sources.
- `setup-luci` (waiting for opkg, retrying, status file) against stub commands.

What no CI can check: GL.iNet's own firmware code (plugin list, menu loading, `init_luci.sh`,
`opkg` behind the panel).

## Verification checklist (needs a real router)

Not yet done. Work through in order; each step says how to roll back.

1. In the panel: Applications > Packages > Manage sources, add `wharf` = `https://github.com/0xfe10/wharf/releases/latest/download` (click **+**, then Apply), Refresh. Do `wharf-*` packages appear in the plugin list?
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
5. In LuCI import a subscription, start OpenClash, open the dashboard links.
6. After a firmware upgrade: are the packages reinstalled and is `/etc/openclash` kept?
7. Does anything conflict with GL.iNet VPN / firewall features while OpenClash runs?
