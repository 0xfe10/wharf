# wharf

OpenWrt 路由器的插件库:一个托管在 GitHub Pages 上的静态 **opkg 软件源**,
加上针对特定固件的薄适配层。第一个插件是 [OpenClash](plugins/openclash/README.md)。

[English](README.md)

## 使用

软件源地址 `https://0xfe10.github.io/wharf/`:

| 源 | 地址 | 适用 |
|---|---|---|
| generic | `https://0xfe10.github.io/wharf/opkg/generic` | 任何带 opkg 的 OpenWrt |
| glinet | `https://0xfe10.github.io/wharf/opkg/glinet` | GL.iNet 4.x 固件(会在后台添加入口) |

GL.iNet 用户在 应用 > 插件 > 添加自定义软件源 里把**两个源都加上**,然后在插件列表里
安装 `wharf-glinet-openclash`。详见 [docs/using-the-feed.md](docs/using-the-feed.md)。

> 软件包没有签名(GL.iNet 的 opkg 不校验签名),请只添加你信任的源。

## 结构

```
plugins/<名称>/
  plugin.json          上游来源、包定义
  upstream.lock.json   固定的上游版本(tag、URL、sha256)
  <目标固件>/          一种固件的适配层:CONTROL/ 脚本 + root/ 文件
tools/                 build-pkg、build-ipk、make-feed(sh + GNU tar + jq)、fetch-upstream、build-all(Python 标准库)
tests/                 单元测试、页面文件加载测试(node)、opkg 安装卸载测试(docker)
.github/workflows/     构建发布、每周检查上游新版本
docs/                  软件源用法、如何新增插件
```

## 开发

```bash
python3 -m unittest discover tests -v   # 工具、打包、setup-luci 测试
node tests/view-eval.js                 # 检查 GL.iNet 页面文件能作为 Vue 组件加载
tools/build-all --out site              # 本地构建整个软件源
tests/opkg-install.sh site              # 安装/卸载往返测试(需要 docker)
```

打包在 CI(Linux:GNU tar、gzip、jq)里完成;在 macOS 上打包相关测试会被跳过,其余照常运行。构建可复现(`SOURCE_DATE_EPOCH`)。上游包原样转存,且只有在 sha256 与仓库里提交的
锁文件一致时才会发布。新增插件见 [docs/adding-a-plugin.md](docs/adding-a-plugin.md)。

## 状态

已测试:工具行为、包格式、页面文件加载。**尚未在真实 GL.iNet 路由器上验证**,
请按 [plugins/openclash/README.md](plugins/openclash/README.md) 里的清单逐项验证。

## 许可证

MIT。转存的上游包保留它们自己的许可证(OpenClash:MIT)。
