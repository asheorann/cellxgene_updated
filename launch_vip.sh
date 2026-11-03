#!/usr/bin/env bash
# Quick launcher for VIP cellxgene
# Usage: ./launch_vip.sh <data.h5ad> [port]
#
# Examples:
#   ./launch_vip.sh data/mydata.h5ad
#   ./launch_vip.sh data/mydata.h5ad 5005

DATA_FILE="${1:-}"
PORT="${2:-5005}"

if [ -z "$DATA_FILE" ]; then
    echo "Usage: $0 <data.h5ad> [port]"
    echo ""
    echo "Example: $0 data/test.h5ad 5005"
    exit 1
fi

# Setup conda
source ~/miniconda3/etc/profile.d/conda.sh
conda activate VIP

# Convert Windows path to WSL path if needed
if [[ "$DATA_FILE" == /mnt/* ]]; then
    WSL_PATH="$DATA_FILE"
elif [[ "$DATA_FILE" == /* ]]; then
    WSL_PATH="$DATA_FILE"
else
    # Relative path - convert to absolute
    WSL_PATH="$(pwd)/$DATA_FILE"
fi

echo "============================================"
echo "  Launching VIP cellxgene"
echo "============================================"
echo "  Data: $WSL_PATH"
echo "  Port: $PORT"
echo "  URL:  http://localhost:$PORT"
echo "============================================"
echo ""

# Kill any existing process on the port
if command -v fuser &> /dev/null; then
    fuser -k "$PORT/tcp" 2>/dev/null && echo "Killed existing process on port $PORT"
elif command -v lsof &> /dev/null; then
    lsof -ti:"$PORT" | xargs kill -9 2>/dev/null && echo "Killed existing process on port $PORT"
fi

# Small delay to ensure port is freed
sleep 1

cellxgene launch "$WSL_PATH" --host 0.0.0.0 --port "$PORT"
