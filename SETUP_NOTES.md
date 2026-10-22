# Setup Notes: What Breaks and Why

A log of every problem hit while setting up VIP + CCC on a fresh Windows laptop
(Oct 2026), with the cause and the fix. Use it to make setup repeatable for new
lab members and to plan hosting on the Penn Vet server / AWS EC2.

## Summary

Setup is fragile because we are building a **2021-era stack** (cellxgene 1.1.1,
Python 3.8, webpack 4, Node 16) on 2026 tooling, from a cellxgene source tree
that is **vendored inside our own git repo**. Almost every failure below traces
back to one of those two facts.

## Problems hit, in order

| # | Symptom | Cause | Fix applied / workaround |
|---|---------|-------|--------------------------|
| 1 | `conda` not found on Windows | VIP needs bash, make, sed, cpio; it cannot build natively on Windows | Use WSL (Ubuntu) + Miniconda inside WSL |
| 2 | Docs/scripts point at `/mnt/c/Users/anush/...` | `QUICKSTART.md`, `launch_vip.sh`, `ccc_worker/test_ccc_backend.py` hardcode the original laptop's paths | Not fixed. Use relative paths or an env var |
| 3 | `env: 'bash\r': No such file or directory` | Git on Windows (`core.autocrlf=true`) checked files out with CRLF line endings | **Fixed:** added `.gitattributes` (`* text=auto eol=lf`) and converted the working tree |
| 4 | `conda activate VIP` → `EnvironmentNameNotFound` | Env is never created by any script | `conda create -n VIP -c conda-forge python=3.8 nodejs=16` |
| 5 | VIP block duplicated in `client/index_template.html` | The `sed` template patch from `config.sh` is not idempotent and was run twice | **Fixed:** template reset and patched once. Don't run the `sed` step again |
| 6 | `jq: Could not open .../cellxgene_updated/environment.default.json` | cellxgene's `common.mk` finds its root via `git rev-parse --show-toplevel`, which returns *our* repo root, not `cellxgene/` | Pass `PROJECT_ROOT=$PWD` to `make` |
| 7 | `husky install` → `.git can't be found`, `npm ci` fails | Same cause: husky expects `cellxgene/.git`. `HUSKY=0` does not help in husky 7.0.4 | **Fixed:** `client/package.json` `prepare` now ends in `|| true` |
| 8 | Wall of `cp: cannot create ... site-packages/server/...` | `update.VIPInterface.sh` ran after the build had already failed | Chain the steps with `&&` |
| 9 | `error:0308010C:digital envelope routines::unsupported` | webpack 4 uses an MD4 hash that OpenSSL 3 disables (conda's Node links OpenSSL 3) | `export NODE_OPTIONS=--openssl-legacy-provider` |
| 10 | Every retry takes several extra minutes | `make pydist` runs `clean`, which deletes `node_modules`; building on `/mnt/c` from WSL is slow | Accept it, or build from a copy under `~/` |
| 11 | (pending) liana on Python 3.8 | VIP is pinned to Python 3.8 + old numpy/pandas; recent liana needs newer Python. The CCC code was tested on liana 1.10 / Python 3.12 only | Check the version pip picks; re-test CCC against it |

## Other risks found along the way

- **Version pins** (from `QUICKSTART.md`): Flask 2.0.3, Werkzeug 2.0.3,
  pandas 1.5.3, numpy <= 1.22, rpy2 3.3.5. Upgrading any of them breaks cellxgene/VIP.
- **92 npm vulnerabilities** (5 critical) in the cellxgene 1.1.1 client
  dependencies. Not a problem locally, but a concern for a public-facing host.
  `npm audit fix` will likely break the build.
- **Runtime CDN dependency:** `index_template.insert` loads jQuery, d3 and
  jsPanel from `interactivereport.github.io` and `d3js.org` at page load. If those
  go down or move, the VIP panel breaks. A hosted version should serve them locally.
- **Miniconda installer** (`Miniconda3-latest-Linux-x86_64.sh`) sits untracked in
  the repo root and in `cellxgene_VIP/`. It should not be committed; add to `.gitignore`.
- **Original CCC code bugs** (fixed Oct 2026 in `VIPInterface.py`): non-lowercase
  LIANA resource names, no mouse resource, method dropdown ignored, condition
  comparison ignored, top-level `import liana` could take down all of VIP.
- **liana `rank_aggregate` bug** (present in 1.5.0 and 1.10.0): NATMI and Connectome
  share the `expr_prod` column, which is ranked twice, reversing its order and
  corrupting `magnitude_rank`. The GitHub fix needs a newer Python than our 3.8 env,
  so `CCCpatchLiana()` in `VIPInterface.py` works around it. Remove the patch once
  we can run a fixed liana release.

## Recommendations

### For new lab members (short term)
1. Commit the already-patched `index_template.html` (done in working tree) so nobody runs the `sed` step.
2. Write a single `setup_wsl.sh` that does env creation → build (with `PROJECT_ROOT`, `NODE_OPTIONS`) → `update.VIPInterface.sh` → version pins → liana, stopping on the first error.
3. Replace hardcoded `/mnt/c/Users/anush` paths with paths relative to the repo.

### Avoid rebuilding at all
The Node/webpack build is the source of problems 6, 7, 9 and 10, and its output is
the same every time. **Build it once and keep the result**: `make pydist` produces
`cellxgene/dist/cellxgene-1.1.1.tar.gz`. Store that file (release asset or shared
drive), and everyone else just runs `pip install cellxgene-1.1.1.tar.gz` and
`update.VIPInterface.sh`. No Node, npm or webpack needed.

### For hosting (Penn Vet server / EC2)
Use **Docker**. Bake the fixes above into an image: Ubuntu + Miniconda + Python 3.8
env, the prebuilt cellxgene tarball, VIP files, pinned versions, liana, and a
pre-warmed LIANA resource cache. The existing `cellxgene_VIP/Dockerfile` builds from
upstream VIP and has neither liana nor our CCC changes, so it needs updating. Also
plan to serve the CDN scripts locally and decide what to do about the npm
vulnerabilities before exposing the server publicly.
