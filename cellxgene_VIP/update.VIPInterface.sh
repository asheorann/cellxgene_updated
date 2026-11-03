#!/usr/bin/env bash
if [ -n "$1" ]; then
echo "usually update once"
fi

## finished setting up ------
strPath="$(python -c 'import site; print(site.getsitepackages()[0])')"
strweb="${strPath}/server/common/web/static/."

cp VIPInterface.py $strPath/server/app/.
cp interface.html $strweb
cp ccc.py $strPath/server/app/.
cp ccc.js ccc.html $strweb
cp vip-theme.css vip-theme.js $strweb
cp vip.env $strPath/server/app/. 2>/dev/null | true

# Inject vip-theme.css into the main cellxgene index.html so it loads on startup
# Search for index.html in multiple locations
for indexhtml in \
  "${strPath}/server/common/web/static/index.html" \
  "${strPath}/server/common/web/index.html" \
  "${strPath}/server/common/web/templates/index.html" \
  $(find "${strPath}/server" -name "index.html" 2>/dev/null | head -5)
do
  if [ -f "$indexhtml" ]; then
    echo "Found index.html at: $indexhtml"
    if ! grep -q "vip-theme.css" "$indexhtml"; then
      echo "Injecting vip-theme.css..."
      sed -i 's|</head>|<link rel="stylesheet" href="static/vip-theme.css"></head>|' "$indexhtml"
    else
      echo "vip-theme.css already injected"
    fi
    break
  fi
done

# Also inject CSS import into the main CSS file as fallback
maincss=$(ls ${strPath}/server/common/web/static/main-*.css 2>/dev/null | head -1)
if [ -n "$maincss" ] && [ -f "$maincss" ]; then
  if ! grep -q "vip-theme.css" "$maincss"; then
    echo "Injecting @import into main CSS: $maincss"
    # Prepend import statement
    echo '@import url("vip-theme.css");' | cat - "$maincss" > /tmp/maincss_tmp && mv /tmp/maincss_tmp "$maincss"
  else
    echo "vip-theme.css already in main CSS"
  fi
fi

cp fgsea.R $strPath/server/app/.
mkdir -p $strPath/server/app/gsea
cp gsea/*gmt $strPath/server/app/gsea
cp complexHeatmap.R $strPath/server/app/.
cp volcano.R $strPath/server/app/.

if [ -n "$1" ]; then
  cp Density2D.R $strPath/server/app/.
  cp bubbleMap.R $strPath/server/app/.
  cp violin.R $strPath/server/app/.
  cp volcano.R $strPath/server/app/.
  cp browserPlot.R $strPath/server/app/.
  cp complexHeatmap.R $strPath/server/app/.
  cp proteinatlas_protein_class.csv $strPath/server/app/.
  cp complex_vlnplot_multiple.R $strPath/server/app/.
  if [ "$(uname -s)" = "Darwin" ]; then
    sed -i .bak "s|route(request.data,current_app.app_config, \"/tmp\")|route(request.data,current_app.app_config)|" "$strPath/server/app/app.py"
    sed -i .bak "s|MAX_LAYOUTS *= *[0-9]\+|MAX_LAYOUTS = 300|" "$strPath/server/common/constants.py"
  else
    sed -i "s|route(request.data,current_app.app_config, \"/tmp\")|route(request.data,current_app.app_config)|" "$strPath/server/app/app.py"
    sed -i "s|MAX_LAYOUTS *= *[0-9]\+|MAX_LAYOUTS = 300|" "$strPath/server/common/constants.py"
  fi
  
  # fix the top left cornor image
  find $strweb -name "*js" -exec sed -i 's|../static/assets|static/assets|' {} \;
  
  find ./cellxgene/server/ -name "decode_fbs.py" -exec cp {} $strPath/server/app/. \;
fi

echo -e "\nls -l $strweb\n"
ls -l $strweb
