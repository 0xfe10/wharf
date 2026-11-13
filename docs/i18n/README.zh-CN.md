# wharf

OpenWrt 路由器的插件库:托管在 GitHub Releases 上的静态 **opkg 软件源**,加上针对特定固件的薄适配层。第一个插件是 [OpenClash](../../plugins/openclash/README.md)。

[English](../../README.md) · 简体中文 · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

## 使用

只有一个软件源,以 GitHub Release 附件的形式发布。每个版本(`v1.0.0` 等)的 release 都包含全部软件包以及 `Packages` / `Packages.gz`;最新版本始终可以通过下面这个固定地址访问:

```
https://github.com/0xfe10/wharf/releases/latest/download
```

- **GL.iNet 4.x:** 应用 > 插件 > 添加自定义软件源,填入上面的地址,然后在插件列表里安装 `wharf-glinet-openclash`。
- **其他 OpenWrt:** 在 `/etc/opkg/customfeeds.conf` 中加入 `src/gz wharf https://github.com/0xfe10/wharf/releases/latest/download`,然后执行 `opkg update && opkg install wharf-openclash`。

详见 [using-the-feed.md](../using-the-feed.md)(英文)。

> 软件源索引已用 usign 签名(v1.0.1 起)。原版 OpenWrt 需要先导入公钥,见 [using-the-feed.md](../using-the-feed.md)(英文);GL.iNet 不校验签名。请只添加你信任的源。

## 结构

```
plugins/<name>/
  plugin.json          upstream, package definitions
  upstream.lock.json   pinned upstream release (tag, URL, sha256)
  <target>/            adapter for one firmware: CONTROL/ + root/
tools/                 build-pkg, build-ipk, make-feed, fetch-upstream, build-all
tests/                 unit tests, view evaluation, opkg round-trip
.github/workflows/     build, release (vX.Y.Z tag), weekly upstream tracking
docs/                  feed usage, adding a plugin, translations
```

## 开发

```bash
python3 -m unittest discover tests -v   # tests
node tests/view-eval.js                 # GL.iNet view loads as a Vue component
tools/build-all --out site              # build the feed locally (GNU tar + jq, i.e. Linux/CI)
tests/opkg-install.sh site              # install/remove round-trip (needs docker)
```

打包在 CI(Linux)里完成;macOS 上打包相关测试会被跳过。构建可复现(`SOURCE_DATE_EPOCH`)。上游包原样转存,且只有 sha256 与仓库里的锁文件一致时才会发布。发布新版本:推送 `vX.Y.Z` 形式的 tag。新增插件见 [adding-a-plugin.md](../adding-a-plugin.md)(英文)。

## 状态

已测试:工具行为、包格式、页面文件加载。**尚未在真实 GL.iNet 路由器上验证**,请按 [OpenClash 插件文档](../../plugins/openclash/README.md)里的清单逐项验证。

## 许可证

MIT。转存的上游包保留各自的许可证(OpenClash:MIT)。
