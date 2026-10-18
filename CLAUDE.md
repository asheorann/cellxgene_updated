# CellxGene VIP Extension: Cell-Cell Communication

## Project Overview
Adding cell-cell communication (CCC) analysis to the CellxGene VIP viewer. Users select cell groupings and a condition split, run CCC analysis from the UI, and see which ligand-receptor pairs and pathways differ between conditions.

**Lab context**: This hosts the GutPath scRNA-seq atlas on Penn Vet's server/AWS EC2.

## Codebase

**Starting point**: Merged VIP + ParaCell (see `MERGE_ANALYSIS.md` for details)

The plan is to merge ParaCell's trajectory features into current VIP to get the most complete base. ParaCell is 126 commits behind VIP but added clean extensions.

### Key Files
- `VIPInterface.py` - Backend analysis dispatcher (~2000 lines). Add new analysis functions here.
- `interface.html` - Frontend UI (~6000 lines). Add UI controls and AJAX calls here.
- `bin/` - R scripts for visualization (volcano.R, fgsea.R, etc.)

### Extension Pattern
```python
# 1. Add function in VIPInterface.py
def CCC(data):
    adata = createData(data)  # Get AnnData slice
    # ... run analysis ...
    return iostreamFig(fig)   # or json.dumps(results)

# 2. Register in distributeTask() dict at line 290
'CCC': CCC,

# 3. Add frontend in interface.html - jQuery AJAX POST to VIPurl
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
