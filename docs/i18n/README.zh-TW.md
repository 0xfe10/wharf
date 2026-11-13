# wharf

OpenWrt 路由器的外掛程式庫:託管在 GitHub Releases 上的靜態 **opkg 軟體來源**,加上針對特定韌體的薄適配層。第一個外掛是 [OpenClash](../../plugins/openclash/README.md)。

[English](../../README.md) · [简体中文](README.zh-CN.md) · 繁體中文 · [日本語](README.ja.md) · [한국어](README.ko.md)

## 使用

軟體來源以 GitHub Release 附件的形式發佈(每個來源一個 release,每次推送到 `main` 由 CI 更新):

| 來源 | URL | 適用 |
|---|---|---|
| generic | `https://github.com/0xfe10/wharf/releases/download/feed-generic` | 任何帶 opkg 的 OpenWrt |
| glinet | `https://github.com/0xfe10/wharf/releases/download/feed-glinet` | GL.iNet 4.x 韌體(會在後台新增入口) |

GL.iNet 使用者在 應用程式 > 外掛 > 新增自訂軟體來源 中把**兩個來源都加上**,然後在外掛清單中安裝 `wharf-glinet-openclash`。詳見 [using-the-feed.md](../using-the-feed.md)(英文)。

> 軟體套件沒有簽章。GL.iNet 的 opkg 不驗證簽章,但**原版 OpenWrt 會驗證**,在來源被簽章之前會拒絕這些來源。請只新增你信任的來源。

## 結構

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

## 開發

```bash
python3 -m unittest discover tests -v   # tests
node tests/view-eval.js                 # GL.iNet view loads as a Vue component
tools/build-all --out site              # build the whole feed locally (GNU tar + jq, i.e. Linux/CI)
tests/opkg-install.sh site              # install/remove round-trip (needs docker)
```

打包在 CI(Linux)中完成;macOS 上與打包相關的測試會被跳過。建置可重現(`SOURCE_DATE_EPOCH`)。上游套件原樣轉存,且只有 sha256 與儲存庫中的鎖定檔一致時才會發佈。新增外掛見 [adding-a-plugin.md](../adding-a-plugin.md)(英文)。

## 狀態

已測試:工具行為、套件格式、頁面檔載入。**尚未在真實 GL.iNet 路由器上驗證**,請依 [OpenClash 外掛文件](../../plugins/openclash/README.md)中的清單逐項驗證。

## 授權

MIT。轉存的上游套件保留各自的授權(OpenClash:MIT)。
