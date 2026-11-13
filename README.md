# wharf

A small plugin library for OpenWrt routers: a static **opkg feed** (hosted on
GitHub Releases) plus thin adapters that make plugins show up nicely on specific
firmwares. [OpenClash](plugins/openclash/README.md) is the first plugin.

[简体中文](docs/i18n/README.zh-CN.md) · [繁體中文](docs/i18n/README.zh-TW.md) · [日本語](docs/i18n/README.ja.md) · [한국어](docs/i18n/README.ko.md)

## Use it

One feed, published as GitHub release assets. Every release (`v1.0.0`, ...) holds
all packages plus `Packages` / `Packages.gz`; the newest release is always
reachable at this fixed URL:

```
https://github.com/0xfe10/wharf/releases/latest/download
```

- **GL.iNet 4.x:** Applications > Plugins > custom software source, add the URL,
  then install `wharf-glinet-openclash` from the plugin list.
- **Other OpenWrt:** `src/gz wharf https://github.com/0xfe10/wharf/releases/latest/download` in `/etc/opkg/customfeeds.conf`, then
  `opkg update && opkg install wharf-openclash`.

Details: [docs/using-the-feed.md](docs/using-the-feed.md).

> From v1.0.1 the feed is signed (usign). Stock OpenWrt needs the public key imported
> first, see [docs/using-the-feed.md](docs/using-the-feed.md); GL.iNet does not check signatures.
> Only add feeds you trust.

## Layout

```
plugins/<name>/
  plugin.json          upstream source, package definitions
  upstream.lock.json   pinned upstream release (tag, URL, sha256)
  <target>/            adapter for one firmware: CONTROL/ scripts + root/ files
tools/                 build-pkg, build-ipk, make-feed (sh + GNU tar + jq), fetch-upstream, build-all (Python stdlib)
tests/                 unit tests, view evaluation (node), opkg round-trip (docker)
.github/workflows/     build, release (push a vX.Y.Z tag), weekly upstream tracking
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
