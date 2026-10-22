# Changes From Upstream (VIP, cellxgene, LIANA)

Running log of everything this project changes relative to the original
software, and how to pull new upstream VIP versions. **Update this file with
every change** to VIP, cellxgene or how we use LIANA, newest changelog entries first.

## Baselines

| Component | Upstream | Version we're based on |
|-----------|----------|------------------------|
| cellxgene VIP | https://github.com/interactivereport/cellxgene_VIP | commit in `cellxgene_VIP/VIP_UPSTREAM` (currently `c0228348`, 2026-06-23) |
| cellxgene | https://github.com/chanzuckerberg/cellxgene | v1.1.1 @ `f48d06fb` (pinned in `cellxgene_VIP/config.sh`) |
| LIANA | https://github.com/saezlab/liana-py | installed from PyPI (`liana>=1.0.0`); CCC tested on 1.5.0 (VIP env) and 1.10.0 |
| ParaCell | `paraCell/` in this repo | **not merged yet**; none of its functions are in `cellxgene_VIP/` |

## Layout: our code lives in separate files

All CCC code is in our own files. VIP's files only contain small hooks, so
upstream updates rarely touch our code.

| Our file | Installed to | Contents |
|----------|--------------|----------|
| `cellxgene_VIP/ccc.py` | `server/app/` | Backend: `CCC()` and helpers |
| `cellxgene_VIP/ccc.js` | `server/common/web/static/` | Frontend logic; on load, inserts the tab button and `ccc.html` into the VIP panel |
| `cellxgene_VIP/ccc.html` | `server/common/web/static/` | CCC tab markup |
| `cellxgene_VIP/VIP_UPSTREAM` | — | Upstream commit we're based on (used by the sync script) |
| `tools/sync_vip_upstream.sh` | — | Pull upstream VIP changes (see below) |
| `tools/check_ccc_compat.py` | — | Check VIP still provides what CCC needs |
| `tools/test_ccc_backend.py` | — | Run `ccc.py` end to end on an h5ad |

## Edits to upstream VIP files

The **only** differences from upstream VIP. `tools/check_ccc_compat.py` checks that each hook is present.

| File | Change | Why |
|------|--------|-----|
| `VIPInterface.py` imports | `import server.app.ccc as ccc` | Hook: load the CCC backend |
| `VIPInterface.py` `distributeTask()` | `'CCC':ccc.CCC` | Hook: register the CCC request |
| `VIPInterface.py` `route()` | `app__identifier` read with `getattr(..., 'default')` | Bug fix: upstream crashes on every request when cellxgene wasn't patched with `app__identifier` |
| `interface.html` end of file | One `<script>` line: `$.getScript(.../static/ccc.js)` | Hook: load the CCC frontend |
| `update.VIPInterface.sh` | `cp ccc.py ...` and `cp ccc.js ccc.html ...` | Hook: install our files |

## What the CCC code does

### Backend (`ccc.py`)
| Function | Purpose |
|----------|---------|
| `CCC_METHODS`, `CCC_RESOURCES`, `CCC_LASSO_COL` | Map frontend values to LIANA method/resource names; temp obs column for lasso mode |
| `Msg()` | Calls VIP's `Msg()` (imported at call time to avoid a circular import) |
| `CCCpatchLiana()` | Runtime fix for a LIANA bug (see LIANA section) |
| `CCCtidyDotplot()` | Facets LIANA's dotplot by sender, drops empty columns, wraps long labels |
| `CCCguessSpecies()` | Mouse vs human from gene-symbol case (auto resource selection) |
| `CCCuseSymbols()` | Uses VIP's `var_index` gene-name column (X and raw) |
| `CCCscoreCols()` | Magnitude/specificity columns and sort direction per method |
| `CCCfilterGroups()` | Drops cell types below `min_cells` |
| `CCCwrap()` | Wraps long cell type names for plot labels |
| `CCClayerKeys/Matrix/Args()` | Expression layers (X, `.raw`, `adata.layers`) and the LIANA arguments to read one |
| `CCCcheckLayer()` | Is a layer log-normalized and depth-normalized? `ok` / `warn` / `fail` (see "Comparison view" below) |
| `CCClayerOptions()`, `CCCresolveLayer()` | Layer list with check results for the UI (`action: 'layers'`); pick and check the layer for a run |
| `CCCcompare()` | Condition comparison view (see below) |
| `CCCcomparisonPlot()` | Its dot plot: senders as panels, ref/test columns per target; stacked rows above 24 columns |
| `CCC()` | Cell subset or lasso groups → LIANA per condition → targeted filter → sort/top-N → `[csv, base64_png, notes]` |

