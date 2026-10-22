"""
Cell-cell communication (CCC) extension for cellxgene VIP, using LIANA.

Kept out of VIPInterface.py so upstream VIP updates merge cleanly. VIP hooks:
  - VIPInterface.py imports this module and registers 'CCC': ccc.CCC in distributeTask()
  - interface.html loads static/ccc.js, which loads static/ccc.html (the tab)
See CHANGES_FROM_UPSTREAM.md.
"""
import json
import re
import textwrap
import traceback
import base64
from io import BytesIO
import pprint

import numpy as np
import pandas as pd
import scipy.sparse
import matplotlib
from matplotlib import pyplot as plt

ppr = pprint.PrettyPrinter(depth=6,width=500)

def Msg(msg):
    """VIP's message-as-image response. Imported at call time: VIPInterface imports this module."""
    from server.app.VIPInterface import Msg as vipMsg
    return vipMsg(msg)


# Frontend method value -> liana.mt method name
CCC_METHODS = {
    'rank_aggregate': 'rank_aggregate',
    'cellphonedb': 'cellphonedb',
    'natmi': 'natmi',
    'connectome': 'connectome',
    'logfc': 'logfc',
    'sca': 'singlecellsignalr'
}

# Frontend resource value -> LIANA resource name (LIANA names are lowercase)
CCC_RESOURCES = {
    'consensus': 'consensus',
    'mouseconsensus': 'mouseconsensus',
    'cellphonedb': 'cellphonedb',
    'cellchatdb': 'cellchatdb',
    'connectomedb': 'connectomedb2020'
}

# Temporary obs column holding lasso selection labels in CCC lasso mode
CCC_LASSO_COL = '_ccc_lasso_selection'

# LIANA's per-gene filter: fraction of a cell type's cells that must express a gene
CCC_EXPR_PROP = 0.1

# Comparison view: cells of a cell type a replicate (mouse) needs to count toward the
# across-mice average. Separate from LIANA's expr_prop: below ~30 cells a proportion
# estimate can't tell which side of the 10% cut-off it falls on (SE 0.055 at n=30)
CCC_SAMPLE_MIN_CELLS = 30

# Comparison view: above this many condition columns, stack the two conditions as rows
CCC_SLOT_LIMIT = 24

# Cells sampled when checking whether an expression layer is log-normalized
CCC_CHECK_CELLS = 2000

def CCCwrap(s, width=14):
    """Wrap a cell type name, breaking only at spaces or after '/', never inside a marker name."""
    lines, line = [], ''
    for token in re.findall(r'[^ /]+/?|\s+', str(s)):
        if line and len(line) + len(token.rstrip()) > width:
            lines.append(line.strip())
            line = token.lstrip()
        else:
            line += token
    lines.append(line.strip())
    return '\n'.join(l for l in lines if l)

def CCCpatchLiana():
    """
    Work around a rank_aggregate bug in liana (present in 1.5.0 and 1.10.0):
    NATMI and Connectome share the 'expr_prod' column, which gets converted to
    ranks once per method. The second pass reverses the order, so the weakest
    interactions look strongest. Rank each score column only once.
    """
    from liana.method._pipe_utils import _aggregate as agg
    if getattr(agg, '_vip_patched', False):
        return
    original = agg._rank_aggregate

    def rank_once(lr_res, specs, aggregate_method):
        unique_specs, seen = {}, set()
        for method_name, (score_name, ascending) in specs.items():
            if score_name not in seen:
                seen.add(score_name)
                unique_specs[method_name] = (score_name, ascending)
        return original(lr_res, unique_specs, aggregate_method)

    agg._rank_aggregate = rank_once
    agg._vip_patched = True

def CCCtidyDotplot(fig, res):
    """
    Make liana's dotplot readable with many senders: drop empty target columns
    per panel, wrap long cell type names, and widen the figure to fit.
    """
    import plotnine as p9

    wrap = CCCwrap
    n_cols = len(res[['source', 'target']].drop_duplicates())
    n_rows = len(res[['ligand_complex', 'receptor_complex']].drop_duplicates())
    return (fig
            + p9.facet_grid('~source', scales='free_x', space='free_x',
                            labeller=p9.labeller(cols=wrap))
            + p9.scale_x_discrete(labels=lambda labels: [wrap(l) for l in labels])
            + p9.theme(strip_text=p9.element_text(size=10, colour="black"),
                       axis_text_x=p9.element_text(size=9, face="bold", angle=90),
                       figure_size=(min(4 + 0.9 * n_cols, 24), min(3 + 0.35 * n_rows, 20))))

def CCCguessSpecies(genes):
    """Mouse gene symbols are title case (Cd4), human are upper case (CD4)."""
    sample = [g for g in genes[:5000] if any(c.isalpha() for c in g)]
    nUpper = sum(1 for g in sample if g == g.upper())
    nTitle = sum(1 for g in sample if g[0].isupper() and g[1:] != g[1:].upper())
    return 'mouse' if nTitle > nUpper else 'human'

def CCCuseSymbols(adata, var_index):
    """Use the same gene-name column as the rest of VIP (data['var_index'])."""
    if not var_index or var_index not in adata.var.columns:
        return adata
    symbols = adata.var[var_index].astype(str)
    if list(symbols) == list(adata.var_names):
        return adata
    mapping = dict(zip(adata.var_names, symbols))
    if adata.raw is not None:
        rawA = adata.raw.to_adata()
        rawA.var_names = [mapping.get(g, g) for g in rawA.var_names]
        rawA.var_names_make_unique()
        adata.raw = rawA
    adata.var_names = symbols.values
    adata.var_names_make_unique()
    return adata

