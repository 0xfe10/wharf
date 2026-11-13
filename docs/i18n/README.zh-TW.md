# wharf

OpenWrt 路由器的外掛程式庫:託管在 GitHub Releases 上的靜態 **opkg 軟體來源**,加上針對特定韌體的薄適配層。第一個外掛是 [OpenClash](../../plugins/openclash/README.md)。

[English](../../README.md) · [简体中文](README.zh-CN.md) · 繁體中文 · [日本語](README.ja.md) · [한국어](README.ko.md)

## 使用

只有一個軟體來源,以 GitHub Release 附件的形式發佈。每個版本(`v1.0.0` 等)的 release 都包含全部軟體套件以及 `Packages` / `Packages.gz`;最新版本一律可透過下面這個固定網址取得:

```
https://github.com/0xfe10/wharf/releases/latest/download
```

- **GL.iNet 4.x:** 應用程式 > 外掛 > 新增自訂軟體來源,填入上面的網址,然後在外掛清單中安裝 `wharf-glinet-openclash`。
- **其他 OpenWrt:** 在 `/etc/opkg/customfeeds.conf` 中加入 `src/gz wharf https://github.com/0xfe10/wharf/releases/latest/download`,然後執行 `opkg update && opkg install wharf-openclash`。

詳見 [using-the-feed.md](../using-the-feed.md)(英文)。

> 軟體來源索引已用 usign 簽章(v1.0.1 起)。原版 OpenWrt 需要先匯入公鑰,見 [using-the-feed.md](../using-the-feed.md)(英文);GL.iNet 不驗證簽章。請只新增你信任的來源。

## 結構

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

## 開發

```bash
python3 -m unittest discover tests -v   # tests
node tests/view-eval.js                 # GL.iNet view loads as a Vue component
tools/build-all --out site              # build the feed locally (GNU tar + jq, i.e. Linux/CI)
tests/opkg-install.sh site              # install/remove round-trip (needs docker)
```

打包在 CI(Linux)中完成;macOS 上與打包相關的測試會被跳過。建置可重現(`SOURCE_DATE_EPOCH`)。上游套件原樣轉存,且只有 sha256 與儲存庫中的鎖定檔一致時才會發佈。發佈新版本:推送 `vX.Y.Z` 格式的 tag。新增外掛見 [adding-a-plugin.md](../adding-a-plugin.md)(英文)。

## 狀態

已測試:工具行為、套件格式、頁面檔載入。**尚未在真實 GL.iNet 路由器上驗證**,請依 [OpenClash 外掛文件](../../plugins/openclash/README.md)中的清單逐項驗證。

## 授權

MIT。轉存的上游套件保留各自的授權(OpenClash:MIT)。
