"""
Test CCC (Cell-Cell Communication) analysis on cardiac h5ad data.
Simulates what VIPInterface.py CCC function does.
"""
import scanpy as sc
import liana as li
import pandas as pd
import numpy as np
import os

# Output directory
os.makedirs('ccc_output', exist_ok=True)

print("=" * 60)
print("CCC Test: Cardiac MI vs Normal Dataset")
print("=" * 60)

# 1. Load data
print("\n[1/6] Loading h5ad file...")
adata = sc.read_h5ad('data/4780eb7d-4c7c-4630-8705-471f0de8e27a.h5ad')
print(f"    Shape: {adata.shape[0]:,} cells x {adata.shape[1]:,} genes")

# 2. Check gene names - LIANA needs gene symbols, not Ensembl IDs
print("\n[2/6] Preparing gene names...")
if adata.var_names[0].startswith('ENSG'):
    print("    Gene IDs are Ensembl, converting to symbols...")
    if 'feature_name' in adata.var.columns:
        # Use feature_name as gene symbols
        adata.var['ensembl_id'] = adata.var_names
        adata.var_names = adata.var['feature_name'].astype(str)
        adata.var_names_make_unique()
        print(f"    Sample genes: {adata.var_names[:5].tolist()}")
    else:
        print("    WARNING: No feature_name column found!")

# 3. Set up groupby (cell types)
groupby = 'cell_type'
print(f"\n[3/6] Cell type distribution ({groupby}):")
cell_counts = adata.obs[groupby].value_counts()
for ct, count in cell_counts.items():
    print(f"    {ct}: {count:,}")

# Filter to cell types with enough cells (min 50 for testing)
min_cells = 50
valid_groups = cell_counts[cell_counts >= min_cells].index.tolist()
print(f"\n    Keeping {len(valid_groups)} cell types with >= {min_cells} cells")
adata = adata[adata.obs[groupby].isin(valid_groups)].copy()
print(f"    Filtered shape: {adata.shape[0]:,} cells")

# 4. Subsample for faster testing (optional - comment out for full run)
print("\n[4/6] Subsampling for test run...")
n_sample = 20000  # Use 20k cells for testing
if adata.shape[0] > n_sample:
    sc.pp.subsample(adata, n_obs=n_sample, random_state=42)
    print(f"    Subsampled to {adata.shape[0]:,} cells")
    # Recheck cell type counts after subsampling
    cell_counts = adata.obs[groupby].value_counts()
    valid_groups = cell_counts[cell_counts >= min_cells].index.tolist()
    adata = adata[adata.obs[groupby].isin(valid_groups)].copy()
    print(f"    After filtering: {adata.shape[0]:,} cells, {len(valid_groups)} cell types")

# 5. Run LIANA
print("\n[5/6] Running LIANA rank_aggregate...")
print("    This may take a few minutes...")

# Check if raw counts are available
use_raw = adata.raw is not None
print(f"    Using raw counts: {use_raw}")

try:
    li.mt.rank_aggregate(
        adata,
        groupby=groupby,
        resource_name='consensus',  # Good default resource
        expr_prop=0.1,              # Min proportion of cells expressing
        use_raw=use_raw,
        n_perms=None,               # Skip permutation for speed
        verbose=True
    )
    print("    LIANA completed successfully!")
except Exception as e:
    print(f"    ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# 6. Extract and save results
print("\n[6/6] Extracting results...")

if 'liana_res' not in adata.uns:
    print("    ERROR: No liana_res found in adata.uns")
    exit(1)

liana_res = adata.uns['liana_res']
print(f"    Found {len(liana_res):,} ligand-receptor interactions")

# Sort by magnitude rank
liana_res = liana_res.sort_values('magnitude_rank', ascending=True)

# Save full results
liana_res.to_csv('ccc_output/ccc_full_results.csv', index=False)
print("    Saved: ccc_output/ccc_full_results.csv")

# Save top 50 for quick viewing
top_50 = liana_res.head(50)
top_50.to_csv('ccc_output/ccc_top50.csv', index=False)
print("    Saved: ccc_output/ccc_top50.csv")

# Print top 10 interactions
print("\n" + "=" * 60)
print("TOP 10 LIGAND-RECEPTOR INTERACTIONS")
print("=" * 60)
cols_to_show = ['source', 'target', 'ligand_complex', 'receptor_complex', 'magnitude_rank']
cols_to_show = [c for c in cols_to_show if c in liana_res.columns]
print(liana_res[cols_to_show].head(10).to_string(index=False))

# 7. Create visualization
print("\n[7/7] Creating visualization...")
try:
    # Get unique cell types in top results
    top_for_plot = liana_res.head(100)
    source_labels = top_for_plot['source'].unique().tolist()[:5]  # Limit for clarity
    target_labels = top_for_plot['target'].unique().tolist()[:5]

    fig = li.pl.dotplot(
        adata=adata,
        colour='magnitude_rank',
        size='specificity_rank' if 'specificity_rank' in liana_res.columns else 'magnitude_rank',
        inverse_colour=True,
        inverse_size=True,
        source_labels=source_labels,
        target_labels=target_labels,
        top_n=30,
        orderby='magnitude_rank',
        orderby_ascending=True,
        return_fig=True
    )

    fig.save('ccc_output/ccc_dotplot.png', dpi=150)
    print("    Saved: ccc_output/ccc_dotplot.png")
except Exception as e:
    print(f"    Plot failed (non-critical): {e}")

print("\n" + "=" * 60)
print("CCC TEST COMPLETE")
print("=" * 60)
print("\nOutput files in ccc_output/:")
print("  - ccc_full_results.csv  (all interactions)")
print("  - ccc_top50.csv         (top 50 by magnitude)")
print("  - ccc_dotplot.png       (visualization)")
