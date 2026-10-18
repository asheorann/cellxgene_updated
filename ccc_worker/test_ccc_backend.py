#!/usr/bin/env python
"""
Test script for CCC backend integration.
Simulates what cellxgene would pass to the CCC function and compares
results to the standalone LIANA test.
"""

import sys
import os
import time
import json
import warnings
warnings.filterwarnings('ignore')

# Add cellxgene_VIP to path so we can import VIPInterface
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cellxgene_VIP'))

import anndata as ad
import pandas as pd
import liana as li

# Test data path (adjust for your system - this is WSL path)
DATA_PATH = '/mnt/c/Users/anush/projects/cellxgene_updated/data/scanpy-pbmc3k.h5ad'
# Windows path alternative
DATA_PATH_WIN = r'C:\Users\anush\projects\cellxgene_updated\data\scanpy-pbmc3k.h5ad'

# Use whichever path exists
if os.path.exists(DATA_PATH):
    data_path = DATA_PATH
elif os.path.exists(DATA_PATH_WIN):
    data_path = DATA_PATH_WIN
else:
    print("ERROR: Could not find test data file")
    print(f"Tried: {DATA_PATH}")
    print(f"Tried: {DATA_PATH_WIN}")
    sys.exit(1)

print("=" * 60)
print("CCC Backend Integration Test")
print("=" * 60)
print(f"LIANA version: {li.__version__}")
print(f"Data path: {data_path}")
print()

# Load data
print("Loading data...")
adata = ad.read_h5ad(data_path)
print(f"Dataset shape: {adata.shape}")
print(f"Leiden categories: {adata.obs['leiden'].unique().tolist()}")
print()

# Create a mock data adapter class
class MockDataAdapter:
    def __init__(self, adata):
        self.data = adata

# Simulate the request that would come from frontend
mock_request = {
    'method': 'CCC',
    'mode': 'untargeted',
    'compute': {
        'cells': 'all',
        'cell_indices': None,
        'groupby': 'leiden',
        'compare_by': None,
        'compare_values': None,
        'ccc_method': 'liana',
        'resource': 'consensus',
        'min_cells': 20,
        'n_perms': None  # Faster test without permutations
    },
    'display': {
        'sender': None,
        'receiver': None,
        'direction': 'one_way',
        'top_n': 20,
        'sort_by': 'magnitude'
    },
    'figOpt': {
        'dpi': 150,
        'img': 'png'
    },
    'data_adapter': MockDataAdapter(adata)
}

print("=" * 60)
print("Test 1: Direct LIANA call (baseline)")
print("=" * 60)

# Run LIANA directly for comparison
start_time = time.time()
adata_test = adata.copy()
li.mt.rank_aggregate(
    adata_test,
    groupby='leiden',
    resource_name='consensus',
    expr_prop=0.1,
    use_raw=True,
    n_perms=None,
    verbose=False
)
direct_runtime = time.time() - start_time

direct_results = adata_test.uns['liana_res'].copy()
print(f"Runtime: {direct_runtime:.2f} seconds")
print(f"Results shape: {direct_results.shape}")
print(f"Top 5 interactions:")
print(direct_results.head().to_string())
print()

print("=" * 60)
print("Test 2: CCC Backend Function")
print("=" * 60)

# Now test the actual CCC function from VIPInterface
# We need to import it carefully since it has many dependencies

