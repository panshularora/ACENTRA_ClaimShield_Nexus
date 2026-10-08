"""Resolve tokens.css custom properties and compute WCAG contrast for every pairing the system relies on.
Writes contrast_table.md (markdown) and exits non-zero if any required pair fails."""
import re, sys
sys.path.insert(0, '/workspace/claimshield-review/scripts')
from colorlib import contrast, blend
css = open('/workspace/claimshield-review/tokens.css').read()
css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
def block(sel):
    m = re.search(re.escape(sel) + r'\s*\{(.*?)\n\}', css, re.S); return dict(re.findall(r'(--[\w-]+)\s*:\s*([^;]+);', m.group(1)))
ROOT = block(':root'); DARK = {**ROOT, **block('[data-theme="dark"]')}
def res(v, T, depth=0):
    v = v.strip()
    m = re.fullmatch(r'var\((--[\w-]+)\)', v)
    return res(T[m.group(1)], T, depth + 1) if m else v
L = lambda k: res(ROOT[k], ROOT); D = lambda k: res(DARK[k], DARK)
rows = []
def add(group, name, fg, bg, need, theme='light'):
    G = L if theme == 'light' else D
    f, b = G(fg) if fg.startswith('--') else fg, G(bg) if bg.startswith('--') else bg
    c = contrast(f, b); rows.append((theme, group, name, f, b, c, need, 'PASS' if c >= need - 1e-9 else 'FAIL'))
for th in ('light', 'dark'):
    for t in ('--color-text', '--color-text-muted', '--color-text-subtle', '--color-link', '--color-brand-text'):
        for b in ('--color-bg', '--color-surface', '--color-surface-sunken', '--color-surface-hover'):
            add('Text (≥4.5)', f'{t[8:]} on {b[8:]}', t, b, 4.5, th)
    add('Text (≥4.5)', 'text on brand-subtle (selected row)', '--color-text', '--color-brand-subtle', 4.5, th)
    add('Text (≥4.5)', 'text-muted on brand-subtle', '--color-text-muted', '--color-brand-subtle', 4.5, th)
    add('Brand (≥4.5)', 'text-on-brand on brand (primary button)', '--color-text-on-brand', '--color-brand', 4.5, th)
    if th == 'light':
        add('Brand (≥4.5)', 'text-on-brand on brand-hover', '--color-text-on-brand', '--color-brand-hover', 4.5)
        add('Brand (≥4.5)', 'text-on-brand on brand-active', '--color-text-on-brand', '--color-brand-active', 4.5)
        add('Brand (≥4.5)', 'white glyph on graph subject fill', '--graph-subject-glyph', '--graph-subject-fill', 4.5)
    for b in ('--color-bg', '--color-surface', '--color-surface-sunken'):
        add('UI state (≥3)', f'focus ring on {b[8:]}', '--color-focus', b, 3, th)
        add('UI state (≥3)', f'border-strong on {b[8:]}', '--color-border-strong', b, 3, th)
    add('UI state (≥3)', 'brand-strong (active nav underline) on surface', '--color-brand-strong', '--color-surface', 3, th)
    add('UI state (≥3)', 'brand-strong (selected-row bar) on brand-subtle', '--color-brand-strong', '--color-brand-subtle', 3, th)
    for lv in ('low', 'medium', 'high', 'critical'):
        add('Risk badge', f'risk-{lv}-fg on risk-{lv}-bg (≥4.5)', f'--risk-{lv}-fg', f'--risk-{lv}-bg', 4.5, th)
        add('Risk badge', f'risk-{lv}-border on risk-{lv}-bg (≥3)', f'--risk-{lv}-border', f'--risk-{lv}-bg', 3, th)
        add('Risk badge', f'risk-{lv}-border on surface (≥3)', f'--risk-{lv}-border', '--color-surface', 3, th)
        add('Risk badge', f'risk-{lv}-solid on surface, graph ring (≥3)', f'--risk-{lv}-solid', '--color-surface', 3, th)
    add('Harm', 'harm-fg on harm-bg (≥4.5)', '--harm-fg', '--harm-bg', 4.5, th)
    add('Harm', 'harm-border on harm-bg (≥3)', '--harm-border', '--harm-bg', 3, th)
    add('Harm', 'harm-solid on surface (≥3)', '--harm-solid', '--color-surface', 3, th)
    add('Chart', 'chart-focus on surface (≥3)', '--chart-focus', '--color-surface', 3, th)
    add('Chart', 'chart-axis on surface (≥3)', '--chart-axis', '--color-surface', 3, th)
    add('Chart', 'chart-baseline on surface (≥3)', '--chart-baseline', '--color-surface', 3, th)
    add('Chart', 'chart-comparison-line on surface (≥3)', '--chart-comparison-line', '--color-surface', 3, th)
    add('Chart', 'chart-label (tick text) on surface (≥4.5)', '--chart-label', '--color-surface', 4.5, th)