def CCCscoreCols(method, liana_res):
    """Magnitude/specificity score columns (and sort direction) for a LIANA method."""
    cols = []
    for kind in ['magnitude', 'specificity']:
        col = getattr(method, kind, None)
        asc = getattr(method, kind + '_ascending', True)
        if col is None and kind + '_rank' in liana_res.columns:  # rank_aggregate
            col, asc = kind + '_rank', True
        cols.append((col, asc) if col in liana_res.columns else (None, True))
    return cols

def CCCfilterGroups(adata, groupby, min_cells):
    group_counts = adata.obs[groupby].value_counts()
    valid_groups = group_counts[group_counts >= min_cells].index.tolist()
    return adata[adata.obs[groupby].isin(valid_groups)].copy(), valid_groups, group_counts

def CCClayerKeys(adata):
    """Expression layers a user can pick: X, .raw, and every adata.layers key."""
    return ['X'] + (['raw'] if adata.raw is not None else []) + [str(k) for k in adata.layers.keys()]

def CCClayerMatrix(adata, key):
    if key == 'X':
        return adata.X
    if key == 'raw':
        return adata.raw.X
    return adata.layers[key]

def CCClayerArgs(key):
    """LIANA arguments that make it read this layer."""
    if key == 'raw':
        return dict(use_raw=True, layer=None)
    return dict(use_raw=False, layer=None if key == 'X' else key)

def CCCcheckLayer(M):
    """
    Is this layer log-normalized, with every cell normalized for sequencing depth?
    The comparison view plots absolute values, so anything else would show depth
    differences as biology. Returns (status, message), status 'ok' | 'warn' | 'fail'.

    Calibrated 2026-10-22 on pbmc68k and synthetic data (CHANGES_FROM_UPSTREAM.md):
      - negative values      -> scaled / z-scored                     -> fail
      - mostly whole numbers -> raw counts                            -> fail
      - max > 50             -> not log scale                         -> fail
      - most cells share the same smallest non-zero value -> log of counts that were
        never depth-normalized (a count of 1 is log(2) in every cell) -> fail.
        Normalized data: 0% of cells; unnormalized: 100%. Unlike row sums, this
        doesn't change when the layer is a gene subset.
      - expm1(x) / expm1(cell's smallest value) not whole numbers -> can't confirm
        the layer is log1p of per-cell-scaled counts (other transform?) -> warn
    """
    n = M.shape[0]
    rows = np.sort(np.random.RandomState(0).choice(n, min(n, CCC_CHECK_CELLS), replace=False))
    sub = M[rows]
    sub = sub.toarray() if scipy.sparse.issparse(sub) else np.asarray(sub)
    sub = sub.astype(float)
    nz = sub[sub != 0]
    if nz.size == 0:
        return 'fail', 'layer has no non-zero values'
    if sub.min() < 0:
        return 'fail', f'has negative values (min {sub.min():.2f}): looks scaled / z-scored, not log-normalized'
    if np.mean(nz == np.round(nz)) >= 0.95:
        return 'fail', 'values are whole numbers: looks like raw counts, not log-normalized'
    if sub.max() > 50:
        return 'fail', f'max value {sub.max():.0f} is too high for log scale'
    cells = [r[r > 0] for r in sub if (r > 0).any()]
    mins = np.array([c.min() for c in cells])
    vals, counts = np.unique(np.round(mins, 3), return_counts=True)
    modal = vals[np.argmax(counts)]
    same = np.mean(np.abs(mins - modal) < 1e-3)
    if same >= 0.5:
        return 'fail', (f'{same:.0%} of cells have the same smallest value ({modal:.3f}): looks like '
                        'log of counts that were never normalized for sequencing depth')
    whole = np.mean([np.mean(np.abs(v - np.round(v)) < 0.05)
                     for v in (np.expm1(c) / np.expm1(c.min()) for c in cells)])
    if whole < 0.9:
        return 'warn', ("log scale, but can't confirm it is log1p of depth-normalized counts "
                        "(other transformation or log base?)")
    return 'ok', 'log-normalized, per-cell depth normalization confirmed'

def CCClayerOptions(adata):
    """JSON for the frontend's layer dropdown: every layer with its check result."""
    layers = []
    for key in CCClayerKeys(adata):
        try:
            status, message = CCCcheckLayer(CCClayerMatrix(adata, key))
        except Exception as e:
            status, message = 'fail', f'could not check: {e}'
        layers.append(dict(key=key, status=status, message=message))
    auto = next((l['key'] for l in layers if l['status'] != 'fail'), None)
    return json.dumps(dict(layers=layers, auto=auto))

def CCCresolveLayer(adata, key):
    """Pick and check the layer. Returns (key, status, message) or (None, None, error)."""
    if key in (None, '', 'auto'):
        failures = []
        for k in CCClayerKeys(adata):
            status, message = CCCcheckLayer(CCClayerMatrix(adata, k))
            if status != 'fail':
                return k, status, message
            failures.append(f"  {k}: {message}")
        return None, None, ("No log-normalized expression layer found:\n" + "\n".join(failures))
    if key not in CCClayerKeys(adata):
        return None, None, f"Expression layer '{key}' not found in dataset"
    status, message = CCCcheckLayer(CCClayerMatrix(adata, key))
    if status == 'fail':
        return None, None, f"Layer '{key}' can't be used for the comparison view:\n{message}"
    return key, status, message

