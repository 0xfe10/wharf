# wharf

OpenWrt 路由器的插件库:托管在 GitHub Releases 上的静态 **opkg 软件源**,加上针对特定固件的薄适配层。第一个插件是 [OpenClash](../../plugins/openclash/README.md)。

[English](../../README.md) · 简体中文 · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

## 使用

软件源以 GitHub Release 附件的形式发布(每个源一个 release,每次推送到 `main` 由 CI 更新):

| 源 | URL | 适用 |
|---|---|---|
| generic | `https://github.com/0xfe10/wharf/releases/download/feed-generic` | 任何带 opkg 的 OpenWrt |
| glinet | `https://github.com/0xfe10/wharf/releases/download/feed-glinet` | GL.iNet 4.x 固件(会在后台添加入口) |

GL.iNet 用户在 应用 > 插件 > 添加自定义软件源 里把**两个源都加上**,然后在插件列表里安装 `wharf-glinet-openclash`。详见 [using-the-feed.md](../using-the-feed.md)(英文)。

> 软件包没有签名。GL.iNet 的 opkg 不校验签名,但**原版 OpenWrt 会校验**,在源被签名之前会拒绝这些源。请只添加你信任的源。

## 结构

```
plugins/<name>/
  plugin.json          upstream, package definitions
  upstream.lock.json   pinned upstream release (tag, URL, sha256)
  <target>/            adapter for one firmware: CONTROL/ + root/
tools/                 build-pkg, build-ipk, make-feed, fetch-upstream, build-all
tests/                 unit tests, view evaluation, opkg round-trip
.github/workflows/     build + publish, weekly upstream tracking
docs/                  feed usage, adding a plugin, translations
```

## 开发

```bash
python3 -m unittest discover tests -v   # tests
node tests/view-eval.js                 # GL.iNet view loads as a Vue component
tools/build-all --out site              # build the whole feed locally (GNU tar + jq, i.e. Linux/CI)
tests/opkg-install.sh site              # install/remove round-trip (needs docker)
```

打包在 CI(Linux)里完成;macOS 上打包相关测试会被跳过。构建可复现(`SOURCE_DATE_EPOCH`)。上游包原样转存,且只有 sha256 与仓库里的锁文件一致时才会发布。新增插件见 [adding-a-plugin.md](../adding-a-plugin.md)(英文)。

## 状态

已测试:工具行为、包格式、页面文件加载。**尚未在真实 GL.iNet 路由器上验证**,请按 [OpenClash 插件文档](../../plugins/openclash/README.md)里的清单逐项验证。

## 许可证

MIT。转存的上游包保留各自的许可证(OpenClash:MIT)。
