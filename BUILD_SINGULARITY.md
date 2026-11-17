# Building the CellxGene VIP Container

Step-by-step instructions for building and running the Singularity container.

---

## Prerequisites

### 1. Install Singularity/Apptainer

**On Ubuntu/Debian/WSL:**
```bash
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:apptainer/ppa
sudo apt update
sudo apt install -y apptainer

# Verify
singularity --version
```

**On macOS:** Requires a Linux VM (Lima or Vagrant)

**On Windows:** Use WSL2 (Windows Subsystem for Linux)

### 2. Clone the Repository

```bash
git clone https://github.com/asheorann/cellxgene_updated.git
cd cellxgene_updated
```

---

## Build the Container

```bash
# Build (requires sudo, takes 30-60 minutes)
sudo singularity build cellxgene_vip.sif Singularity.def
```

**What gets installed:**
- Python 3.8 with cellxgene, scanpy, liana, diffxpy
- R with ggplot2, ComplexHeatmap, fgsea
- VIP extensions including CCC analysis

**Output:** `cellxgene_vip.sif` (~2-3 GB)

### Verify the Build

```bash
# Run built-in tests
singularity test cellxgene_vip.sif
```

---

## Run the Container

### Basic Usage

```bash
# Your data file must be accessible via bind mount
singularity run --bind ~/data:/data cellxgene_vip.sif /data/your_file.h5ad
```

Then open **http://localhost:5005**

### Common Examples

```bash
# Data in home directory
singularity run --bind $HOME:/home cellxgene_vip.sif /home/data/pbmc3k.h5ad

# Data in a specific folder
singularity run --bind /path/to/datasets:/data cellxgene_vip.sif /data/experiment.h5ad

# Custom port
singularity run --bind ~/data:/data cellxgene_vip.sif /data/file.h5ad 5006

# Multiple directories
singularity run --bind ~/data:/data,~/results:/results cellxgene_vip.sif /data/file.h5ad
```

---

## Troubleshooting

### "File not found" error
The container can't see files outside its filesystem. Use `--bind` to mount directories:
```bash
singularity run --bind /your/data/folder:/data cellxgene_vip.sif /data/file.h5ad
```

### "Permission denied" when building
```bash
sudo singularity build cellxgene_vip.sif Singularity.def
```

### Port already in use
```bash
singularity run --bind ~/data:/data cellxgene_vip.sif /data/file.h5ad 5006
```

### Build fails on R packages
Network issues can cause R package installation to fail. Just retry:
```bash
sudo singularity build cellxgene_vip.sif Singularity.def
```

### Out of disk space
```bash
export SINGULARITY_TMPDIR=/path/with/more/space
sudo -E singularity build cellxgene_vip.sif Singularity.def
```

---

## Sharing the Container

The `.sif` file is portable. Copy it to any machine with Singularity installed:

```bash
# Copy to another machine
scp cellxgene_vip.sif user@server:/path/to/destination/

# Or share via cloud storage
```

The recipient just needs Singularity/Apptainer installed.

---

## Quick Reference

| Task | Command |
|------|---------|
| Build | `sudo singularity build cellxgene_vip.sif Singularity.def` |
| Run | `singularity run --bind ~/data:/data cellxgene_vip.sif /data/file.h5ad` |
| Test | `singularity test cellxgene_vip.sif` |
| Shell | `singularity shell cellxgene_vip.sif` |
| Custom port | Add port number at end: `... /data/file.h5ad 5006` |