def CCCcompare(li, adata, groupby, compute, display, mode, resource, notes, dpi):
    """
    Condition comparison on ABSOLUTE values, not LIANA's within-run ranks.

    For each (ligand -> receptor, sender, target, condition), per replicate:
        prop = min(ligand_props, receptor_props)    fraction of cells expressing
        expr = (ligand_means + receptor_means) / 2  mean expression (LIANA's lr_means,
               computed here because return_all_lrs overwrites lr_means of filtered rows)
    then the mean across replicates, each weighted equally. A replicate counts only
    if it has >= min_cells_per_sample cells of both sender and target.

    Dot state, from k = replicates where prop >= expr_prop, out of n:
        k == 0      -> '-' (not detected)
        3k >= 2n    -> filled (detected in at least 2/3 of replicates)
        otherwise   -> ring
    Without a sample column, cells are pooled per condition (n = 1): descriptive only.
    """
    compare_by = compute['compare_by']
    levels = [str(l) for l in (compute.get('compare_levels') or [])]
    if len(levels) != 2 or levels[0] == levels[1]:
        return Msg("Pick two different conditions\n(reference and test) to compare.")
    ref, test = levels
    if compare_by not in adata.obs.columns:
        return Msg(f"Annotation '{compare_by}' not found in dataset")
    if compare_by == groupby:
        return Msg("The condition column must differ\nfrom the cell type annotation.")
    sample_key = compute.get('sample_key') or None
    if sample_key and sample_key not in adata.obs.columns:
        return Msg(f"Sample column '{sample_key}' not found in dataset")
    if sample_key in (groupby, compare_by):
        return Msg("The sample column must differ from the\ncell type and condition columns.")
    min_cells = int(compute.get('min_cells_per_sample') or CCC_SAMPLE_MIN_CELLS)

    cond = adata.obs[compare_by].astype(str)
    adata = adata[cond.isin(levels).values].copy()
    cond = adata.obs[compare_by].astype(str).values
    missing = [l for l in levels if l not in set(cond)]
    if missing:
        return Msg(f"No cells with {compare_by} = {', '.join(missing)}\nin the selected cells.")

    layer_key, layer_status, layer_msg = CCCresolveLayer(adata, compute.get('layer'))
    if layer_key is None:
        return Msg(layer_msg)
    notes.append(f"Expression layer: {layer_key} ({layer_msg}).")

    cell_type = adata.obs[groupby].astype(str).values
    if sample_key:
        sample = adata.obs[sample_key].astype(str).values
        per = pd.crosstab(sample, cond)
        mixed = per.index[(per > 0).sum(axis=1) > 1].tolist()
        if mixed:
            return Msg("Each replicate must belong to one condition.\n"
                       f"In both {ref} and {test}: {', '.join(mixed[:8])}"
                       f"{' ...' if len(mixed) > 8 else ''}")
    else:
        sample = cond  # pooled: one pseudo-replicate per condition
        notes.append("No sample column: cells pooled per condition. Descriptive only; "
                     "mouse-to-mouse variation can't be assessed.")
    min_reps = 2 if sample_key else 1
    counts = pd.crosstab([cond, sample], cell_type)

    types = sorted(set(cell_type))
    if mode == 'targeted':
        s, r = str(display.get('sender')), str(display.get('receiver'))
        absent = [t for t in (s, r) if t not in types]
        if absent:
            return Msg(f"No cells of {', '.join(absent)} in\n{ref} or {test}.")
        pairs = [(s, r)]
        if display.get('direction') == 'both_ways' and s != r:
            pairs.append((r, s))
    else:
        pairs = [(a, b) for a in types for b in types]

    # Replicates that qualify for each (sender, target, condition)
    eligible = {}
    for c in levels:
        cnt = counts.loc[c]
        for s, t in pairs:
            eligible[(s, t, c)] = [smp for smp in cnt.index
                                   if cnt.loc[smp].get(s, 0) >= min_cells and cnt.loc[smp].get(t, 0) >= min_cells]

    def countLine(s, t, c):
        cnt = counts.loc[c]
        per_rep = ", ".join(f"{smp}: {cnt.loc[smp].get(s, 0)}/{cnt.loc[smp].get(t, 0)}" for smp in cnt.index[:6])
        return (f"  {c}: {len(eligible[(s, t, c)])} of {len(cnt)} qualify "
                f"({per_rep}{' ...' if len(cnt) > 6 else ''})")

    blocked = [k for k, v in eligible.items() if len(v) < min_reps]
    if mode == 'targeted' and blocked:
        lines = [f"Not enough {'mice' if sample_key else 'cells'} to compare. Need "
                 f"{'at least 2 mice per condition, each' if sample_key else 'each condition'} "
                 f"with >= {min_cells} cells of both sender and receiver "
                 "(counts below are sender/receiver cells)."]
        for s, t, c in blocked:
            lines.append(f"{s} -> {t}")
            lines.append(countLine(s, t, c))
        return Msg("\n".join(textwrap.fill(l, 70, subsequent_indent='    ') for l in lines))
    if blocked:
        notes.append(f"{len(blocked)} sender/target/condition combinations have fewer than "
                     f"{min_reps} qualifying {'mice' if sample_key else 'cell groups'} and are shown as n/a.")
    if sample_key:
        few = sorted({(s, t, c) for (s, t, c), v in eligible.items() if 2 <= len(v) < 3})
        for s, t, c in few[:5]:
            notes.append(f"Warning: {s} -> {t} in {c} has only {len(eligible[(s, t, c)])} mice; "
                         "the average is unstable.")

    # Run LIANA once per replicate, on just the cell types its qualifying pairs need.
    # (Own loop rather than cellphonedb.by_sample: by_sample fails entirely when one
    # replicate lacks a cell type, and can't give each replicate its own pairs.)
    supp = ['ligand_props', 'receptor_props', 'ligand_means', 'receptor_means']
    keep = ['source', 'target', 'ligand_complex', 'receptor_complex'] + supp
    per_rep = []
    for c in levels:
        for smp in counts.loc[c].index:
            smp_pairs = [(s, t) for (s, t) in pairs if smp in eligible[(s, t, c)]]
            if not smp_pairs:
                continue
            need = {x for p in smp_pairs for x in p}
            sub = adata[(cond == c) & (sample == smp) & np.isin(cell_type, list(need))].copy()
            try:
                li.mt.cellphonedb(sub, groupby=groupby, resource_name=resource, expr_prop=CCC_EXPR_PROP,
                                  min_cells=min_cells, groupby_pairs=pd.DataFrame(smp_pairs, columns=['source', 'target']),
                                  supp_columns=supp, return_all_lrs=True, n_perms=None, verbose=False,
                                  **CCClayerArgs(layer_key))
                res = sub.uns['liana_res'][keep].copy()
            except Exception as e:
                ppr.pprint(f"CCC compare: LIANA failed for {c}/{smp}: {traceback.format_exc()}")
                notes.append(f"{c} / {smp}: LIANA failed ({str(e).split('[')[0][:120]}); left out.")
                for (s, t) in smp_pairs:
                    eligible[(s, t, c)].remove(smp)
                continue
            res['condition'], res['sample'] = c, smp
            per_rep.append(res)
    if not per_rep:
        return Msg("No ligand-receptor results for any replicate.\n" + "\n".join(notes))
    df = pd.concat(per_rep, ignore_index=True)
    df['source'], df['target'] = df['source'].astype(str), df['target'].astype(str)
    df['prop'] = df[['ligand_props', 'receptor_props']].min(axis=1)
    df['expr'] = (df['ligand_means'] + df['receptor_means']) / 2

    # Aggregate across replicates. Every qualifying replicate counts, including ones
    # with no row for an interaction (prop and expr 0).
    lr = ['ligand_complex', 'receptor_complex']
    summary, slots = [], {}
    for s, t in pairs:
        g = df[(df['source'] == s) & (df['target'] == t)]
        lr_index = pd.MultiIndex.from_frame(g[lr].drop_duplicates()) if len(g) else None
        for c in levels:
            reps = eligible[(s, t, c)]
            if len(reps) < min_reps:
                slots[(s, t, c)] = (len(reps), True)  # n/a: too few qualifying replicates
                continue
            slots[(s, t, c)] = (len(reps), None)
            if lr_index is None:
                continue
            gc_ = g[g['condition'] == c]
            p = gc_.pivot_table(index=lr, columns='sample', values='prop', aggfunc='first').reindex(index=lr_index, columns=reps).fillna(0)
            e = gc_.pivot_table(index=lr, columns='sample', values='expr', aggfunc='first').reindex(index=lr_index, columns=reps).fillna(0)
            n = len(reps)
            k = (p >= CCC_EXPR_PROP).sum(axis=1)
            out = pd.DataFrame({'mean_prop': p.mean(axis=1), 'sd_prop': p.std(axis=1, ddof=1) if n > 1 else np.nan,
                                'mean_expr': e.mean(axis=1), 'sd_expr': e.std(axis=1, ddof=1) if n > 1 else np.nan,
                                'n_mice': n, 'n_detected': k}).reset_index()
            out['state'] = np.where(k.values == 0, 'none', np.where(3 * k.values >= 2 * n, 'filled', 'ring'))
            out.insert(0, 'condition', c)
            out.insert(0, 'target', t)
            out.insert(0, 'source', s)
            summary.append(out)
    if not summary:
        return Msg("Nothing to compare: every sender/target/condition\nwas left out (see notes).\n" + "\n".join(notes[-3:]))
    summary = pd.concat(summary, ignore_index=True)

    # Top N: largest mean expression in either condition, among detected slots.
    # Neutral on purpose: sorting by the difference would look like a result.
    keys = ['source', 'target'] + lr
    detected = summary[summary['state'] != 'none']
    if len(detected) == 0:
        return Msg("No interaction is detected in either condition\nfor the selected cell types.")
    top_n = int(display.get('top_n', 20))
    best = detected.groupby(keys)['mean_expr'].max().sort_values(ascending=False).head(top_n)
    top_lr = list(dict.fromkeys(zip(best.index.get_level_values(2), best.index.get_level_values(3))))
    shown_pairs = sorted(set(zip(best.index.get_level_values(0), best.index.get_level_values(1))), key=pairs.index)
    shown = summary[summary.set_index(lr).index.isin(top_lr) &
                    summary.set_index(['source', 'target']).index.isin(shown_pairs)]

    img = ""
    try:
        img = CCCcomparisonPlot(shown, top_lr, shown_pairs, slots, ref, test, bool(sample_key),
                                layer_key, min_cells, dpi)
    except Exception as e:
        ppr.pprint(f"CCC comparison plot failed: {traceback.format_exc()}")
        notes.append(f"Plot could not be drawn ({e}); the table has the values.")

    order = {k_: i for i, k_ in enumerate(top_lr)}
    shown = shown.assign(_o=[order[(a, b)] for a, b in zip(shown['ligand_complex'], shown['receptor_complex'])])
    shown = shown.sort_values(['_o', 'source', 'target', 'condition']).drop(columns='_o')
    cols = ['source', 'target', 'ligand_complex', 'receptor_complex', 'condition', 'state', 'n_mice', 'n_detected',
            'mean_prop', 'sd_prop', 'mean_expr', 'sd_expr']
    csv = shown[cols].round(4).to_csv(index=False)
    notes.insert(0, f"Comparison view: {ref} (reference) vs {test} (test); "
                    f"{'mean across mice' if sample_key else 'pooled cells, no replicates'}; "
                    f"replicates need >= {min_cells} cells of sender and target; resource: {resource}.")
    meta = dict(view='comparison' if sample_key else 'descriptive', layer=layer_key,
                layer_status=layer_status, layer_message=layer_msg, reference=ref, test=test)
    return json.dumps([csv, img, notes, meta])