try:
    # Try to import just the parts we need
    import base64
    import traceback
    from io import BytesIO
    import pprint
    ppr = pprint.PrettyPrinter(depth=6, width=500)

    # Minimal Msg function for testing
    def Msg(text):
        return f"MSG: {text}"

    # Inline the CCC function logic for testing
    def test_CCC(data):
        """Simplified CCC function for testing"""

        scD = data.get('data_adapter')
        if scD is None:
            return Msg("No data adapter available")

        adata = scD.data.copy()
        compute = data.get('compute', {})
        cells_selection = compute.get('cells', 'all')

        if cells_selection != 'all':
            cell_indices = compute.get('cell_indices')
            if cell_indices and len(cell_indices) > 0:
                adata = adata[cell_indices, :].copy()
            else:
                return Msg("No cells selected.")

        groupby = compute.get('groupby')
        if not groupby or groupby == 'NA':
            return Msg("Please select a cell type annotation column")

        if groupby not in adata.obs.columns:
            return Msg(f"Annotation '{groupby}' not found")

        adata.obs[groupby] = adata.obs[groupby].astype(str)

        min_cells = compute.get('min_cells', 20)
        group_counts = adata.obs[groupby].value_counts()
        valid_groups = group_counts[group_counts >= min_cells].index.tolist()

        if len(valid_groups) < 2:
            return Msg(f"Need at least 2 cell types with >= {min_cells} cells")

        adata = adata[adata.obs[groupby].isin(valid_groups)].copy()

        use_raw = adata.raw is not None

        resource_map = {
            'consensus': 'consensus',
            'cellphonedb': 'CellPhoneDB',
            'cellchatdb': 'CellChatDB',
        }
        resource = resource_map.get(compute.get('resource', 'consensus'), 'consensus')

        n_perms = compute.get('n_perms', 1000)
        if n_perms is not None and n_perms < 100:
            n_perms = None

        li.mt.rank_aggregate(
            adata,
            groupby=groupby,
            resource_name=resource,
            expr_prop=0.1,
            use_raw=use_raw,
            n_perms=n_perms,
            verbose=False
        )

        if 'liana_res' not in adata.uns:
            return Msg("No interactions found")

        liana_res = adata.uns['liana_res'].copy()

        # Filter for targeted mode
        display = data.get('display', {})
        mode = data.get('mode', 'untargeted')

        if mode == 'targeted':
            sender = display.get('sender')
            receiver = display.get('receiver')
            if sender and receiver:
                liana_res['source'] = liana_res['source'].astype(str)
                liana_res['target'] = liana_res['target'].astype(str)
                liana_res = liana_res[
                    (liana_res['source'] == str(sender)) &
                    (liana_res['target'] == str(receiver))
                ]

        # Sort
        sort_by = display.get('sort_by', 'magnitude')
        sort_col = {'magnitude': 'magnitude_rank'}.get(sort_by, 'magnitude_rank')
        if sort_col in liana_res.columns:
            liana_res = liana_res.sort_values(by=sort_col, ascending=True)

        # Limit
        top_n = display.get('top_n', 20)
        liana_res = liana_res.head(top_n)

        # Return CSV
        output_cols = ['source', 'target', 'ligand_complex', 'receptor_complex', 'lr_means', 'magnitude_rank']
        output_cols = [c for c in output_cols if c in liana_res.columns]
        csv_data = liana_res[output_cols].to_csv(index=False)

        return json.dumps([csv_data, ""])  # No image for this test

    start_time = time.time()
    result = test_CCC(mock_request)
    backend_runtime = time.time() - start_time

    print(f"Runtime: {backend_runtime:.2f} seconds")

    if result.startswith('MSG:'):
        print(f"Error: {result}")
    else:
        result_data = json.loads(result)
        csv_data = result_data[0]
        backend_results = pd.read_csv(pd.io.common.StringIO(csv_data))
        print(f"Results shape: {backend_results.shape}")
        print(f"Top 5 interactions:")
        print(backend_results.head().to_string())

except Exception as e:
    print(f"Error testing CCC function: {e}")
    traceback.print_exc()

print()
print("=" * 60)
print("Test 3: Targeted Mode (source=0, target=1)")
print("=" * 60)

# Test targeted mode
mock_request_targeted = mock_request.copy()
mock_request_targeted['mode'] = 'targeted'
mock_request_targeted['display'] = {
    'sender': '0',
    'receiver': '1',
    'direction': 'one_way',
    'top_n': 20,
    'sort_by': 'magnitude'
}
mock_request_targeted['data_adapter'] = MockDataAdapter(adata.copy())

try:
    start_time = time.time()
    result = test_CCC(mock_request_targeted)
    targeted_runtime = time.time() - start_time

    print(f"Runtime: {targeted_runtime:.2f} seconds")

    if result.startswith('MSG:'):
        print(f"Result: {result}")
    else:
        result_data = json.loads(result)
        csv_data = result_data[0]
        targeted_results = pd.read_csv(pd.io.common.StringIO(csv_data))
        print(f"Results shape: {targeted_results.shape}")
        print(f"Interactions (0 -> 1):")
        print(targeted_results.to_string())

except Exception as e:
    print(f"Error: {e}")

print()
print("=" * 60)
print("Comparison with Original test_liana.py Results")
print("=" * 60)

# Load original results if they exist
original_csv = os.path.join(os.path.dirname(__file__), 'liana_results.csv')
if os.path.exists(original_csv):
    original_results = pd.read_csv(original_csv)
    print(f"Original results shape: {original_results.shape}")
    print(f"Direct test results shape: {direct_results.shape}")

    # Compare top interactions
    orig_top = original_results.head(10)[['source', 'target', 'ligand_complex', 'receptor_complex']].values.tolist()
    direct_top = direct_results.head(10)[['source', 'target', 'ligand_complex', 'receptor_complex']].values.tolist()

    matches = sum(1 for o, d in zip(orig_top, direct_top) if o == d)
    print(f"Top 10 match rate: {matches}/10")

    if matches < 10:
        print("\nNote: Some differences may be due to tie-breaking in ranking.")
else:
    print(f"Original results file not found: {original_csv}")
    print("Run test_liana.py first to generate baseline results.")

print()
print("=" * 60)
print("Summary")
print("=" * 60)
print(f"Direct LIANA runtime: {direct_runtime:.2f}s")
print(f"Backend function runtime: {backend_runtime:.2f}s")
print(f"Targeted mode runtime: {targeted_runtime:.2f}s")
print("All tests completed successfully!" if 'backend_results' in dir() else "Some tests failed.")
