#!/usr/bin/env bash
# Quick VIP Setup Script
# Re-patches cellxgene for VIP if needed (e.g., after pip upgrades)
#
# This script is FAST - no rebuilding required!
# Run this once after initial setup or after updating cellxgene.

set -e

echo "=== VIP Quick Setup ==="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VIP_DIR="$SCRIPT_DIR/cellxgene_VIP"

# Setup conda
source ~/miniconda3/etc/profile.d/conda.sh
conda activate VIP

SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])")
SERVER_APP="$SITE_PACKAGES/server/app"
WEB_STATIC="$SITE_PACKAGES/server/common/web/static"
WEB_TEMPLATES="$SITE_PACKAGES/server/common/web/templates"

echo "Installing cellxgene 1.1.1 from PyPI..."
pip install -q cellxgene==1.1.1

echo "Patching for VIP..."

# Copy VIPInterface
cp "$VIP_DIR/VIPInterface.py" "$SERVER_APP/"

# Copy R scripts
cp "$VIP_DIR"/*.R "$SERVER_APP/"
chmod +x "$SERVER_APP"/*.R

# Copy bin and DataTables
cp -r "$VIP_DIR/bin" "$SERVER_APP/"
cp -r "$VIP_DIR/DataTables" "$SERVER_APP/"
chmod +x "$SERVER_APP/bin/"* 2>/dev/null || true

# Copy interface.html to static
cp "$VIP_DIR/interface.html" "$WEB_STATIC/"

# Patch index.html with VIP insert
python3 << PYEOF
index_path = '$WEB_TEMPLATES/index.html'
insert_path = '$VIP_DIR/index_template.insert'

with open(index_path, 'r') as f:
    content = f.read()

if 'jsPanel.create' not in content:
    with open(insert_path, 'r') as f:
        vip_insert = f.read()
    content = content.replace('<div id="root"></div>', vip_insert + '\n    <div id="root"></div>')
    with open(index_path, 'w') as f:
        f.write(content)
    print('  Patched index.html')
else:
    print('  index.html already patched')
PYEOF

# Add VIP route to app.py if not present
if ! grep -q "def VIP():" "$SERVER_APP/app.py"; then
    cat >> "$SERVER_APP/app.py" << 'EOF'

# VIP extension
from server.app.VIPInterface import route as vip_route
@webbp.route("/VIP", methods=["POST"])
def VIP():
    from flask import request, current_app
    return vip_route(request.data, current_app.app_config)
EOF
    echo "  Added VIP route to app.py"
else
    echo "  VIP route already exists"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To launch: ./launch_vip.sh <data.h5ad> [port]"
echo "Example:   ./launch_vip.sh data/test.h5ad 5005"
echo "Then open: http://localhost:5005"
