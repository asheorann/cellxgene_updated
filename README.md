# CellxGene VIP with Cell-Cell Communication Analysis

Interactive single-cell RNA-seq visualization with VIP extensions and **cell-cell communication (CCC) analysis** powered by LIANA.

Developed for the **GutPath scRNA-seq atlas** at Penn Vet.

---

## Quick Start

### Prerequisites

1. **Install Singularity/Apptainer** (Linux or WSL required)
   ```bash
   # Ubuntu/Debian/WSL
   sudo apt update
   sudo apt install -y software-properties-common
   sudo add-apt-repository -y ppa:apptainer/ppa
   sudo apt update
   sudo apt install -y apptainer
   ```

2. **Prepare your data**
   - Place your `.h5ad` file in a folder (e.g., `~/data/`)
   - The file should contain log-normalized expression data
   - Cell type annotations should be in `adata.obs`

### Build the Container (one-time)

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/cellxgene_updated.git
cd cellxgene_updated

# Build the container (takes 30-60 minutes)
sudo singularity build cellxgene_vip.sif Singularity.def
```

### Run

```bash
# Mount your data folder and run
singularity run --bind ~/data:/data cellxgene_vip.sif /data/your_file.h5ad

# Or with a custom port
singularity run --bind ~/data:/data cellxgene_vip.sif /data/your_file.h5ad 5006
```

Open **http://localhost:5005** in your browser.

---

## Cell-Cell Communication (CCC) Feature

The CCC tab enables ligand-receptor interaction analysis between cell populations using [LIANA](https://liana-py.readthedocs.io/).

### Two Analysis Modes

| Mode | Description |
|------|-------------|
| **Targeted** | Analyze communication between a specific sender and receiver cell type that you select. Use this when you have a hypothesis about which cells are communicating. |
| **Untargeted** | Discover all ligand-receptor interactions across all cell type pairs. Use this for exploratory analysis. |

### Optional: Compare Two Conditions

You can optionally compare CCC between two conditions (e.g., infected vs. control):
- Select a condition column (e.g., "infection_status")
- Choose reference and test groups
- Optionally specify a replicate/sample column for proper averaging across mice

### How to Use CCC

1. Click the **VIP** button (top-right dropdown) to open the visualization panel
2. Navigate to the **CCC: Cell Communication** tab
3. Select your **cell type annotation** column
4. Choose **Targeted** or **Untargeted** mode
5. (Optional) Set up condition comparison
6. Click **Run Analysis**

### Speed Optimizations

CCC analysis can be slow on large datasets. These optimizations are enabled by default:

| Setting | Default | Effect |
|---------|---------|--------|
| **Max cells per type** | 500 | Large cell types are subsampled to 500 cells |
| **Permutations** | 0 | No permutation testing (fast exploratory mode) |

For publication-quality results, increase permutations to 100-1000 in Advanced Options.

### Advanced Settings

| Setting | Options | Recommendation |
|---------|---------|----------------|
| **Method** | CellPhoneDB, NATMI, Rank Aggregate, etc. | CellPhoneDB (fast) or Rank Aggregate (comprehensive) |
| **Resource** | Auto, Mouse Consensus, Consensus (human) | Auto-detects; use Mouse Consensus for mouse data |
| **Min cells per group** | 5-100 | 20 (default) - excludes small clusters |

---

## Console Warnings (Normal)

You may see these warnings when launching - they are **expected** and do not affect functionality:

```
[cellxgene] Warning: Anndata data matrix is in float64 format not float32
WARNING:root:Type float64 will be converted to 32 bit float
'Warning: No raw counts detected. Using X directly.'
```

These indicate:
- Data precision is reduced from 64-bit to 32-bit (fine for visualization)
- LIANA is using the main expression matrix since `.raw` is not available

---

## Limitations

### Data Requirements
- Input must be an `.h5ad` file with log-normalized expression
- Cell type annotations must be in `adata.obs`
- For condition comparison: need condition and sample columns in `adata.obs`

### CCC Limitations
- Requires at least 2 cell types with 20+ cells each
- Comparison view requires 2+ replicates per condition with 30+ cells each
- Very large datasets (>100k cells) may be slow even with subsampling

---

## Troubleshooting

### "File not found" error
```bash
# Bind mount the directory containing your data
singularity run --bind /path/to/your/data:/data cellxgene_vip.sif /data/file.h5ad
```

### Port already in use
```bash
singularity run --bind ~/data:/data cellxgene_vip.sif /data/file.h5ad 5006
```

### VIP panel not appearing
- Hard refresh: `Ctrl+Shift+R`
- Check browser console (F12) for errors

### CCC analysis fails
- Ensure 2+ cell types with 20+ cells each
- Check that groupby column exists and has valid categories
- For comparison view: verify condition and sample columns exist

---

## Project Structure

```
cellxgene_updated/
├── Singularity.def          # Container definition
├── cellxgene_vip.sif        # Built container (after build)
├── README.md                # This file
├── cellxgene_VIP/           # VIP extension source
│   ├── ccc.py               # CCC backend
│   ├── ccc.js               # CCC frontend
│   ├── ccc.html             # CCC interface
│   ├── VIPInterface.py      # VIP backend
│   └── interface.html       # VIP interface
└── data/                    # Your h5ad files (not included)
```

---

## For Developers

See `CLAUDE.md` for development context.

```bash
# Local development (requires VIP conda environment)
conda activate VIP
cd cellxgene_VIP && bash update.VIPInterface.sh && cd ..
cellxgene launch data/your_file.h5ad --host 0.0.0.0 --port 5005
```

---

## Citation

- CellxGene: [Chan Zuckerberg Initiative](https://chanzuckerberg.github.io/cellxgene/)
- VIP: [interactivereport/cellxgene_VIP](https://github.com/interactivereport/cellxgene_VIP)
- LIANA: [saezlab/liana-py](https://github.com/saezlab/liana-py)