for s in ('info', 'success', 'warning', 'danger'):
    add('Status', f'{s}-fg on {s}-bg (≥4.5)', f'--color-{s}-fg', f'--color-{s}-bg', 4.5)
    add('Status', f'{s}-border on {s}-bg (≥3)', f'--color-{s}-border', f'--color-{s}-bg', 3)
for i in range(1, 9):
    add('Chart', f'chart-{i} on surface (≥3)', f'--chart-{i}', '--color-surface', 3)
for k in ('provider', 'owner', 'facility', 'address', 'phone', 'bank', 'member'):
    add('Graph', f'{k} node stroke on its fill (≥3)', f'--graph-node-{k}-stroke', f'--graph-node-{k}-fill', 3)
    add('Graph', f'{k} node stroke on canvas (≥3)', f'--graph-node-{k}-stroke', '--graph-bg', 3)
for e in ('shared', 'ownership', 'referral'):
    add('Graph', f'edge {e} on canvas (≥3)', f'--graph-edge-{e}', '--graph-bg', 3)
# Informational (no requirement; decorative or context-only)
info = []
def note(name, fg, bg, why):
    f, b = L(fg), L(bg); info.append((name, f, b, contrast(f, b), why))
note('brand (#2bbc2b) on surface', '--color-brand', '--color-surface', 'Decorative brand bar and button fill only; never text, never a state indicator')
note('border on surface', '--color-border', '--color-surface', 'Decorative 1px card/row divider')
note('chart-grid on surface', '--chart-grid', '--color-surface', 'Gridlines are deliberately quiet')
note('chart-comparison on surface', '--chart-comparison', '--color-surface', 'Context bars; always carry a direct value label')
note('graph claim edge on canvas', '--graph-edge-claim', '--graph-bg', 'Most numerous edges, kept quiet; type is also in the hover label')
# dimmed graph elements at 15%
dim = blend(L('--graph-node-provider-stroke'), L('--graph-bg'), float(L('--graph-dim-opacity')))
info.append(('dimmed node stroke (15% opacity)', dim, L('--graph-bg'), contrast(dim, L('--graph-bg')), 'Intentionally faded context outside the 2-hop focus'))
out = ['| Theme | Group | Pair | FG | BG | Ratio | Needs | Result |', '|---|---|---|---|---|---:|---:|---|']
for r in rows: out.append('| %s | %s | %s | `%s` | `%s` | %.2f | %.1f | %s |' % r)
out += ['', '**Informational (no requirement, by design):**', '', '| Pair | FG | BG | Ratio | Why it is allowed |', '|---|---|---|---:|---|']
for r in info: out.append('| %s | `%s` | `%s` | %.2f | %s |' % r)
open('/workspace/claimshield-review/scripts/contrast_table.md', 'w').write('\n'.join(out) + '\n')
fails = [r for r in rows if r[7] == 'FAIL']
print(len(rows), 'pairs;', len(fails), 'fail')
for r in fails: print('FAIL', r)
sys.exit(1 if fails else 0)
