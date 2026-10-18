#!/usr/bin/env python
"""
Standalone LIANA test script.
Tests cell-cell communication analysis on the PBMC3k dataset.
"""

import time
import warnings
warnings.filterwarnings('ignore')

import anndata as ad
import liana as li
import pandas as pd

# Path to test data
DATA_PATH = '/mnt/c/Users/anush/projects/cellxgene_updated/data/scanpy-pbmc3k.h5ad'
OUTPUT_DIR = '/mnt/c/Users/anush/projects/cellxgene_updated/ccc_worker'

def main():
    print("=" * 60)
    print("LIANA Test Script")
    print("=" * 60)
    print(f"LIANA version: {li.__version__}")
    print()

    # Load data
    print("Loading data...")
    adata = ad.read_h5ad(DATA_PATH)
    print(f"Dataset shape: {adata.shape}")
    print(f"Groupby categories (leiden): {adata.obs['leiden'].unique().tolist()}")
    print()

    # Run with permutations (n_perms=1000)
    print("=" * 60)
    print("Running LIANA with n_perms=1000...")
    print("=" * 60)

    start_time = time.time()
    li.mt.rank_aggregate(
        adata,
        groupby='leiden',
        resource_name='consensus',
        expr_prop=0.1,
        use_raw=True,
        n_perms=1000,
        verbose=True
    )
    runtime_perms = time.time() - start_time
    print(f"\nRuntime with n_perms=1000: {runtime_perms:.2f} seconds")
    print()

    # Save results from permutation run
    results_perms = adata.uns['liana_res'].copy()

    # Run without permutations (n_perms=None)
    print("=" * 60)
    print("Running LIANA with n_perms=None...")
    print("=" * 60)

    start_time = time.time()
    li.mt.rank_aggregate(
        adata,
        groupby='leiden',
        resource_name='consensus',
        expr_prop=0.1,
        use_raw=True,
        n_perms=None,
        verbose=True
    )
    runtime_no_perms = time.time() - start_time
    print(f"\nRuntime with n_perms=None: {runtime_no_perms:.2f} seconds")
    print()

    # Analyze results
    print("=" * 60)
    print("Results Analysis")
    print("=" * 60)

    liana_res = adata.uns['liana_res']
    print(f"\nResult columns: {liana_res.columns.tolist()}")
    print(f"\nResult shape: {liana_res.shape}")
    print(f"\nTop 10 rows:")
    print(liana_res.head(10).to_string())
    print()

    # Save full results to CSV
    csv_path = f"{OUTPUT_DIR}/liana_results.csv"
    liana_res.to_csv(csv_path, index=False)
    print(f"Full results saved to: {csv_path}")
    print()

    # Filter and create dotplot
    print("=" * 60)
    print("Creating dotplot for source=0, target=1")
    print("=" * 60)

    # Filter results
    filtered = liana_res[(liana_res['source'] == '0') & (liana_res['target'] == '1')]
    print(f"Filtered results shape: {filtered.shape}")

    if len(filtered) > 0:
        # Create dotplot
        png_path = f"{OUTPUT_DIR}/liana_dotplot.png"

        # Check available columns for plotting
        print(f"Available columns: {liana_res.columns.tolist()}")

        # Use magnitude_rank for both if specificity_rank not available
        size_col = 'specificity_rank' if 'specificity_rank' in liana_res.columns else 'magnitude_rank'
        print(f"Using size column: {size_col}")

        # Use the filtered data for plotting
        # Note: Need to run with n_perms to get specificity_rank
        fig = li.pl.dotplot(
            adata=adata,
            colour='magnitude_rank',
            size=size_col,
            inverse_colour=True,
            inverse_size=True,
            source_labels=['0'],
            target_labels=['1'],
            top_n=20,
            orderby='magnitude_rank',
            orderby_ascending=True,
            return_fig=True
        )
        fig.save(png_path, dpi=150)
        print(f"Dotplot saved to: {png_path}")
    else:
        print("No interactions found for source=0, target=1")
        png_path = None

    # Summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Runtime with n_perms=1000: {runtime_perms:.2f} seconds")
    print(f"Runtime with n_perms=None: {runtime_no_perms:.2f} seconds")
    print(f"Speed difference: {runtime_perms / runtime_no_perms:.1f}x slower with permutations")
    print(f"Total interactions found: {len(liana_res)}")
    print(f"CSV path: {csv_path}")
    if png_path:
        print(f"PNG path: {png_path}")

if __name__ == '__main__':
    main()
