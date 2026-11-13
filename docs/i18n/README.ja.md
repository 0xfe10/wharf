# wharf

OpenWrt ルーター向けのプラグインライブラリです。GitHub Releases でホストする静的な **opkg フィード**と、特定ファームウェア向けの薄いアダプターで構成されます。最初のプラグインは [OpenClash](../../plugins/openclash/README.md) です。

[English](../../README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · 日本語 · [한국어](README.ko.md)

## 使い方

フィードは 1 つで、GitHub Release のアセットとして公開されます。各バージョン(`v1.0.0` など)の release にはすべてのパッケージと `Packages` / `Packages.gz` が含まれ、最新版は次の固定 URL から常に取得できます。

```
https://github.com/0xfe10/wharf/releases/latest/download
```

- **GL.iNet 4.x:** 「アプリケーション > プラグイン」のカスタムソフトウェアソースに上の URL を追加し、プラグイン一覧から `wharf-glinet-openclash` をインストールします。
- **その他の OpenWrt:** `/etc/opkg/customfeeds.conf` に `src/gz wharf https://github.com/0xfe10/wharf/releases/latest/download` を追加し、`opkg update && opkg install wharf-openclash` を実行します。

詳細は [using-the-feed.md](../using-the-feed.md)(英語)を参照してください。

> パッケージには署名がありません。GL.iNet の opkg は署名を検証しませんが、**標準の OpenWrt は検証する**ため、フィードに署名するまで拒否されます。信頼できるフィードだけを追加してください。

## 構成

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

## 開発

```bash
python3 -m unittest discover tests -v   # tests
node tests/view-eval.js                 # GL.iNet view loads as a Vue component
tools/build-all --out site              # build the feed locally (GNU tar + jq, i.e. Linux/CI)
tests/opkg-install.sh site              # install/remove round-trip (needs docker)
```

パッケージ作成は CI(Linux)で行い、macOS ではパッケージ関連のテストはスキップされます。ビルドは再現可能です(`SOURCE_DATE_EPOCH`)。上流パッケージはそのままミラーされ、sha256 がリポジトリのロックファイルと一致した場合のみ公開されます。新しいバージョンの公開は `vX.Y.Z` 形式のタグをプッシュします。プラグインの追加は [adding-a-plugin.md](../adding-a-plugin.md)(英語)を参照してください。

## 状況

テスト済み: ツールの動作、パッケージ形式、ビューの読み込み。**実機の GL.iNet ルーターでは未検証**です。[OpenClash プラグインのドキュメント](../../plugins/openclash/README.md)のチェックリストに沿って確認してください。

## ライセンス

MIT。ミラーした上流パッケージはそれぞれのライセンスを保持します(OpenClash: MIT)。
