# Quick Start Guide: VIP & paraCell

## Prerequisites
- WSL with Ubuntu
- Miniconda installed in WSL
- Conda environments already set up: `VIP` and `paraCell`

---

## Running VIP (cellxgene with Visualization Plugin)

```bash
# 1. Open WSL terminal
wsl

# 2. Activate VIP environment and navigate to project
source ~/miniconda3/etc/profile.d/conda.sh
conda activate VIP
cd /mnt/c/Users/anush/projects/cellxgene_updated

# 3. Launch cellxgene with your data
cellxgene launch <path-to-your-data.h5ad> --host 0.0.0.0 --port 5005

# Example with sample data:
cellxgene launch cellxgene_VIP/cellxgene/example-dataset/pbmc3k.h5ad --host 0.0.0.0 --port 5005
```

Then open: **http://localhost:5005**

### Using VIP Features
1. The "Visualization in Plugin" panel appears on the left
2. **Select cells first** (use lasso tool or click clusters) - boxes are greyed out until you select data
3. Choose visualization type and click generate

---

## Running paraCell

```bash
# 1. Open WSL terminal
wsl

# 2. Activate paraCell environment and navigate to project
source ~/miniconda3/etc/profile.d/conda.sh
conda activate paraCell
cd /mnt/c/Users/anush/projects/cellxgene_updated

# 3. Launch cellxgene with your data
cellxgene launch <path-to-your-data.h5ad> --host 0.0.0.0 --port 5006
```

Then open: **http://localhost:5006**

---

## Running Both Side-by-Side

Open **two WSL terminals**:

**Terminal 1 (VIP on port 5005):**
```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate VIP
cd /mnt/c/Users/anush/projects/cellxgene_updated
cellxgene launch <data.h5ad> --host 0.0.0.0 --port 5005
```

**Terminal 2 (paraCell on port 5006):**
```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate paraCell
cd /mnt/c/Users/anush/projects/cellxgene_updated
cellxgene launch <data.h5ad> --host 0.0.0.0 --port 5006
```

---

## Using Your Own Dataset

### Option 1: Use absolute WSL path
```bash
# If your file is at C:\Users\anush\data\mydata.h5ad
cellxgene launch /mnt/c/Users/anush/data/mydata.h5ad --host 0.0.0.0 --port 5005
```

### Option 2: Copy to project folder
```bash
# Copy your h5ad file to a data folder
cp /mnt/c/path/to/mydata.h5ad /mnt/c/Users/anush/projects/cellxgene_updated/data/

# Then launch
cellxgene launch data/mydata.h5ad --host 0.0.0.0 --port 5005
```

### Path conversion (Windows to WSL)
- `C:\Users\anush\...` becomes `/mnt/c/Users/anush/...`
- `D:\data\...` becomes `/mnt/d/data/...`

### Data requirements
- File must be `.h5ad` format (AnnData)
- Should have embeddings (UMAP, t-SNE) pre-computed for visualization
- Cell annotations in `.obs` for grouping

---

## Sample Data Locations

- `cellxgene_VIP/cellxgene/example-dataset/pbmc3k.h5ad` (recommended for testing)
- `cellxgene_VIP/cellxgene/test/fixtures/pbmc3k-CSC-gz.h5ad`

---

## Troubleshooting

### "command not found: cellxgene"
```bash
hash -r  # Refresh shell's command cache
```

### VIP/paraCell panel boxes are greyed out
1. **Select cells first** - use lasso tool or click on clusters in the embedding
2. If still greyed out after selection, hard refresh: `Ctrl+Shift+R`

### Browser shows old version or cached content
Hard refresh: `Ctrl+Shift+R`

### Wrong Python/cellxgene being used
Always activate the conda environment first:
```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate VIP  # or paraCell
```

### "AssertionError: View function mapping is overwriting an existing endpoint"
The VIP route was added multiple times. Fix by removing duplicates:
```bash
# Check for duplicates
grep -n 'def VIP' /home/anushkas2003/miniconda3/envs/VIP/lib/python3.8/site-packages/server/app/app.py

# If multiple lines shown, edit to keep only one VIP route
```

### Module import errors (Flask, pandas, numpy)
The environments need specific versions. If broken, reinstall:
```bash
conda activate VIP  # or paraCell
pip install 'Flask==2.0.3' 'Werkzeug==2.0.3' 'pandas==1.5.3' 'numpy>=1.17.5,<=1.22'
```

---

## What We Learned (Setup Notes)

### Why PyPI cellxgene doesn't work with VIP
The VIP/paraCell panel needs `window.store` to communicate with cellxgene's Redux store. The PyPI version doesn't export this. We built cellxgene from source with this modification in `client/src/reducers/index.js`:
```javascript
window.store = store;
```

### Key version constraints
- **Flask**: 2.0.3 (Flask 3.0 breaks `flask.json.JSONEncoder`)
- **Werkzeug**: 2.0.3 (must match Flask)
- **pandas**: 1.5.3 (newer versions break scanpy's `is_categorical`)
- **numpy**: >=1.17.5,<=1.22 (cellxgene constraint)
- **rpy2**: 3.3.5 (newer versions have different module structure)

### Files that were patched
In each conda environment's site-packages:
- `server/app/app.py` - Added VIP route
- `server/app/VIPInterface.py` - Copied from cellxgene_VIP/
- `server/common/web/static/` - Built JS with window.store + interface.html
- `server/common/web/templates/index.html` - Patched with jsPanel initialization

### If you need to re-patch after pip upgrades
Run `./quick_setup.sh` from WSL to re-apply VIP patches to the VIP environment.

---

## Quick Reference

| Environment | Port | URL | Panel Title |
|------------|------|-----|-------------|
| VIP | 5005 | http://localhost:5005 | Visualization in Plugin |
| paraCell | 5006 | http://localhost:5006 | PARACELL |
