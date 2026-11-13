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
   PRs for new releases; nothing is published until you merge.
3. Package files: set `"dir": "glinet"` on a package and add
   - `plugins/example/glinet/root/...` files installed to `/`
   - `plugins/example/glinet/CONTROL/{preinst,postinst,prerm,postrm,conffiles}`
   - `"gzip": ["www/views/x.common.js"]` to ship a file as `.gz` (the source stays
     readable and testable in the repo).
   Packages must not overwrite files owned by firmware or other packages;
   `tests/test_tools.py` enforces an allow-list of install paths for GL.iNet packages.
   Packages are built by `tools/build-pkg` (GNU tar + jq), i.e. in CI.
4. Run the tests and `tools/build-all --out site`.

Feeds are just directory names (`feed`): keep firmware-specific packages in
their own feed so users of other firmwares never see them.
