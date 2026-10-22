#!/usr/bin/env python
"""
Run cellxgene_VIP/ccc.py end to end, the way VIP calls it, without cellxgene.

    python tools/test_ccc_backend.py data/pbmc68k_reduced.h5ad [groupby]

Run in the VIP conda env after a VIP sync or a LIANA/pandas/plotnine upgrade.
Covers annotation mode, lasso mode (with a swap and overlapping cells) and an
error message. VIP's Msg() is stubbed, so this tests our code and its libraries,
not VIP itself (tools/check_ccc_compat.py covers the VIP side).
"""
import importlib.util
import json
import os
import sys
import types

import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['figure.autolayout'] = True  # VIPInterface sets this globally

VIP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'cellxgene_VIP')


def load_ccc():
    stub = types.ModuleType('server.app.VIPInterface')
    stub.Msg = lambda m: 'MSG:' + m
    for name in ['server', 'server.app']:
        sys.modules.setdefault(name, types.ModuleType(name))
    sys.modules['server.app.VIPInterface'] = stub
    spec = importlib.util.spec_from_file_location('ccc', os.path.join(VIP, 'ccc.py'))
    ccc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ccc)
    return ccc


def main(h5ad, groupby=None):
    import anndata as ad
    import numpy as np
    ccc = load_ccc()
    adata = ad.read_h5ad(h5ad)

    if groupby is None:  # first annotation with two groups of >= 20 cells
        for col in adata.obs.columns:
            counts = adata.obs[col].astype(str).value_counts()
            if 2 <= len(counts) <= 100 and (counts >= 20).sum() >= 2:
                groupby = col
                break
    labels = adata.obs[groupby].astype(str).values
    counts = adata.obs[groupby].astype(str).value_counts()
    a, b = counts[counts >= 20].index[:2]
    print(f'groupby={groupby}, sender={a}, receiver={b}')

    class D:
        data = adata

    def run(compute, display):
        c = dict(cells='all', groupby=groupby, resource='auto', ccc_method='rank_aggregate',
                 min_cells=5, n_perms=100)
        c.update(compute)
        d = dict(top_n=10, sort_by='magnitude', direction='one_way')
        d.update(display)
        return ccc.CCC(dict(data_adapter=D, var_index=None, compute=c, display=d,
                            mode='targeted', figOpt={'dpi': 60}))

    failures = []

    def check(name, res, source):
        if res.startswith('MSG:'):
            failures.append(f'{name}: {res}')
            return
        csv, img, notes = json.loads(res)
        rows = csv.strip().split('\n')[1:]
        sources = {r.split(',')[0] for r in rows}
        ok = rows and sources == {source} and len(img) > 100
        print(f'{"ok  " if ok else "FAIL"} {name}: {len(rows)} rows, sources={sources}, image={len(img) > 100}')
        if not ok:
            failures.append(name)

    check('annotation mode', run({}, dict(sender=a, receiver=b)), a)
    s1 = np.where(labels == a)[0].tolist()
    s2 = np.where(labels == b)[0].tolist()
    lasso = dict(lasso_groups={'Selection 1': s1, 'Selection 2': s2 + s1[:3]})
    check('lasso mode, swapped', run(lasso, dict(sender='Selection 2', receiver='Selection 1')), 'Selection 2')
    res = run(dict(lasso_groups={'Selection 1': s1, 'Selection 2': []}), {})
    ok = res.startswith('MSG:')
    print(f'{"ok  " if ok else "FAIL"} empty selection gives a message: {res[:60]}')
    if not ok:
        failures.append('empty selection')

    failures += test_layer_check(ccc)
    failures += test_comparison(ccc, adata, groupby, a, b, run)

    print('\nAll passed.' if not failures else f'\nFAILED: {failures}')
    return 1 if failures else 0


def test_layer_check(ccc):
    """CCCcheckLayer against the cases it was calibrated on (synthetic, so no data needed)."""
    import numpy as np
    rng = np.random.default_rng(0)
    failures = []
    for sigma in [0.6, 0.25]:  # uneven and even sequencing depth
        depth = rng.lognormal(8, sigma, 1000)
        counts = rng.poisson(np.outer(depth, rng.dirichlet(np.ones(3000) * 0.1))).astype(float)
        lognorm = np.log1p(counts / counts.sum(1, keepdims=True) * 1e4)
        cases = [('raw counts', counts, 'fail'), ('log1p, not depth-normalized', np.log1p(counts), 'fail'),
                 ('scaled', (lognorm - lognorm.mean(0)) / (lognorm.std(0) + 1e-9), 'fail'),
                 ('log-normalized', lognorm, 'ok'), ('log-normalized, 800-gene subset', lognorm[:, :800], 'ok')]
        for name, M, expected in cases:
            status, message = ccc.CCCcheckLayer(M)
            ok = status == expected
            print(f'{"ok  " if ok else "FAIL"} layer check, depth sigma {sigma}, {name}: {status} ({message[:50]})')
            if not ok:
                failures.append(f'layer check: {name}')
    return failures


def test_comparison(ccc, adata, groupby, a, b, run):
    """Comparison view with synthetic replicates: 4 'mice', 2 per condition."""
    import json
    import numpy as np
    failures = []
    adata.obs['_test_mouse'] = np.random.RandomState(0).choice(['m1', 'm2', 'm3', 'm4'], adata.n_obs)
    adata.obs['_test_cond'] = np.where(adata.obs['_test_mouse'].isin(['m1', 'm2']), 'ref', 'test')
    base = dict(compare_by='_test_cond', compare_levels=['ref', 'test'], sample_key='_test_mouse', layer='auto',
                min_cells_per_sample=5)

    def check(name, ok, detail):
        print(f'{"ok  " if ok else "FAIL"} {name}: {detail}')
        if not ok:
            failures.append(name)

    res = run(base, dict(sender=a, receiver=b))
    if res.startswith('MSG:'):
        check('comparison view runs', False, res[:120])
    else:
        csv, img, notes, meta = json.loads(res)
        header, rows = csv.split('\n')[0], csv.strip().split('\n')[1:]
        states = {r.split(',')[5] for r in rows}
        check('comparison view runs', meta['view'] == 'comparison' and len(img) > 100 and rows,
              f'{len(rows)} rows, view={meta["view"]}, layer={meta["layer"]}, states={sorted(states)}')
        check('comparison has no rank columns', 'rank' not in header, header)
    res = run(dict(base, min_cells_per_sample=10 ** 6), dict(sender=a, receiver=b))
    check('too few mice blocks', res.startswith('MSG:Not enough mice'), res[:60].replace('\n', ' '))
    mixed = dict(base, sample_key='_test_cond_mouse')
    adata.obs['_test_cond_mouse'] = 'same_mouse'
    res = run(mixed, dict(sender=a, receiver=b))
    check('replicate in both conditions blocks', res.startswith('MSG:Each replicate'), res[:60].replace('\n', ' '))
    res = run(dict(base, sample_key=None), dict(sender=a, receiver=b))
    check('no sample column gives descriptive view', not res.startswith('MSG:') and json.loads(res)[3]['view'] == 'descriptive',
          res[:60] if res.startswith('MSG:') else 'descriptive')
    return failures


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:3]))
