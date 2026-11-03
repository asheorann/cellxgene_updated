# CCC (Cell-Cell Communication) Speed Optimizations

This document explains the speed optimizations applied to the CCC analysis in cellxgene VIP, why they work, and potential failure modes.

## Summary of Changes

| Setting | Before | After | Impact |
|---------|--------|-------|--------|
| Default method | `rank_aggregate` | `cellphonedb` | ~5x faster |
| Permutations | 1000 | 0 (disabled) | ~10x faster |
| Cell subsampling | None | 500 per type | ~2-4x faster for large datasets |
| **Total estimated speedup** | | | **~30-100x faster** |

## 1. Changed Default Method: `rank_aggregate` → `cellphonedb`

### What it does
- **Before**: `rank_aggregate` runs 5+ different CCC methods (CellPhoneDB, NATMI, Connectome, Log2FC, SingleCellSignalR) and aggregates their rankings
- **After**: `cellphonedb` runs only the CellPhoneDB scoring method

### Why it's faster
- Running 5 methods takes ~5x longer than running 1 method
- Rank aggregation adds additional computation overhead

### Trade-offs
- **Pro**: Much faster for exploratory analysis
- **Con**: You only get one method's scores, not a consensus across methods
- **When to use rank_aggregate**: When you need high confidence results and have time to wait; the consensus ranking reduces method-specific biases

### Where it can fail
- CellPhoneDB may miss interactions that other methods would catch
- For publication-quality results, consider running with `rank_aggregate`

**Location**: `ccc.py` line ~809, `ccc.html` line ~94-101

---

## 2. Disabled Permutation Testing by Default

### What it does
- **Before**: 1000 permutations to compute p-values for each interaction
- **After**: 0 permutations (skipped entirely)

### Why it's faster
- Permutation testing randomly shuffles cell labels and re-runs the analysis 1000 times
- This is the single biggest time cost in CCC analysis
- Skipping it provides ~10x speedup

### Trade-offs
- **Pro**: Dramatic speedup (minutes → seconds)
- **Con**: No p-values for statistical significance testing
- **When to enable**: Set permutations to 100-1000 when you need to filter by significance

### Where it can fail
- Without permutation testing, you cannot statistically filter interactions
- All interactions passing the expression threshold are shown, including potentially spurious ones
- For differential analysis, p-values are important

**Location**: `ccc.py` line ~816-818, `ccc.html` line ~120-123

---

## 3. Cell Subsampling for Large Cell Types

### What it does
- **Before**: All cells used (e.g., 50,000 cells of one type)
- **After**: Large cell types subsampled to 500 cells each

### Why it's faster
- CCC analysis scales with cell count: more cells = more computation
- Most signal is captured with ~500 cells per type
- Reduces memory usage and computation time

### How it works
```python
# For each cell type with >500 cells:
# 1. Randomly select 500 cells (seed=42 for reproducibility)
# 2. Drop the rest from that cell type
# 3. Keep all cells from small cell types
```

### Trade-offs
- **Pro**: Faster analysis, lower memory usage
- **Con**: May miss rare interactions expressed in few cells
- **When to increase**: Set to 1000-2000 if you have rare cell types or need higher precision

### Where it can fail
- If a ligand/receptor is expressed in only 50 cells out of 50,000, subsampling may drop those cells
- The random seed (42) ensures reproducibility, but different subsamples could give slightly different results
- Very small cell types (<500 cells) are not subsampled, so imbalance can occur

**Location**: `ccc.py` function `CCCsubsample()` lines ~166-200

---

## Configuration Options (Advanced Panel)

All speed settings are configurable in the CCC tab's "Advanced Options":

| Option | Default | Range | Effect |
|--------|---------|-------|--------|
| CCC Method | CellPhoneDB | dropdown | Faster methods: cellphonedb, natmi. Slower: rank_aggregate |
| Permutations | 0 | 0-10000 | 0=fast (no p-values), 100+=statistical testing |
| Max cells per type | 500 | 50-5000 | Lower=faster, Higher=more complete |
| Min cells per group | 20 | 5-100 | Filters out small cell types |

---

## Failure Modes and Troubleshooting

### "Request failed" error
**Cause**: Usually a server timeout or memory issue
**Fix**:
1. Reduce "Max cells per type" to 200-300
2. Use "Targeted" mode instead of "Untargeted"
3. Check server logs for the actual error

### No interactions found
**Cause**: Expression threshold too strict, wrong resource, or subsampling dropped relevant cells
**Fix**:
1. Increase "Max cells per type" to 1000+
2. Check species: use "Mouse Consensus" for mouse data
3. Lower "Min cells per group" if you have small clusters

### Results differ from expected
**Cause**: Subsampling, no permutation testing, or single-method bias
**Fix**:
1. Run with `rank_aggregate` method for consensus
2. Enable permutations (set to 1000)
3. Increase subsampling limit

### Analysis still slow
**Cause**: Too many cell types, large dataset, or rank_aggregate selected
**Fix**:
1. Use "Targeted" mode to analyze specific pairs
2. Reduce dataset to cells of interest first
3. Ensure permutations=0 for exploration

---

## Recommended Workflows

### Quick Exploration (default settings)
- Method: CellPhoneDB
- Permutations: 0
- Max cells: 500
- **Time**: ~30 seconds

### Publication-Ready Analysis
- Method: Rank Aggregate
- Permutations: 1000
- Max cells: 2000+
- **Time**: 5-15 minutes

### Targeted Hypothesis Testing
- Mode: Targeted
- Sender/Receiver: specific cell types
- Permutations: 1000
- **Time**: 1-2 minutes

---

## Code Locations

- Backend optimizations: `cellxgene_VIP/ccc.py`
  - `CCC_MAX_CELLS_PER_TYPE = 500` (line ~62)
  - `CCC_DEFAULT_PERMS = None` (line ~65)
  - `CCCsubsample()` function (lines ~166-200)

- Frontend defaults: `cellxgene_VIP/ccc.html`
  - Method dropdown (lines ~94-101)
  - Permutations input (lines ~120-123)
  - Max cells input (lines ~124-127)

- Request building: `cellxgene_VIP/ccc.js`
  - `CCCbuildRequest()` function (lines ~387-446)
