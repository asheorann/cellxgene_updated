#!/usr/bin/env python
"""
Check that VIP still provides everything the CCC extension relies on.

Run after every upstream VIP sync (tools/sync_vip_upstream.sh runs it for you):
    python tools/check_ccc_compat.py

Checks the hooks we add to VIP files and the VIP functions/state that
ccc.py, ccc.js and ccc.html use. Standard library only, so it runs in any env.
Exit code 0 = all required checks passed.
"""
import ast
import os
import re
import sys

VIP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'cellxgene_VIP')

# (file, regex, what it means). Failing any of these breaks CCC.
REQUIRED = [
    # Our hooks into VIP files
    ('VIPInterface.py', r'^import server\.app\.ccc as ccc', 'hook: VIPInterface imports ccc.py'),
    ('VIPInterface.py', r"'CCC'\s*:\s*ccc\.CCC", "hook: 'CCC' registered in distributeTask()"),
    ('interface.html', r'/static/ccc\.js', 'hook: interface.html loads ccc.js'),
    ('update.VIPInterface.sh', r'cp ccc\.py ', 'hook: install script copies ccc.py'),
    ('update.VIPInterface.sh', r'cp ccc\.js ccc\.html ', 'hook: install script copies ccc.js/ccc.html'),
    # Backend: what ccc.py gets from VIP
    ('VIPInterface.py', r'^def Msg\(msg\)', 'Msg() helper (ccc.py error messages)'),
    ('VIPInterface.py', r"data\['data_adapter'\]\s*=", "route() sets data['data_adapter']"),
    ('VIPInterface.py', r"data\['var_index'\]\s*=", "route() sets data['var_index']"),
    # Frontend: what ccc.js/ccc.html use from interface.html
    ('interface.html', r'function selFun\(evt,\s*sel\)', 'selFun() tab switching'),
    ('interface.html', r'function getCells\(eID,\s*sep', 'getCells(eID, sep) selection helper'),
    ('interface.html', r'function cellNupdate\(', 'cellNupdate() selection counts'),
    ('interface.html', r'function showImg\(', 'showImg() figure display'),
    ('interface.html', r'function hideShow\(', 'hideShow() "Hide Input" button'),
    ('interface.html', r'var VIPurl\b', 'VIPurl request URL'),
    ('interface.html', r'window\.figOpt\b', 'window.figOpt figure options'),
    ('interface.html', r'window\.accumulateCell\b', 'window.accumulateCell (accumulate selections)'),
    ('interface.html', r'\.differential\[', 'store.differential selection lists'),
    ('interface.html', r"class=\"cellN1\"", '.cellN1/.cellN2 count spans'),
    ('interface.html', r'\.tabcontent\s*\{', '.tabcontent CSS (tab hidden until opened)'),
    ('interface.html', r'datatables(\.min)?\.js', 'DataTables library (results table)'),
]

# Not fatal: ccc.js falls back to appending at the end if these are gone
WARN = [
    ('interface.html', r"class=\"tablinks\" onclick=\"selFun\(event, 'CLI'\)", 'CLI tab button (CCC button goes before it)'),
    ('interface.html', r'<div id="CLI" class="tabcontent">', 'CLI tab content (CCC tab goes before it)'),
]

# Our own files must exist and parse
OWN_PY = ['ccc.py', 'VIPInterface.py']
OWN_FILES = ['ccc.py', 'ccc.js', 'ccc.html']


def read(name):
    with open(os.path.join(VIP, name), encoding='utf-8') as f:
        return f.read()


def main():
    failed = 0
    for name in OWN_FILES:
        if not os.path.exists(os.path.join(VIP, name)):
            print(f'FAIL  missing {name}')
            failed += 1
    for name in OWN_PY:
        try:
            ast.parse(read(name))
        except SyntaxError as e:
            print(f'FAIL  {name} does not parse: {e}')
            failed += 1
    for name in ['VIPInterface.py', 'interface.html', 'ccc.py', 'ccc.js']:
        if re.search(r'^(<<<<<<<|>>>>>>>) ', read(name), re.M):
            print(f'FAIL  {name} still has merge conflict markers')
            failed += 1

    for level, checks in [('FAIL', REQUIRED), ('WARN', WARN)]:
        for name, pattern, what in checks:
            if re.search(pattern, read(name), re.M):
                print(f'ok    {what}')
            else:
                print(f'{level}  {what}  [{name}: /{pattern}/]')
                failed += level == 'FAIL'

    # ccc.js reads these cellxgene store fields; the cellxgene version is
    # pinned in config.sh, so this only changes if that pin changes
    print('\nAlso check by hand if config.sh changed the cellxgene version: ccc.js uses '
          'store.annoMatrix (schema, fetch, nObs), store.obsCrossfilter.allSelectedLabels(), '
          'store.config.displayNames and the "store current cell selection as differential set N" action.')
    print(f'\n{"FAILED: " + str(failed) + " problem(s)" if failed else "All required checks passed."}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
