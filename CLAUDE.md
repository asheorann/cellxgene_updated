# CellxGene VIP Extension: Cell-Cell Communication

## Project Overview
Adding cell-cell communication (CCC) analysis to the CellxGene VIP viewer. Users select cell groupings and a condition split, run CCC analysis from the UI, and see which ligand-receptor pairs and pathways differ between conditions.

**Lab context**: This hosts the GutPath scRNA-seq atlas on Penn Vet's server/AWS EC2.

## Codebase

**Starting point**: Merged VIP + ParaCell (see `MERGE_ANALYSIS.md` for details)

The plan is to merge ParaCell's trajectory features into current VIP to get the most complete base. ParaCell is 126 commits behind VIP but added clean extensions.

### Keep Our Code Separate From Upstream (rule)
Code we add goes in **our own files**, never inside VIP's or cellxgene's files, so
upstream VIP updates can be pulled in with `tools/sync_vip_upstream.sh` without
fighting our changes.
- New backend code: `cellxgene_VIP/ccc.py` (or another new module next to it).
- New frontend code: `cellxgene_VIP/ccc.js` / `ccc.html` (or new files loaded the same way).
- Upstream files (`VIPInterface.py`, `interface.html`, `update.VIPInterface.sh`, R scripts, `cellxgene/`) only get minimal **hook lines** (an import, a dispatcher entry, a script loader, a `cp` line). Don't refactor, reformat or fix unrelated things in them.
- If a hook or upstream edit is unavoidable, log it in `CHANGES_FROM_UPSTREAM.md` and add a check for it in `tools/check_ccc_compat.py`.
- New VIP functions/state our code relies on also go in `check_ccc_compat.py`.

### Key Files
- `cellxgene_VIP/ccc.py`, `ccc.js`, `ccc.html` - **our CCC code** (backend, frontend logic, tab markup).
- `CHANGES_FROM_UPSTREAM.md` - every difference from upstream VIP/cellxgene/LIANA, and the upstream sync process.
- `tools/` - `sync_vip_upstream.sh`, `check_ccc_compat.py`, `test_ccc_backend.py`.
- `VIPInterface.py` - upstream backend dispatcher (~2000 lines). Hooks only.
- `interface.html` - upstream frontend UI (~6000 lines). Hooks only.
- `bin/` - R scripts for visualization (volcano.R, fgsea.R, etc.)

### Extension Pattern
```python
# 1. Add the function in ccc.py (or a new module of ours)
def CCC(data):
    adata = data['data_adapter'].data  # full AnnData
    # ... run analysis ...
    return json.dumps([csv, img, notes])   # or Msg("...") for errors

# 2. Hook: VIPInterface.py imports the module and registers it in distributeTask()
'CCC':ccc.CCC

# 3. Frontend in ccc.js / ccc.html - jQuery AJAX POST to VIPurl
```

### Data Access
- `data['data_adapter']` - Access to raw h5ad
- `data['cells']` - Dict of cell indices by group
- `data['genes']` - List of gene names
- `data['grp']` - Grouping category names
- `data['figOpt']` - Visualization options (DPI, fontsize, colormap)

## Open Technical Decisions

### R vs Python for CCC
- **CellChat** (R): More mature, but bridging to R adds operational cost
- **LIANA** (Python): Wraps multiple scoring methods, cleaner integration
- **CellPhoneDB** (Python): Well-established, good database
- **Squidpy** (Python): Has ligand-receptor function, good for spatial

**Next step**: Test LIANA and CellPhoneDB on same dataset, compare outputs.

### Ligand-Receptor Database
GutPath is **mouse data**. Database options:
- **CellChatDB**: Good mouse coverage, handles multi-subunit complexes
- **CellPhoneDB**: Primarily human, has mouse orthologs
- **OmniPath**: Broad coverage, verify mouse-specific curation

Filter databases by mouse support before committing.

## Merge Strategy: VIP + ParaCell

ParaCell is 448 commits ahead (trajectory features) but **126 commits behind** VIP master. Rather than choosing one, we merge both:

**From VIP (base):**
- Visium/CosMx spatial visualization
- `adata_to_df()` sparse matrix fix
- pandas/anndata compatibility fixes
- jQuery 3.7.1 security update

**From ParaCell (port):**
- 17 new functions (trajectory, host-parasite, gene search)
- `tsPlot.R` (TradeSeq visualization)
- Frontend tabs for new features

See `MERGE_ANALYSIS.md` for the full breakdown.

## Design Consideration: Uncertainty
CCC methods infer interactions from co-expression, not direct measurement. Results depend on annotation quality, cells per cluster, and null model choice. The UI should surface this uncertainty rather than presenting ranked lists as fact.

## Bug Policy
Fix only bugs on the path of CCC feature. Log others with reproduction steps - no open-ended cleanup.

## Open Items to Revisit
Active list, not just a log: raise these with the user when working nearby, and remove an item only when it's fixed (details and repro steps in `CHANGES_FROM_UPSTREAM.md` "Known issues").
1. **Single-condition view uses `.raw` without a normalization check** (added 2026-10-22). The comparison view checks layers (`CCCresolveLayer`), the single-condition path doesn't. Planned fix: reuse the layer dropdown and check there. Revisit before running on GutPath.
2. **Validate the comparison view on GutPath** before trusting it there: which layer is log-normalized, the mouse ID column, mice per condition per cell type at 30 cells. Layer-check cut-offs were calibrated on pbmc68k and synthetic data only.
3. **Differential analysis across replicates** (pseudobulk DESeq2 / `df_to_lr`): the comparison view's disclaimer says it is "not yet available"; update the banner (`ccc.js` `CCCshowBanner`) when it exists.
4. **Remove `CCCpatchLiana()`** once a LIANA release with the `rank_aggregate` fix can be installed (needs Python > 3.8).
5. "Cells to include" dropdown counts stuck at 0; `CCCbuildRequest()` ignores accumulate mode.

## Current Phase: Local Testing

Testing VIP and ParaCell side-by-side before merging.

```bash
# Terminal 1 - VIP
cd cellxgene_VIP
conda activate VIP
cellxgene launch ../data/test.h5ad --host 0.0.0.0 --port 5005

# Terminal 2 - ParaCell
cd paraCell
conda activate paraCell
cellxgene launch ../data/test.h5ad --host 0.0.0.0 --port 5006
```

Compare at http://localhost:5005 vs http://localhost:5006

## Future Work (not in current scope)
- UI bug fixes
- User data upload
- Spatial transcriptomics support
- Onboarding/AI guidance layer
