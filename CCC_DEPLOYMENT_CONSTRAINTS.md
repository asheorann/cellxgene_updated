# CCC/LIANA Deployment Constraints

Reference document for deploying cell-cell communication analysis on EC2/production.

---

## LIANA API Dependencies

We're coupled to LIANA in **3 specific places**:

### 1. Analysis Function
```python
li.mt.rank_aggregate(
    adata,
    groupby=groupby,
    resource_name=resource,  # 'consensus', 'CellChatDB', etc.
    expr_prop=0.1,
    use_raw=use_raw,
    n_perms=n_perms,
    verbose=False
)
```

### 2. Results Location
```python
liana_res = adata.uns['liana_res']
```

### 3. Results Schema (Column Names)
- `source`, `target` - cell type pairs
- `ligand_complex`, `receptor_complex` - L-R pairs
- `lr_means` - mean expression
- `magnitude_rank` - always present
- `specificity_rank` - only with permutations
- `cellphone_pvals` - only with permutations

### 4. Plotting Function
```python
li.pl.dotplot(adata, colour='magnitude_rank', size=size_col, ...)
```

Returns a plotnine figure with `.save()` method.

---

## Risk Summary

| Coupling Point | Risk Level | What Breaks |
|----------------|------------|-------------|
| `li.mt.rank_aggregate()` | **High** | Entire analysis fails |
| `adata.uns['liana_res']` | **Medium** | Can't extract results |
| Column names | **Medium** | Sorting/filtering/display breaks |
| `li.pl.dotplot()` | **Low** | Only visualization fails (table still works) |

---

## Memory (RAM) Constraints

### The Problem
Multiple copies of AnnData are created:
```python
adata = scD.data.copy()           # Full dataset copy #1
adata = adata[cell_indices].copy() # Filtered copy #2
adata = adata[valid_groups].copy() # Another copy #3
```

LIANA also creates internal matrices for permutation testing.

### RAM Requirements

| Dataset Size | Approx RAM Needed |
|--------------|-------------------|
| 10k cells × 20k genes | ~2-4 GB |
| 50k cells × 20k genes | ~8-16 GB |
| 100k cells × 30k genes | ~20-40 GB |
| 500k cells | ~100+ GB |

### EC2 Instance Recommendations

| Use Case | Instance | RAM | Cost |
|----------|----------|-----|------|
| Dev/testing | t3.medium | 4 GB | ~$0.04/hr |
| Small datasets (<20k cells) | t3.large | 8 GB | ~$0.08/hr |
| Medium datasets (<50k cells) | r5.large | 16 GB | ~$0.13/hr |
| Large datasets (<100k cells) | r5.xlarge | 32 GB | ~$0.25/hr |
| Very large (GutPath full) | r5.2xlarge | 64 GB | ~$0.50/hr |

---

## CPU / Runtime Constraints

### Permutation Testing

| Permutations | Runtime (3k cells) | Runtime (50k cells) |
|--------------|-------------------|---------------------|
| None (n_perms=0) | ~10 sec | ~2-5 min |
| 100 | ~15 sec | ~5-10 min |
| 1000 (default) | ~30 sec | ~15-30 min |

### vCPU Impact
- t2.micro (1 vCPU): 10x slower than above estimates
- t3.large (2 vCPU): Close to estimates
- c5.xlarge (4 vCPU): ~2x faster

---

## Concurrency Constraints

### Global Lock Problem
```python
getLock(jobLock)        # BLOCKS all other VIP requests
taskRes = distributeTask(...)
freeLock(jobLock)
```

VIP uses a **single global lock**. While CCC runs (30-60+ seconds):
- ALL other users wait
- Even simple plots are blocked
- No request queuing/prioritization

### Impact
- 5 concurrent users → 4 waiting
- Long CCC job → everyone frustrated

---

## Timeout Constraints

| Layer | Default Timeout |
|-------|-----------------|
| Browser fetch | 60 sec |
| Nginx proxy | 60 sec |
| Gunicorn worker | 30 sec |

If CCC exceeds timeout:
- User sees "Request failed"
- Backend keeps computing (wasted resources)
- No cancellation mechanism

---

## Network/Storage Constraints

### L-R Database Downloads
LIANA downloads databases on first use:
- `consensus`: ~10 MB
- `CellChatDB`: ~20 MB
- `CellPhoneDB`: ~15 MB

Cached in `~/.cache/liana/` or similar.

### First-Run Considerations
- Needs outbound internet access
- First request takes extra 10-30 sec
- Pre-warm cache during deployment:
  ```python
  import liana as li
  li.resource.select_resource('consensus')
  ```

### Disk Space
- H5AD files: 100 MB - 10 GB typical
- Swap file: Recommend 2x RAM
- LIANA cache: ~100 MB

---

## Recommended Safeguards

### Cell Count Limits
```python
if len(adata) > 50000:
    return Msg("Dataset has >50k cells.\nPlease select a subset.")

if n_perms and n_perms > 100 and len(adata) > 20000:
    return Msg("Large dataset + permutations will be slow.\nSet permutations to 0.")
```

### Memory Monitoring
```python
import psutil
mem = psutil.Process().memory_info().rss / 1024**3  # GB
if mem > 12:  # Getting close to limit
    gc.collect()
```

### Timeout Warning in UI
```javascript
$("#CCCfig").html("<i>Running LIANA analysis... This may take 30-60 seconds.</i>");
```

---

## Production Checklist

- [ ] EC2 instance sized for max expected dataset
- [ ] Swap file configured (2x RAM)
- [ ] Nginx timeout increased to 300s for VIP routes
- [ ] Gunicorn timeout increased
- [ ] LIANA cache pre-warmed
- [ ] Monitoring/alerting on memory usage
- [ ] User documentation on expected wait times
- [ ] Consider: async job queue for large analyses

---

## Testing Benchmarks

From `ccc_worker/test_liana.py` on PBMC3k (2,700 cells):

| Setting | Runtime | Memory |
|---------|---------|--------|
| n_perms=None | ~10 sec | ~1 GB |
| n_perms=1000 | ~30 sec | ~1.5 GB |

Should test on GutPath subset to get realistic estimates.
