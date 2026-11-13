# wharf

OpenWrt 라우터용 플러그인 라이브러리입니다. GitHub Releases에서 호스팅하는 정적 **opkg 피드**와 특정 펌웨어용 얇은 어댑터로 구성됩니다. 첫 번째 플러그인은 [OpenClash](../../plugins/openclash/README.md)입니다.

[English](../../README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · 한국어

## 사용법

피드는 하나이며 GitHub Pages에서 배포됩니다(같은 파일이 각 버전 release에도 첨부됩니다). 이 URL은 항상 최신 버전을 가리킵니다.

```
https://0xfe10.github.io/wharf
```

- **GL.iNet 4.x:** '애플리케이션 > 플러그인'의 사용자 지정 소프트웨어 소스에 위 URL을 추가한 뒤 플러그인 목록에서 `wharf-glinet-openclash`를 설치합니다.
- **그 밖의 OpenWrt:** `/etc/opkg/customfeeds.conf`에 `src/gz wharf https://0xfe10.github.io/wharf`를 추가하고 `opkg update && opkg install wharf-openclash`를 실행합니다.

자세한 내용은 [using-the-feed.md](../using-the-feed.md)(영어)를 참고하세요.

> 피드 인덱스는 usign으로 서명됩니다(v1.0.1부터). 기본 OpenWrt에서는 먼저 공개 키를 가져와야 합니다. [using-the-feed.md](../using-the-feed.md)(영어)를 참고하세요. GL.iNet은 서명을 검증하지 않습니다. 신뢰할 수 있는 피드만 추가하세요.

## 구조

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

## 개발

```bash
python3 -m unittest discover tests -v   # tests
node tests/view-eval.js                 # GL.iNet view loads as a Vue component
tools/build-all --out site              # build the feed locally (GNU tar + jq, i.e. Linux/CI)
tests/opkg-install.sh site              # install/remove round-trip (needs docker)
```

패키징은 CI(Linux)에서 수행하며 macOS에서는 패키징 관련 테스트를 건너뜁니다. 빌드는 재현 가능합니다(`SOURCE_DATE_EPOCH`). 업스트림 패키지는 그대로 미러링되며 sha256이 저장소의 잠금 파일과 일치할 때만 배포됩니다. 새 버전을 배포하려면 `vX.Y.Z` 형식의 태그를 푸시합니다. 플러그인 추가는 [adding-a-plugin.md](../adding-a-plugin.md)(영어)를 참고하세요.

## 상태

테스트 완료: 도구 동작, 패키지 형식, 뷰 로딩. **실제 GL.iNet 라우터에서는 아직 검증하지 않았습니다.** [OpenClash 플러그인 문서](../../plugins/openclash/README.md)의 체크리스트대로 확인하세요.

## 라이선스

MIT. 미러링한 업스트림 패키지는 각자의 라이선스를 유지합니다(OpenClash: MIT).
