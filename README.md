# wharf

A small plugin library for OpenWrt routers: a static **opkg feed** (hosted on
GitHub Releases) plus thin adapters that make plugins show up nicely on specific
firmwares. [OpenClash](plugins/openclash/README.md) is the first plugin.

[简体中文](docs/i18n/README.zh-CN.md) · [繁體中文](docs/i18n/README.zh-TW.md) · [日本語](docs/i18n/README.ja.md) · [한국어](docs/i18n/README.ko.md)

## Use it

Feeds are published as GitHub release assets (one release per feed, updated by CI on every push to `main`):

| Feed | URL | For |
|---|---|---|
| generic | `https://github.com/0xfe10/wharf/releases/download/feed-generic` | any OpenWrt with opkg |
| glinet | `https://github.com/0xfe10/wharf/releases/download/feed-glinet` | GL.iNet 4.x firmware (adds an admin-panel entry) |

GL.iNet users add **both** feeds (Applications > Plugins > custom software
source), then install `wharf-glinet-openclash` from the plugin list.
Details: [docs/using-the-feed.md](docs/using-the-feed.md).

> Packages are unsigned. GL.iNet's opkg does not enable signature checks, but **stock
> OpenWrt does** and will reject these feeds until they are signed (see
> [docs/using-the-feed.md](docs/using-the-feed.md)). Only add feeds you trust.

## Layout

```
plugins/<name>/
  plugin.json          upstream source, package definitions
  upstream.lock.json   pinned upstream release (tag, URL, sha256)
  <target>/            adapter for one firmware: CONTROL/ scripts + root/ files
tools/                 build-pkg, build-ipk, make-feed (sh + GNU tar + jq), fetch-upstream, build-all (Python stdlib)
tests/                 unit tests, view evaluation (node), opkg round-trip (docker)
.github/workflows/     build + publish, weekly upstream tracking
docs/                  feed usage, how to add a plugin
```

## Develop

```bash
python3 -m unittest discover tests -v   # tool, package and setup-luci tests
node tests/view-eval.js                 # GL.iNet view loads as a Vue component
tools/build-all --out site              # build the whole feed locally
tests/opkg-install.sh site              # install/remove round-trip (needs docker)
```

Packages are built by CI (Linux: GNU tar, gzip, jq); on macOS the packaging tests are
skipped and everything else still runs. Builds are reproducible (`SOURCE_DATE_EPOCH`). Upstream packages are
mirrored unchanged and only after their sha256 matches the committed lock.
Adding a plugin: [docs/adding-a-plugin.md](docs/adding-a-plugin.md).

## Status

Tested: tool behaviour, package format, view evaluation. **Not yet tested on a
real GL.iNet router**: see the verification checklist in
[plugins/openclash/README.md](plugins/openclash/README.md).

## Licence

MIT. Mirrored upstream packages keep their own licences (OpenClash: MIT).