def CCCcomparisonPlot(res, lr_rows, pairs, slots, ref, test, replicates, layer_key, min_cells, dpi):
    """
    Dot plot of absolute values across two conditions. Senders are panels; within a
    panel each target gets two adjacent columns (ref, test). With more than
    CCC_SLOT_LIMIT columns, the two conditions are stacked as rows instead.
    """
    conds = [ref, test]
    cmap = plt.get_cmap('viridis')
    vmax = res.loc[res['state'] != 'none', 'mean_expr'].max()
    norm = matplotlib.colors.Normalize(0, vmax if vmax > 0 else 1)
    area = lambda p: 20 + 380 * float(p)
    rows = {lr_: i for i, lr_ in enumerate(lr_rows)}
    labels = [f"{a} -> {b}" for a, b in lr_rows]
    lookup = {(r.source, r.target, r.condition, r.ligand_complex, r.receptor_complex): r for r in res.itertuples()}
    senders = list(dict.fromkeys(s for s, _ in pairs))
    targets = {s: [t for s2, t in pairs if s2 == s] for s in senders}
    stacked = 2 * len(pairs) > CCC_SLOT_LIMIT
    warn_colour = '#c25e00'

    def dot(ax, x, y, r):
        if r is None or r.state == 'none':
            ax.text(x, y, '–', ha='center', va='center', fontsize=13, color='#aaa')
        elif r.state == 'ring':
            ax.scatter(x, y, s=area(r.mean_prop), facecolors='white', edgecolors=cmap(norm(r.mean_expr)), linewidths=2)
        else:
            ax.scatter(x, y, s=area(r.mean_prop), color=cmap(norm(r.mean_expr)), edgecolors='#444', linewidths=.4)

    def column(ax, x, s, t, c):
        n, na = slots[(s, t, c)]
        if na:
            ax.add_patch(matplotlib.patches.Rectangle((x - .42, -.5), .84, len(lr_rows), color='#eeeeee', zorder=0))
            ax.text(x, (len(lr_rows) - 1) / 2, 'n/a', ha='center', va='center', fontsize=8, color='#777')  # reason is in the legend
        else:
            for (a, b), y in rows.items():
                dot(ax, x, y, lookup.get((s, t, c, a, b)))
        return n, na

    def tick(name, n, na):
        if na:
            return f"{name}\nn/a", '#777'
        if not replicates:
            return f"{name}\npooled", 'black'
        return (f"{name}\nn={n} ⚠", warn_colour) if n < 3 else (f"{name}\nn={n}", 'black')

    label_in = 0.075 * max(len(l) for l in labels) + 0.3
    legend_in = 2.9
    n_rows = len(lr_rows)
    with matplotlib.rc_context({'figure.autolayout': False}):  # VIP turns autolayout on globally
        if not stacked:
            units = [max(len(targets[s]) * 2.6 - 0.6, 3.4) for s in senders]  # min width fits the sender title
            width = label_in + 0.55 * sum(units) + 0.4 * len(senders) + legend_in
            height = 2.3 + 0.34 * n_rows
            fig = plt.figure(figsize=(min(width, 30), min(height, 24)))
            gs = fig.add_gridspec(1, len(senders) + 1, width_ratios=units + [legend_in / 0.55],
                                  left=label_in / width, right=0.99, top=1 - 0.9 / height, bottom=1.15 / height, wspace=0.12)
            axes = [fig.add_subplot(gs[0, i]) for i in range(len(senders))]
            for ax, s in zip(axes, senders):
                ticks, tick_labels, tick_colours = [], [], []
                for j, t in enumerate(targets[s]):
                    base = j * 2.6
                    for ci, c in enumerate(conds):
                        n, na = column(ax, base + ci, s, t, c)
                        lab, col = tick(c, n, na)
                        ticks.append(base + ci)
                        tick_labels.append(lab)
                        tick_colours.append(col)
                    ax.text(base + .5, -1.0, '→ ' + CCCwrap(t), ha='center', va='bottom', fontsize=9, fontweight='bold')
                    if j > 0:
                        ax.axvline(base - .8, color='#bbb', lw=1)
                ax.set_xticks(ticks)
                ax.set_xticklabels(tick_labels, fontsize=8)
                for lab, col in zip(ax.get_xticklabels(), tick_colours):
                    lab.set_color(col)
                ax.set_xlim(-.6, (len(targets[s]) - 1) * 2.6 + 1.6)
                ax.set_title('Sender:\n' + CCCwrap(s, int(units[senders.index(s)] * 0.55 * 11)), fontsize=9.5, pad=30)
        else:
            # Rotated target labels set the gap between the two rows
            longest = max(len(line) for s in senders for t in targets[s] for line in CCCwrap(t, 12).split('\n'))
            tick_in = 0.075 * max(longest, 6) + 0.45
            panel_units = [max(len(targets[s]), 2.4) for s in senders]  # min width fits the sender title
            axes_in = 0.34 * n_rows + 0.3
            title_in, row_label_in, caption_in = 0.9, 0.45, 0.6
            width = label_in + 0.6 * sum(panel_units) + 0.15 * len(senders) + legend_in
            height = title_in + row_label_in + 2 * (axes_in + tick_in) + row_label_in + caption_in
            fig = plt.figure(figsize=(min(width, 30), min(height, 30)))
            gs = fig.add_gridspec(2, len(senders) + 1, width_ratios=panel_units + [legend_in / 0.6],
                                  left=label_in / width, right=0.99,
                                  top=1 - (title_in + row_label_in) / height, bottom=(tick_in + caption_in) / height,
                                  wspace=0.12, hspace=(tick_in + row_label_in) / axes_in)
            axes = []
            for ri, c in enumerate(conds):
                for i, s in enumerate(senders):
                    ax = fig.add_subplot(gs[ri, i])
                    axes.append(ax)
                    ticks, tick_labels, tick_colours = [], [], []
                    for j, t in enumerate(targets[s]):
                        n, na = column(ax, j, s, t, c)
                        lab, col = tick(CCCwrap(t, 12), n, na)
                        ticks.append(j)
                        tick_labels.append(lab)
                        tick_colours.append(col)
                    ax.set_xticks(ticks)
                    ax.set_xticklabels(tick_labels, fontsize=7.5, rotation=90)
                    for lab, col in zip(ax.get_xticklabels(), tick_colours):
                        lab.set_color(col)
                    ax.set_xlim(-.6, len(targets[s]) - .4)
                    if ri == 0:
                        ax.set_title('Sender:\n' + CCCwrap(s, int(panel_units[i] * 0.6 * 11)), fontsize=9, pad=row_label_in * 72 + 4)
                    if i == 0:  # one bold label per condition row
                        ax.annotate(c, xy=(0, 1), xycoords='axes fraction', xytext=(-label_in * 72 + 6, 8),
                                    textcoords='offset points', fontsize=11, fontweight='bold', va='bottom')
        for i, ax in enumerate(axes):
            ax.set_yticks(range(n_rows))
            ax.set_yticklabels(labels if (i % len(senders) == 0) else [], fontsize=8)
            ax.set_ylim(n_rows - .4, -.6 if stacked else -1.6)
            ax.tick_params(length=0)
            for side in ['top', 'right', 'left']:
                ax.spines[side].set_visible(False)

        # Legend: dot states, size, colour
        lax = fig.add_subplot(gs[:, -1] if stacked else gs[0, -1])
        lax.axis('off')
        lax.set_xlim(0, 1)
        lax.set_ylim(0, 1)
        mid = cmap(norm(norm.vmax * .6))
        items = [('filled', 'Detected in >= 2/3 of mice' if replicates else 'Detected (>= 10% of cells)')]
        if replicates:
            items.append(('ring', 'Detected in < 2/3 of mice'))
        items += [('none', 'Not detected in any mouse' if replicates else 'Not detected (< 10% of cells)'),
                  ('na', f"n/a: < 2 mice with >= {min_cells} cells" if replicates else f"n/a: < {min_cells} cells")]
        if replicates:
            items.append(('warn', 'n < 3 mice (column header)'))
        y = .97
        for kind, text in items:
            if kind == 'filled':
                lax.scatter(.07, y, s=area(.5), color=mid, edgecolors='#444', linewidths=.4)
            elif kind == 'ring':
                lax.scatter(.07, y, s=area(.5), facecolors='white', edgecolors=mid, linewidths=2)
            elif kind == 'none':
                lax.text(.07, y, '–', ha='center', va='center', fontsize=13, color='#aaa')
            elif kind == 'na':
                lax.add_patch(matplotlib.patches.Rectangle((.02, y - .02), .1, .04, color='#eeeeee'))
                lax.text(.07, y, 'n/a', ha='center', va='center', fontsize=6.5, color='#777')
            else:
                lax.text(.07, y, '⚠', ha='center', va='center', fontsize=10, color=warn_colour)
            lax.text(.17, y, text, va='center', fontsize=7.5, color=warn_colour if kind == 'warn' else 'black')
            y -= .065
        lax.text(.02, y - .02, 'Size: % of cells expressing\n(min of ligand, receptor)', fontsize=7.5, va='top')
        for j, p in enumerate([.1, .3, .6, .9]):
            lax.scatter(.1 + j * .22, y - .13, s=area(p), color='#bbb')
            lax.text(.1 + j * .22, y - .19, f"{int(p * 100)}%", ha='center', fontsize=7)
        cax = lax.inset_axes([.05, y - .3, .85, .025])
        cb = fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation='horizontal')
        cb.ax.tick_params(labelsize=7)
        cb.set_label(f"Mean expression ({layer_key}, log-normalized)", fontsize=7.5)

        caption = ((f"Absolute values on layer '{layer_key}' (log-normalized), averaged across mice "
                    "(each mouse weighted equally). NOT LIANA's within-run ranks. Not a significance test: "
                    "a visible difference may be within normal mouse-to-mouse variation.")
                   if replicates else
                   (f"DESCRIPTIVE ONLY: cells pooled per condition, no replicates, so mouse-to-mouse variation "
                    f"is unknown. Absolute values on layer '{layer_key}' (log-normalized), not LIANA ranks. "
                    "Not a significance test."))
        fig.text(0.01, 0.01, textwrap.fill(caption, int(fig.get_figwidth() * 15)), fontsize=8,
                 color='#333', va='bottom', ha='left')

        figD = BytesIO()
        fig.savefig(figD, format='png', dpi=dpi)
    plt.close(fig)
    img = base64.encodebytes(figD.getvalue()).decode("utf-8")
    figD.close()
    return img

