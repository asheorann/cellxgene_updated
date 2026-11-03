# CellxGene VIP + CCC

Single-cell RNA-seq visualization with VIP extensions and cell-cell communication analysis.

## Quick Start (WSL)

```bash
# 1. Open WSL
wsl

# 2. Navigate and activate
cd /mnt/c/Users/anush/projects/cellxgene_updated
conda activate VIP

# 3. Update VIP files (run after any changes to cellxgene_VIP/)
cd cellxgene_VIP && bash update.VIPInterface.sh && cd ..

# 4. Launch
./launch_vip.sh data/scanpy-pbmc3k.h5ad
```

Open **http://localhost:5005**

## Project Structure

```
cellxgene_updated/
├── cellxgene_VIP/          # VIP extension code
│   ├── interface.html      # Upstream VIP UI (minimal hooks only)
│   ├── vip-theme.css       # OUR custom UI theme
│   ├── vip-theme.js        # OUR UI helpers
│   ├── ccc.py/js/html      # OUR CCC feature
│   ├── VIPInterface.py     # Upstream backend dispatcher
│   └── update.VIPInterface.sh  # Copies files to conda env
├── data/                   # H5AD datasets
├── tools/                  # Sync and check scripts
├── ui-designs/             # UI mockups/concepts
├── CLAUDE.md               # Claude Code instructions
├── CHANGES_FROM_UPSTREAM.md # Tracks all upstream changes
└── _archive/               # Old/unused files
```

## Key Rules

1. **Keep our code separate from upstream**
   - Our code: `ccc.py`, `ccc.js`, `ccc.html`, `vip-theme.css`, `vip-theme.js`
   - Upstream files get minimal hook lines only (imports, script tags)

2. **After editing VIP files, run the update script**
   ```bash
   cd cellxgene_VIP && bash update.VIPInterface.sh
   ```

3. **Sync upstream VIP** (when needed)
   ```bash
   bash tools/sync_vip_upstream.sh
   ```

## CCC Feature

Cell-cell communication analysis using LIANA. Select cell groups, choose conditions, run analysis.

- Backend: `cellxgene_VIP/ccc.py`
- Frontend: `cellxgene_VIP/ccc.js`, `ccc.html`
- Tab in VIP: "Cell Communication" section

## Troubleshooting

**"Dataset does not exist"**
- Check the path is correct from WSL perspective (`/mnt/c/...`)
- Make sure the .h5ad file exists

**UI changes not showing**
- Run `update.VIPInterface.sh` to copy files to conda env
- Hard refresh browser (Ctrl+Shift+R)

**WSL path issues**
- Windows: `C:\Users\anush\...`
- WSL: `/mnt/c/Users/anush/...`

## Files Reference

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Claude Code context and rules |
| `CHANGES_FROM_UPSTREAM.md` | Tracks all changes from upstream VIP |
| `_archive/SETUP_NOTES.md` | Detailed troubleshooting history |
| `_archive/CCC_DEPLOYMENT_CONSTRAINTS.md` | LIANA API details |
