# wharf

A small plugin library for OpenWrt routers: a static **opkg feed** (hosted on
GitHub Pages) plus thin adapters that make plugins show up nicely on specific
firmwares. [OpenClash](plugins/openclash/README.md) is the first plugin.

[中文说明](README.zh-CN.md)

## Use it

Feeds are published at `https://0xfe10.github.io/wharf/`:

| Feed | URL | For |
|---|---|---|
| generic | `https://0xfe10.github.io/wharf/opkg/generic` | any OpenWrt with opkg |
| glinet | `https://0xfe10.github.io/wharf/opkg/glinet` | GL.iNet 4.x firmware (adds an admin-panel entry) |

GL.iNet users add **both** feeds (Applications > Plugins > custom software
source), then install `wharf-glinet-openclash` from the plugin list.
Details: [docs/using-the-feed.md](docs/using-the-feed.md).

> Packages are unsigned (GL.iNet's opkg does not enable signature checks).
> Only add feeds you trust.

## Layout

```
plugins/<name>/
  plugin.json          upstream source, package definitions
  upstream.lock.json   pinned upstream release (tag, URL, sha256)
  <target>/            adapter for one firmware: CONTROL/ scripts + root/ files
tools/                 fetch-upstream, build-ipk, make-feed, build-all (Python stdlib only)
tests/                 unit tests, view evaluation (node), opkg round-trip (docker)
.github/workflows/     build + publish, weekly upstream tracking
docs/                  feed usage, how to add a plugin
```

## Develop

```bash
python3 -m unittest discover tests -v   # tool and package tests
node tests/view-eval.js                 # GL.iNet view loads as a Vue component
tools/build-all --out site              # build the whole feed locally
tests/opkg-install.sh site              # install/remove round-trip (needs docker)
```

Builds are reproducible (set `SOURCE_DATE_EPOCH`). Upstream packages are
mirrored unchanged and only after their sha256 matches the committed lock.
Adding a plugin: [docs/adding-a-plugin.md](docs/adding-a-plugin.md).

## Status

Tested: tool behaviour, package format, view evaluation. **Not yet tested on a
real GL.iNet router**: see the verification checklist in
[plugins/openclash/README.md](plugins/openclash/README.md).

## Licence

MIT. Mirrored upstream packages keep their own licences (OpenClash: MIT).