def CCC(data):
    """
    Cell-cell communication analysis using LIANA.

    Request format (from CCCbuildRequest() in interface.html):
    {
        method: "CCC",
        mode: "targeted" | "untargeted",
        compute: {
            cells: "all" | "celllist1" | "celllist2",
            cell_indices: [...] | null,
            lasso_groups: {"Selection 1": [...], "Selection 2": [...]} | null,
            groupby: str,   # ignored when lasso_groups is set
            compare_by: str | null,           # set -> comparison view (CCCcompare)
            compare_levels: [ref, test],
            sample_key: str | null,           # replicate (mouse) column; null -> pooled, descriptive
            layer: "auto" | "X" | "raw" | <layers key>,
            min_cells_per_sample: int,
            ccc_method: str,
            resource: str,
            min_cells: int,
            n_perms: int
        },
        display: {
            sender: str | null,
            receiver: str | null,
            direction: str,
            top_n: int,
            sort_by: str
        }
    }

    With compare_by set, CCCcompare() plots absolute values (fraction expressing,
    mean expression) averaged across replicates, not ranks; see its docstring.
    {action: "layers"} returns the expression layers and their normalization checks.

    Returns: JSON array [csv_data, base64_image, notes] (comparison view adds a 4th
    element with view/layer metadata for the frontend banner)
    """

    # Imported here so a missing/broken liana install only disables CCC,
    # not the whole VIP plugin
    try:
        import liana as li
    except Exception as e:
        return Msg(f"LIANA is not available on the server:\n{str(e)}")
    try:
        CCCpatchLiana()
    except Exception as e:
        ppr.pprint(f"Could not patch liana rank aggregation: {e}")

    notes = []

    # 1. Access full AnnData from data adapter
    scD = data.get('data_adapter')
    if scD is None:
        return Msg("No data adapter available")
    if data.get('action') == 'layers':
        return CCClayerOptions(scD.data)

    # Work with a copy to avoid modifying original
    adata = scD.data.copy()

    # 2. Extract compute parameters
    compute = data.get('compute', {})
    cells_selection = compute.get('cells', 'all')

    lasso_groups = compute.get('lasso_groups')
    if lasso_groups:
        # Sender/receiver come from the two lasso selections: label those cells
        # by selection name and drop everything else
        idx = {name: set(int(i) for i in cells) for name, cells in lasso_groups.items()}
        if len(idx) != 2 or any(len(v) == 0 for v in idx.values()):
            return Msg("Lasso mode needs cells in both Selection 1 and Selection 2.")
        (name_a, a), (name_b, b) = idx.items()
        overlap = a & b
        if overlap:
            notes.append(f"{len(overlap)} cells were in both selections and were excluded.")
            a, b = a - overlap, b - overlap
        label = np.full(adata.n_obs, '', dtype=object)
        label[sorted(a)] = name_a
        label[sorted(b)] = name_b
        adata.obs[CCC_LASSO_COL] = label
        adata = adata[label != ''].copy()
        compute['groupby'] = CCC_LASSO_COL
        if not compute.get('compare_by'):  # the comparison view has no specificity scores
            notes.append("Lasso mode: specificity scores are relative to the two selections only.")
    # Filter cells if specific selection requested
    elif cells_selection != 'all':
        cell_indices = compute.get('cell_indices')
        if cell_indices and len(cell_indices) > 0:
            adata = adata[cell_indices, :].copy()
        else:
            return Msg("No cells selected. Please select cells first.")

    # LIANA matches the L-R database by gene symbol
    adata = CCCuseSymbols(adata, data.get('var_index'))

    # 3. Validate groupby / compare_by columns exist
    groupby = compute.get('groupby')
    if not groupby or groupby == 'NA':
        return Msg("Please select a cell type annotation column")

    if groupby not in adata.obs.columns:
        return Msg(f"Annotation '{groupby}' not found in dataset")

    # Ensure groupby is categorical/string
    adata.obs[groupby] = adata.obs[groupby].astype(str)

    # Condition comparison has its own path (CCCcompare, after the resource is known)
    compare_by = compute.get('compare_by')
    conditions = [None]

    # 4. Check for raw counts
    if adata.raw is not None:
        use_raw = True
    else:
        # Check if X might contain raw counts (integers or high values)
        sample_max = adata.X[:100, :100].max() if hasattr(adata.X, '__getitem__') else 50
        if sample_max < 20:  # Likely log-normalized
            ppr.pprint("Warning: No raw counts detected. Using X directly.")
        use_raw = False

    # 5. Resolve resource (auto-detect species from gene symbol case)
    genes = list(adata.raw.var_names if use_raw else adata.var_names)
    species = CCCguessSpecies(genes)
    resource_key = compute.get('resource', 'auto')
    if resource_key == 'auto':
        resource_key = 'mouseconsensus' if species == 'mouse' else 'consensus'
    resource = CCC_RESOURCES.get(resource_key, 'consensus')
    if species == 'mouse' and resource != 'mouseconsensus':
        notes.append(f"Gene names look like mouse, but resource '{resource}' is human. "
                     "Most interactions will not match; consider the Mouse Consensus resource.")
    elif species == 'human' and resource == 'mouseconsensus':
        notes.append("Gene names look like human, but the Mouse Consensus resource was selected.")

    if compare_by:
        return CCCcompare(li, adata, groupby, compute, data.get('display', {}), data.get('mode', 'untargeted'),
                          resource, notes, int(data.get('figOpt', {}).get('dpi', 150)))

    # 6. Resolve method
    method_name = CCC_METHODS.get(compute.get('ccc_method', 'rank_aggregate'), 'rank_aggregate')
    method = getattr(li.mt, method_name, None)
    if method is None:
        return Msg(f"Method '{method_name}' is not available in this LIANA version")

    n_perms = compute.get('n_perms', 1000)
    if n_perms is not None and n_perms < 100:
        n_perms = None  # Disable permutation testing for speed

    # 7. Run LIANA within each condition
    min_cells = compute.get('min_cells', 20)
    results = []
    run_adata = None
    for cond in conditions:
        sub = adata if cond is None else adata[adata.obs[compare_by] == cond].copy()
        sub, valid_groups, group_counts = CCCfilterGroups(sub, groupby, min_cells)
        if len(valid_groups) < 2:
            count_str = ", ".join([f"{k}: {v}" for k, v in group_counts.items()])
            msg = (f"Need at least 2 cell types with >= {min_cells} cells each.\n"
                   f"Found {len(valid_groups)} valid groups.\n"
                   f"Group sizes: {count_str}")
            if cond is None:
                return Msg(msg)
            notes.append(f"Condition '{cond}' skipped. " + msg.replace("\n", " "))
            continue
        dropped = [str(g) for g in group_counts.index if g not in valid_groups]
        if dropped:
            notes.append(f"{'' if cond is None else cond + ': '}excluded cell types with < {min_cells} cells "
                         f"(this also changes specificity scores): {', '.join(dropped)}")

        try:
            method(
                sub,
                groupby=groupby,
                resource_name=resource,
                expr_prop=0.1,
                use_raw=use_raw,
                n_perms=n_perms,
                verbose=False
            )
        except Exception as e:
            ppr.pprint(f"LIANA error: {traceback.format_exc()}")
            err = str(e).split('[')[0][:300]  # LIANA lists every missing gene; keep the summary
            return Msg(f"LIANA analysis failed{'' if cond is None else ' for ' + cond}:\n{err}\n" + "\n".join(notes))

        if 'liana_res' not in sub.uns or len(sub.uns['liana_res']) == 0:
            if cond is None:
                return Msg("No ligand-receptor interactions detected\nbetween the selected cell types.")
            notes.append(f"Condition '{cond}': no interactions detected.")
            continue

        res = sub.uns['liana_res'].copy()
        if cond is not None:
            res.insert(0, 'condition', cond)
        results.append(res)
        run_adata = sub

    if len(results) == 0:
        return Msg("No interactions found in any selected condition.\n" + "\n".join(notes))

    liana_res = pd.concat(results, ignore_index=True)
    liana_res['source'] = liana_res['source'].astype(str)
    liana_res['target'] = liana_res['target'].astype(str)

    # 8. Filter for targeted mode
    display = data.get('display', {})
    mode = data.get('mode', 'untargeted')

    if mode == 'targeted':
        sender = display.get('sender')
        receiver = display.get('receiver')
        direction = display.get('direction', 'one_way')

        if sender and receiver:
            if direction == 'one_way':
                liana_res = liana_res[
                    (liana_res['source'] == str(sender)) &
                    (liana_res['target'] == str(receiver))
                ]
            else:  # both_ways
                liana_res = liana_res[
                    ((liana_res['source'] == str(sender)) & (liana_res['target'] == str(receiver))) |
                    ((liana_res['source'] == str(receiver)) & (liana_res['target'] == str(sender)))
                ]

    if len(liana_res) == 0:
        return Msg("No interactions found for\nthe selected sender/receiver pair.")

    # 9. Sort by the method's own score columns
    (mag_col, mag_asc), (spec_col, spec_asc) = CCCscoreCols(method, liana_res)
    if not (mag_col or spec_col):
        return Msg("Could not find score columns in the LIANA results")
    sort_by = display.get('sort_by', 'magnitude')
    if sort_by == 'pvalue' and 'cellphone_pvals' in liana_res.columns:
        sort_col, sort_asc = 'cellphone_pvals', True
    elif sort_by in ('specificity', 'pvalue') and spec_col:
        sort_col, sort_asc = spec_col, spec_asc
    elif mag_col:
        sort_col, sort_asc = mag_col, mag_asc
    else:
        sort_col, sort_asc = spec_col, spec_asc
    if sort_by == 'pvalue' and sort_col != 'cellphone_pvals':
        notes.append(f"P-values are not produced by this method; sorted by {sort_col} instead.")

    # 10. Keep the top_n interactions (best score in any condition), all conditions
    top_n = display.get('top_n', 20)
    keys = ['source', 'target', 'ligand_complex', 'receptor_complex']
    best = liana_res.groupby(keys)[sort_col].agg('min' if sort_asc else 'max')
    top_keys = best.sort_values(ascending=sort_asc).head(top_n).index
    # Rows come out grouped by interaction, conditions in the order they were run
    liana_res_display = liana_res.set_index(keys).loc[top_keys].reset_index()

    # 11. Create visualization
    colour, colour_asc = (mag_col, mag_asc) if mag_col else (spec_col, spec_asc)
    size, size_asc = (spec_col, spec_asc) if spec_col else (mag_col, mag_asc)
    dpi = int(data.get('figOpt', {}).get('dpi', 150))
    img = ""
    try:
        # Plot exactly the interactions shown in the table
        run_adata.uns['liana_res'] = liana_res_display
        source_labels = liana_res_display['source'].unique().tolist()
        target_labels = liana_res_display['target'].unique().tolist()
        fig = li.pl.dotplot(
            adata=run_adata,
            colour=colour,
            size=size,
            inverse_colour=colour_asc,
            inverse_size=size_asc,
            source_labels=source_labels,
            target_labels=target_labels,
            top_n=min(top_n, 50),
            orderby=sort_col,
            orderby_ascending=sort_asc,
            return_fig=True
        )

        try:
            fig = CCCtidyDotplot(fig, liana_res_display)
        except Exception as e:
            ppr.pprint(f"Dotplot layout tweak failed, using liana default: {e}")

        # Convert plotnine figure to base64
        figD = BytesIO()
        # VIP turns on figure.autolayout globally; it fights plotnine's own
        # layout and squashes the facets, so disable it for this plot
        with matplotlib.rc_context({'figure.autolayout': False}):
            fig.save(figD, format='png', dpi=dpi, verbose=False)
        img = base64.encodebytes(figD.getvalue()).decode("utf-8")
        figD.close()
    except Exception as e:
        ppr.pprint(f"Plot creation failed: {e}")
        # Continue without plot - we still have the table data

    # 12. Prepare CSV output
    output_cols = ['condition'] + keys + ['lr_means', mag_col, spec_col, 'cellphone_pvals']
    output_cols = list(dict.fromkeys(c for c in output_cols if c and c in liana_res_display.columns))
    csv_df = liana_res_display[output_cols].copy()

    csv_data = csv_df.to_csv(index=False)

    # 13. Return in VIP standard format, plus notes for the user
    notes.insert(0, f"Method: {method_name}; resource: {resource}; sorted by {sort_col}"
                    f"{' (lower = stronger)' if sort_asc else ''}.")
    return json.dumps([csv_data, img, notes])
