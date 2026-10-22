#!/usr/bin/env bash
# Pull upstream cellxgene_VIP changes into cellxgene_VIP/ without losing ours.
#
# Usage:  tools/sync_vip_upstream.sh [upstream-ref]     (default: master)
#
# Our copy of VIP has no upstream git history, so this does a three-way merge per
# file using the upstream commit we're based on (cellxgene_VIP/VIP_UPSTREAM):
#   - file unchanged by us        -> replaced with upstream's new version
#   - file changed by us and them -> git merge-file; overlapping edits get
#                                    <<<<<<< conflict markers to fix by hand
#   - added/deleted upstream      -> added/deleted (unless we touched it)
# Then records the new baseline and runs tools/check_ccc_compat.py.
# Run it on a clean working tree (ideally a new branch) so `git diff` shows the sync.
set -euo pipefail

UPSTREAM_URL=https://github.com/interactivereport/cellxgene_VIP.git
ROOT=$(git rev-parse --show-toplevel)
VIP="$ROOT/cellxgene_VIP"
REF=${1:-master}
BASE=$(grep -v '^#' "$VIP/VIP_UPSTREAM" | head -1 | tr -d '[:space:]')

if [ -n "$(git -C "$ROOT" status --porcelain -- cellxgene_VIP ':!cellxgene_VIP/cellxgene')" ]; then
  echo "cellxgene_VIP/ has uncommitted changes. Commit or stash them first." >&2
  exit 1
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
echo "Fetching $UPSTREAM_URL ..."
git clone -q --filter=blob:none "$UPSTREAM_URL" "$TMP/up"
NEW=$(git -C "$TMP/up" rev-parse "origin/$REF" 2>/dev/null || git -C "$TMP/up" rev-parse "$REF")

if [ "$NEW" = "$BASE" ]; then
  echo "Already up to date with upstream $REF ($NEW)."
  exit 0
fi
echo "Upstream changes since ${BASE:0:8}:"
git -C "$TMP/up" log --format='  %h %cd %s' --date=short "$BASE..$NEW"
echo

updated=(); added=(); deleted=(); merged=(); conflicts=(); skipped=()
show() { git -C "$TMP/up" show "$1:$2" > "$3"; }

while IFS=$'\t' read -r status path; do
  local_f="$VIP/$path"
  case "$status" in
    A)
      if [ ! -e "$local_f" ]; then
        mkdir -p "$(dirname "$local_f")"; show "$NEW" "$path" "$local_f"; added+=("$path")
      else
        show "$NEW" "$path" "$TMP/new"
        cmp -s "$TMP/new" "$local_f" || conflicts+=("$path (added upstream, but we have a different file with that name)")
      fi ;;
    D)
      if [ -e "$local_f" ]; then
        show "$BASE" "$path" "$TMP/base"
        if cmp -s "$TMP/base" "$local_f"; then rm "$local_f"; deleted+=("$path")
        else conflicts+=("$path (deleted upstream, but we changed it; decide by hand)"); fi
      fi ;;
    M)
      if [ ! -e "$local_f" ]; then skipped+=("$path (not in our repo, e.g. gitignored)"); continue; fi
      show "$BASE" "$path" "$TMP/base"; show "$NEW" "$path" "$TMP/new"
      if cmp -s "$TMP/base" "$local_f"; then
        cp "$TMP/new" "$local_f"; updated+=("$path")
      else
        set +e
        git merge-file -L ours -L "upstream ${BASE:0:8}" -L "upstream ${NEW:0:8}" "$local_f" "$TMP/base" "$TMP/new"
        rc=$?
        set -e
        if [ $rc -eq 0 ]; then merged+=("$path")
        else conflicts+=("$path ($rc conflict(s), see <<<<<<< markers)"); fi
      fi ;;
  esac
done < <(git -C "$TMP/up" diff --name-status --no-renames "$BASE" "$NEW")

sed -i "s/^$BASE\$/$NEW/" "$VIP/VIP_UPSTREAM"

report() { local title=$1; shift; [ $# -gt 0 ] && { echo "$title ($#):"; printf '  %s\n' "$@"; }; return 0; }
report "Updated (we hadn't changed them)" "${updated[@]+"${updated[@]}"}"
report "Added" "${added[@]+"${added[@]}"}"
report "Deleted" "${deleted[@]+"${deleted[@]}"}"
report "Merged cleanly with our changes" "${merged[@]+"${merged[@]}"}"
report "Skipped" "${skipped[@]+"${skipped[@]}"}"
report "CONFLICTS - fix by hand" "${conflicts[@]+"${conflicts[@]}"}"
if git -C "$TMP/up" diff --quiet "$BASE" "$NEW" -- config.sh; then :; else
  echo; echo "NOTE: upstream changed config.sh. Check whether the pinned cellxgene version changed."
fi

echo; echo "Baseline is now ${NEW:0:8} (cellxgene_VIP/VIP_UPSTREAM)."
echo; echo "== Compatibility check =="
PY=python; python -c "" 2>/dev/null || PY=python3  # conda env has python; plain WSL has python3
"$PY" "$ROOT/tools/check_ccc_compat.py" || true
cat <<EOF

Next steps (see CHANGES_FROM_UPSTREAM.md, "Pulling upstream VIP"):
  1. Fix any conflicts and FAIL lines above, re-run: python tools/check_ccc_compat.py
  2. Review: git diff -- cellxgene_VIP
  3. Backend test (VIP conda env): python tools/test_ccc_backend.py data/pbmc68k_reduced.h5ad
  4. ./update.VIPInterface.sh, launch cellxgene, run the CCC smoke test in the browser
  5. Commit, and add a changelog entry to CHANGES_FROM_UPSTREAM.md
EOF
