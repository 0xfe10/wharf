# Adding a plugin

1. `plugins/<name>/plugin.json` (the directory name must equal `name`):

   ```json
   {
     "name": "example",
     "upstream": {"repo": "owner/repo", "asset": "^example_.+_all\\.ipk$",
                  "package": "example", "feed": "generic"},
     "packages": [
       {"name": "wharf-example", "version": "1.0.0-1", "feed": "generic",
        "depends": ["example"], "description": "One line\nLonger text"}
     ]
   }
   ```

   `upstream` is optional. When present, the release asset must be a single
   architecture-independent (`Architecture: all`) ipk from a GitHub release
   that publishes a sha256 digest.
2. Pin it: `tools/fetch-upstream --plugin example --update` writes
   `upstream.lock.json`. Commit it. The weekly `track-upstream` workflow opens
   PRs for new releases; nothing is published until you merge *and* push a release tag (see Releasing).
3. Package files: set `"dir": "glinet"` on a package and add
   - `plugins/example/glinet/root/...` files installed to `/`
   - `plugins/example/glinet/CONTROL/{preinst,postinst,prerm,postrm,conffiles}`
   - `"gzip": ["www/views/x.common.js"]` to ship a file as `.gz` (the source stays
     readable and testable in the repo).
   Packages must not overwrite files owned by firmware or other packages;
   `tests/test_tools.py` enforces an allow-list of install paths for GL.iNet packages.
   Packages are built by `tools/build-pkg` (GNU tar + jq), i.e. in CI.
4. Run the tests and `tools/build-all --out site`.

`feed` only groups build output: every package ends up in the single published
feed. Firmware-specific packages must therefore depend on something that exists
only on that firmware (e.g. `gl-sdk4-ui-core`) so they cannot be installed elsewhere.

## Releasing

Releases are tags `vX.Y.Z` (the release title is the tag):

```sh
git tag v1.0.1 && git push origin v1.0.1
```

The `release` workflow tests, builds, runs the opkg round-trip and creates the
GitHub release with all packages and the index. Routers use
`releases/latest/download`, so the newest release is picked up automatically.