Behaviour worth knowing:
- `import liana` happens inside `CCC()`, so a broken LIANA install disables only CCC, not all of VIP.
- Raw counts are used when `adata.raw` exists; otherwise X, with a warning.
- `n_perms < 100` turns permutations off.
- **Condition comparison:** see "Comparison view" below. (Before 2026-10-22 it plotted LIANA ranks from separate per-condition runs side by side, which isn't a valid comparison; removed.)

### Comparison view (`CCCcompare`)
Two conditions (reference, test), optionally with a replicate (mouse) column. Plots **absolute values**, not LIANA's within-run ranks, which can't be compared across runs.
- **Per replicate**, for each (ligand→receptor, sender, target, condition): `prop = min(ligand_props, receptor_props)`; `expr = (ligand_means + receptor_means) / 2`. Computed from LIANA's per-subunit columns, because `return_all_lrs=True` overwrites `lr_means` of below-threshold rows with a filler value (verified in LIANA 1.5.0).
- **A replicate counts** for a sender→target pair only with >= 30 cells (`CCC_SAMPLE_MIN_CELLS`, configurable) of both. Separate from LIANA's `expr_prop` (0.1); LIANA's `min_cells` is set to the same 30 so the two never disagree.
- **Plotted value** = mean across qualifying replicates, each weighted equally. Size = prop, colour = expr, one colour scale for both conditions.
- **Dot state**, with k = replicates where `prop >= 0.1`, out of n: `k = 0` → grey "–"; `3k >= 2n` → filled; otherwise → ring. For n = 3: k = 0 → "–", k = 1 → ring, k = 2 or 3 → filled. For n = 2: k = 1 → ring, k = 2 → filled.
- **Column flags:** n < 3 mice → orange "n=2 ⚠" header; n < 2 → grey "n/a" column (untargeted) or the run is blocked (targeted).
- **Guardrails:** each replicate must be in exactly one condition; mice counted per condition per cell type before running (UI preview and server); no sample column → cells pooled per condition, labelled "Descriptive view: no replicates".
- **Top N:** largest mean expression in either condition (neutral; never sorted by difference).
- **Layer:** user picks X / `.raw` / any `adata.layers` key, default Auto (first that passes the check). Shown in the UI, banner, plot caption and notes. `CCCcheckLayer` blocks negative values (scaled), mostly-integer values (raw counts), max > 50, and **layers where most cells share the same smallest non-zero value** (log of counts never normalized for depth: a count of 1 is log 2 in every cell). Calibration (2026-10-22): that last metric is 100% of cells for unnormalized data and 0% for normalized data, including gene subsets. The earlier row-sum CV idea was dropped: it scored correctly-normalized pbmc68k 0.20 and unnormalized even-depth data 0.26, so it couldn't separate them. Warns if values aren't log1p of per-cell-scaled counts.
- **Disclaimer:** orange banner above the results (`ccc.html` `#CCCbanner`) plus a caption drawn into the PNG.
- **Plotting:** matplotlib, not plotnine (column shading and header flags; plotnine 0.10 layout issues).
- **Lasso mode** (`compute.lasso_groups`): cells in Selection 1 and Selection 2 are labelled in `CCC_LASSO_COL`, other cells are dropped, and cells in both selections are excluded. Specificity is relative to the two selections only, and a note says so.

### Frontend (`ccc.js`, `ccc.html`)
- Tab button inserted before the CLI tab (falls back to the end of the tab bar); tab content inserted before the CLI tab content.
- Options: mode (targeted/untargeted), cells to include, cell type annotation, sender/receiver (annotation dropdowns or lasso selections, with Swap), direction, compare conditions (reference/test, replicate column, expression layer, replicate-count preview), top-N, advanced (method, resource, min cells, permutations, sort).
- Lasso mode: "Use current lasso" buttons store the current lasso as Selection 1/2, using the same Redux action as cellxgene's 1/2 menubar buttons.
- `CCCinit()` runs each time the tab opens and keeps the current annotation choices.
- Results: DataTable, CSV export, figure, server notes; comparison-view disclaimer banner.
- Uses from VIP: `selFun`, `getCells`, `cellNupdate`, `showImg`, `hideShow`, `VIPurl`, `window.figOpt`, `window.accumulateCell`, `window.store`, DataTables, d3.

## cellxgene (vendored at `cellxgene_VIP/cellxgene/`, v1.1.1)

| File | Change | Why |
|------|--------|-----|
| `client/index_template.html` | VIP's `index_template.insert` added before `<div id="root">` | Standard VIP install step (`config.sh` `sed`). Applied **once**; the `sed` is not idempotent |
| `client/package.json` | `prepare`: `husky install` → `(husky install client/.husky \|\| true)` | husky needs `cellxgene/.git`, which doesn't exist inside our repo, so `npm ci` failed |

Build workarounds (`PROJECT_ROOT=$PWD`, `NODE_OPTIONS=--openssl-legacy-provider`) are environment settings, not code changes; see `SETUP_NOTES.md`.

## LIANA

**The LIANA package itself is not modified** (no fork, no edited files).

### Runtime patch
`CCCpatchLiana()` wraps `liana.method._pipe_utils._aggregate._rank_aggregate` so each
score column is ranked only once. In LIANA 1.5.0 and 1.10.0, NATMI and Connectome
share `expr_prod`, which was ranked twice. That reversed its order and corrupted
`magnitude_rank`, so the weakest interactions looked strongest. Applied once per
process. **Remove when we can install a LIANA release with the fix** (needs newer
Python than VIP's 3.8). `tools/test_ccc_backend.py` exercises it.

### Usage choices (differ from a plain `li.mt.<method>(adata, groupby)` call)
- Resource: `auto` → `mouseconsensus` for mouse gene symbols, `consensus` for human. A note appears if the resource and the gene symbols disagree.
- `expr_prop=0.1`, `use_raw` from whether `adata.raw` exists, `verbose=False`.
- Cell types below `min_cells` (default 20) are removed **before** LIANA runs, which changes specificity scores; the UI lists what was dropped.
- Sender→receiver filtering happens after LIANA runs, not via LIANA's source/target arguments.
- Single-condition view: top-N picks each interaction's best score.
- Comparison view: `li.mt.cellphonedb` (not `rank_aggregate`: in 1.5.0 it has no `supp_columns`, so it can't return proportions) with `supp_columns=[ligand/receptor props and means]`, `return_all_lrs=True`, `n_perms=None`, `groupby_pairs`, run once per replicate in our own loop. Not `cellphonedb.by_sample`: in 1.5.0 the whole call fails (`No objects to concatenate`) if any one replicate lacks a cell type.

---

## Pulling upstream VIP

Our copy of VIP has no upstream git history, so `tools/sync_vip_upstream.sh` does a
**three-way merge per file**: the upstream commit we're based on
(`VIP_UPSTREAM`), our current file, and upstream's new version.

- Files we never changed are replaced with upstream's version.
- Files both sides changed are merged with `git merge-file`. Only edits to the same lines conflict, marked with `<<<<<<<`.
- Files added/deleted upstream are added/deleted, unless we changed them.
- Paths missing from our repo (gitignored, e.g. `jspanel/dist/`) are skipped and listed.

### Steps (in WSL, VIP conda env active, from the repo root)
```bash
git checkout -b vip-sync            # clean tree required; keeps the sync reviewable
bash tools/sync_vip_upstream.sh     # or: bash tools/sync_vip_upstream.sh <commit>
```
1. **Conflicts:** fix every file listed under CONFLICTS (search for `<<<<<<<`). Usually one of our hook lines next to an upstream edit: keep both.
2. **Compatibility:** `python tools/check_ccc_compat.py` must say "All required checks passed". A FAIL means VIP renamed or removed something CCC uses: fix `ccc.js`/`ccc.py`, not VIP.
3. **Review:** `git diff -- cellxgene_VIP` to see what upstream changed.
4. **Backend test:** `python tools/test_ccc_backend.py data/pbmc68k_reduced.h5ad`.
5. **Browser smoke test:** `cd cellxgene_VIP && ./update.VIPInterface.sh`, launch cellxgene, hard-refresh, then:
   - CCC tab appears before "Command Line Interface"; no errors in the browser console (F12)
   - Targeted, annotation mode: pick sender/receiver, Run → table + figure
   - Lasso mode: lasso → "Use current lasso" for sender and receiver → Swap → Run
   - Compare conditions with 2 conditions → comparison figure
   - Export CSV downloads
   - Another VIP tab (e.g. Violin) still works
6. **If upstream changed `config.sh`'s cellxgene version** (the script warns): also re-check the cellxgene store fields `ccc.js` uses (listed by `check_ccc_compat.py`), and the cellxgene changes above.
7. Commit (include `VIP_UPSTREAM`), add a changelog entry here, merge the branch.

To abandon a sync: `git checkout -- cellxgene_VIP && git clean -fd cellxgene_VIP` on the sync branch.

**Rehearsal (2026-10-22):** in a throwaway copy, with `VIP_UPSTREAM` set back to a
Feb 2025 commit, syncing to `c0228348` merged ~150 changed lines of upstream
`VIPInterface.py`/`interface.html` automatically. It produced one conflict, on the
`setTimeStamp` line where upstream and our `app__identifier` fix both changed the
same line, and `check_ccc_compat.py` flagged it.

How often to sync: upstream changes `VIPInterface.py`/`interface.html` a few times
a year (33 commits touching them since 2024). Check every few months, or when there's an upstream
fix we want.

---

## Repository-level differences (not code changes)

- `.gitignore` excludes `dist/` and `build/`, so upstream's `jspanel/dist/` and `vipdocker/build/` are **not in our repo**. jsPanel is loaded from `interactivereport.github.io` at runtime, so VIP still works, but the Docker build files are missing.
- `.gitattributes` (`* text=auto eol=lf`) keeps LF line endings on Windows. The sync script relies on this; CRLF files would conflict on every line.
- `cellxgene_VIP/cellxgene/` is vendored (upstream VIP clones it during install).

## Known issues (not fixed, per bug policy)

Items we intend to come back to are also listed under "Open items to revisit" in `CLAUDE.md`.

- **Single-condition view uses `.raw` unchecked.** `CCC()` uses `adata.raw` whenever it exists, without the comparison view's layer check. If `.raw` holds raw counts, `lr_means`-based scores are on counts and depth differences leak into magnitude. The nearby `sample_max < 20` check only prints a message and its comment ("Check for raw counts") describes the opposite of what it tests. Repro: an h5ad whose `.raw` is integer counts; run a single-condition CCC; `lr_means` in the CSV are on count scale. Fix: reuse `CCCresolveLayer()` and the layer dropdown for the single-condition path.

- **"Cells to include" dropdown counts are stuck at 0.** The HTML parser drops `<span class="cellN1">` inside `<option>` (`ccc.html`), so `cellNupdate()` has nothing to update. Repro: store cells in Selection 1, open the CCC tab, look at the dropdown.
- **`CCCbuildRequest()` ignores accumulate mode.** It reads `store.differential` before `window.accumulateCell`, so with "accumulate selections" on, CCC with "Selection 1/2" uses only the last selection. Repro: turn accumulate on, add two lassos to Selection 1, run CCC with "Selection 1"; the cell count doesn't match. Lasso mode uses `getCells()` and is not affected.

---

## Changelog

### 2026-10-22
- **Comparison view rebuilt** (see "Comparison view"): absolute values averaged across replicates instead of ranks from separate runs; reference/test + replicate column + expression layer controls; replicate-count preview and guardrails; three dot states + column flags; disclaimer banner and plot caption. Removed `CCCcomparePlot()` and the condition checkboxes.
- `tools/test_ccc_backend.py` now also tests the layer check calibration cases and the comparison view guardrails.
- Moved all CCC code out of VIP files into `ccc.py`, `ccc.js`, `ccc.html`. VIP files now differ from upstream only by the hooks listed above. The CCC tab is now inserted by `ccc.js`, and `CCCinit()` runs when the tab is opened (previously from VIP's page init).
- Added `VIP_UPSTREAM`, `tools/sync_vip_upstream.sh`, `tools/check_ccc_compat.py`, `tools/test_ccc_backend.py`.
- Lasso mode for sender/receiver: toggle, Swap, "Use current lasso" buttons; backend `lasso_groups`.
- Swap button for annotation-based sender/receiver.
- Created this log.

### Before 2026-10-22 (from `SETUP_NOTES.md`)
- Fixed original CCC code: lowercase LIANA resource names, added mouse resource, method dropdown now used, condition comparison now used, `import liana` moved inside `CCC()`.
- Added `CCCpatchLiana()` LIANA workaround.
- `app__identifier` `getattr` fallback; husky `|| true`; template patched once.
