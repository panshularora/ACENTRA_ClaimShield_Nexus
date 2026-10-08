import re, sys
sys.path.insert(0,'/workspace/claimshield-review/scripts')
from colorlib import simulate, contrast
css=open('/workspace/claimshield-review/tokens.css').read()
nc=re.sub(r'/\*.*?\*/','',css,flags=re.S)
root=dict(re.findall(r'(--[\w-]+)\s*:\s*([^;]+);', re.search(r':root\s*\{(.*?)\n\}',nc,re.S).group(1)))
def res(v):
    m=re.fullmatch(r'var\((--[\w-]+)\)',v.strip()); return res(root[m.group(1)]) if m else v.strip()
def sw(var,label=None):
    hx=res(root[var]); return f'<div class="sw"><i style="background:var({var})"></i><b>{label or var}</b><code>{hx}</code></div>'
green=''.join(sw(f'--green-{k}') for k in (50,100,200,300,400,500,600,700,800,900,950))
neutral=''.join(sw(f'--neutral-{k}') for k in (0,25,50,100,150,200,300,400,500,600,700,800,900,950))
risk=''
for lv,name in (('low','Low'),('medium','Medium'),('high','High'),('critical','Critical')):
    g=res(root[f'--risk-{lv}-glyph']).strip('"')
    risk+=f'<span class="badge" style="background:var(--risk-{lv}-bg);color:var(--risk-{lv}-fg);border-color:var(--risk-{lv}-border)"><span aria-hidden="true">{g}</span> {name}</span>'
harm='<span class="badge" style="background:var(--harm-bg);color:var(--harm-fg);border-color:var(--harm-border)"><span aria-hidden="true">✚</span> Harm 4</span>'
rows=''
for kind in ('normal','deuteranopia','protanopia','tritanopia'):
    cells=''.join(f'<i style="background:{res(root[f"--chart-{i}"]) if kind=="normal" else simulate(res(root[f"--chart-{i}"]),kind)}" title="chart-{i}"></i>' for i in range(1,9))
    rcells=''.join(f'<i style="background:{res(root[f"--risk-{lv}-solid"]) if kind=="normal" else simulate(res(root[f"--risk-{lv}-solid"]),kind)}"></i>' for lv in ('low','medium','high','critical'))+f'<i style="background:{res(root["--harm-solid"]) if kind=="normal" else simulate(res(root["--harm-solid"]),kind)}"></i>'
    rows+=f'<tr><th>{kind}</th><td><div class="strip">{cells}</div></td><td><div class="strip">{rcells}</div></td></tr>'
html=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>ClaimShield Nexus palette</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../tokens.css">
<style>
body{{margin:0;background:var(--color-bg);color:var(--color-text);font:var(--type-body);}}
.bar{{height:3px;background:var(--color-brand-bar)}}
header.top{{height:var(--shell-topbar-height);background:var(--color-surface);border-bottom:1px solid var(--color-border);display:flex;align-items:center;gap:var(--space-6);padding:0 var(--space-6)}}
header.top strong{{font:var(--type-h4)}} header.top nav a{{font:var(--type-label);color:var(--color-text-muted);text-decoration:none;padding:18px 2px 15px;border-bottom:3px solid transparent;margin-right:var(--space-4)}}
header.top nav a.on{{color:var(--color-text);border-bottom-color:var(--color-brand-strong)}}
main{{max-width:1180px;margin:0 auto;padding:var(--space-6);display:grid;gap:var(--space-4)}}
.card{{background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius-md);padding:var(--card-padding)}}
.card h2{{font:var(--type-h4);margin:0 0 var(--space-3)}} .ov{{font:var(--type-overline);letter-spacing:var(--letter-spacing-wide);text-transform:uppercase;color:var(--color-text-muted);margin:0 0 2px}}
.ramp{{display:grid;grid-template-columns:repeat(14,1fr);gap:6px}} .ramp.g{{grid-template-columns:repeat(11,1fr)}}
.sw i{{display:block;height:40px;border-radius:var(--radius-sm);border:1px solid var(--color-border)}} .sw b{{display:block;font:var(--type-caption);margin-top:4px}} .sw code{{font:var(--type-caption);font-family:var(--font-mono);color:var(--color-text-muted)}}
.badges{{display:flex;gap:var(--space-2);flex-wrap:wrap;align-items:center}}
.badge{{display:inline-flex;gap:6px;align-items:center;height:22px;padding:0 8px;border:1px solid;border-radius:var(--radius-sm);font:var(--type-label);font-size:var(--font-size-12)}}
.btn{{height:var(--control-height);padding:0 var(--space-4);border-radius:var(--radius-sm);font:var(--type-label);border:1px solid var(--color-border-strong);background:var(--color-surface);color:var(--color-text)}}
.btn.primary{{background:var(--color-brand);border-color:var(--color-brand);color:var(--color-text-on-brand)}} .btn.ghost{{border-color:transparent;background:transparent}}
.btn.danger{{background:var(--color-surface);border-color:var(--color-danger-border);color:var(--color-danger-fg)}} .btn.focus{{box-shadow:var(--focus-ring)}}
table.cvd{{border-collapse:collapse}} table.cvd th{{text-align:left;font:var(--type-label);color:var(--color-text-muted);padding:4px 12px 4px 0}} .strip{{display:flex;gap:3px;margin-right:24px}} .strip i{{width:34px;height:22px;border-radius:2px}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:var(--space-4)}}
.kpi .v{{font:var(--type-numeric-lg);font-variant-numeric:tabular-nums}} .kpi .l{{font:var(--type-label);color:var(--color-text-muted)}} .kpi .d{{font:var(--type-body-sm);color:var(--color-text-muted)}}
svg text{{font-family:var(--font-sans);font-size:11px;fill:var(--color-text-muted)}}
.legend{{display:flex;gap:var(--space-4);flex-wrap:wrap;font:var(--type-caption);color:var(--color-text-muted)}} .legend span{{display:inline-flex;align-items:center;gap:6px}}
</style></head><body>
<div class="bar"></div><header class="top"><strong>ClaimShield Nexus</strong><nav><a class="on" href="#">Queue</a><a href="#">Cases</a><a href="#">Precedents</a><a href="#">Audit</a></nav></header>
<main>
<section class="card"><p class="ov">Primitives</p><h2>Green: built around Acentra #2bbc2b / #209b47 / #1c873e</h2><div class="ramp g">{green}</div></section>
<section class="card"><h2>Neutrals: teal-tinted, ending in Acentra ink #042126</h2><div class="ramp">{neutral}</div></section>
<section class="grid2">
<div class="card"><p class="ov">Risk is never colour alone</p><h2>Risk scale + patient-harm flag (separate axis)</h2><div class="badges">{risk}<span style="width:16px"></span>{harm}</div>
<p style="font:var(--type-body-sm);color:var(--color-text-muted)">Glyph shape changes per level (○ ◐ ● ◆). Harm uses its own hue (plum) and its own glyph (✚).</p></div>
<div class="card"><h2>Buttons and focus</h2><div class="badges"><button class="btn primary">Take case</button><button class="btn">Export</button><button class="btn ghost">Cancel</button><button class="btn danger">Close as unfounded</button><button class="btn primary focus">Focused</button></div></div>
</section>
<section class="card"><h2>Categorical chart palette + risk ramp under colour-vision simulation (Machado 2009)</h2>
<table class="cvd"><tr><th></th><th>--chart-1 … --chart-8</th><th>risk low → critical, harm</th></tr>{rows}</table></section>
<section class="grid2">
<div class="card kpi"><p class="ov">KPI tile</p><div class="l">Flagged dollars in queue</div><div class="v">$1.24M</div><div class="d">▲ 8.2% vs prior run</div></div>
<div class="card"><h2>Network graph: node shapes and edges</h2>
<svg viewBox="0 0 520 120" width="100%" role="img" aria-label="graph legend">
 <g transform="translate(34,44)"><circle r="20" fill="none" stroke="var(--risk-high-solid)" stroke-width="3"/><circle r="15" fill="var(--graph-subject-fill)"/><text y="44" text-anchor="middle">Subject</text></g>
 <g transform="translate(100,44)"><circle r="12" fill="var(--graph-node-provider-fill)" stroke="var(--graph-node-provider-stroke)" stroke-width="1.5"/><text y="44" text-anchor="middle">Provider</text></g>
 <g transform="translate(160,44)"><rect x="-10" y="-10" width="20" height="20" rx="4" fill="var(--graph-node-owner-fill)" stroke="var(--graph-node-owner-stroke)" stroke-width="1.5"/><text y="44" text-anchor="middle">Owner</text></g>
 <g transform="translate(220,44)"><rect x="-14" y="-9" width="28" height="18" rx="2" fill="var(--graph-node-facility-fill)" stroke="var(--graph-node-facility-stroke)" stroke-width="1.5"/><text y="44" text-anchor="middle">Facility</text></g>
 <g transform="translate(280,44)"><path d="M0-12L12 0 0 12-12 0Z" fill="var(--graph-node-address-fill)" stroke="var(--graph-node-address-stroke)" stroke-width="1.5"/><text y="44" text-anchor="middle">Address</text></g>
 <g transform="translate(336,44)"><circle r="7" fill="var(--graph-node-phone-fill)" stroke="var(--graph-node-phone-stroke)" stroke-width="1.5"/><text y="44" text-anchor="middle">Phone</text></g>
 <g transform="translate(392,44)"><path d="M-11 0L-5.5-9.5 5.5-9.5 11 0 5.5 9.5-5.5 9.5Z" fill="var(--graph-node-bank-fill)" stroke="var(--graph-node-bank-stroke)" stroke-width="1.5"/><text y="44" text-anchor="middle">Bank / TIN</text></g>
 <g transform="translate(452,44)"><path d="M0-9L9 7-9 7Z" fill="var(--graph-node-member-fill)" stroke="var(--graph-node-member-stroke)" stroke-width="1.5"/><text y="44" text-anchor="middle">Member</text></g>
 <g transform="translate(500,44)"><circle r="10" fill="var(--graph-node-provider-fill)" stroke="var(--graph-node-provider-stroke)" stroke-width="1.5"/><circle cx="8" cy="-8" r="4.5" fill="var(--harm-solid)" stroke="var(--graph-bg)" stroke-width="1.5"/><text y="44" text-anchor="middle">Harm</text></g>
</svg>
<div class="legend"><span><svg width="28" height="8"><line x1="0" y1="4" x2="28" y2="4" stroke="var(--graph-edge-claim)" stroke-width="1.5"/></svg>Billed / rendered</span>
<span><svg width="28" height="8"><line x1="0" y1="4" x2="28" y2="4" stroke="var(--graph-edge-shared)" stroke-width="1.5"/></svg>Shared address / TIN / phone</span>
<span><svg width="32" height="10"><line x1="0" y1="5" x2="24" y2="5" stroke="var(--graph-edge-ownership)" stroke-width="2"/><path d="M24 1L31 5 24 9Z" fill="var(--graph-edge-ownership)"/></svg>Owns</span>
<span><svg width="32" height="10"><line x1="0" y1="5" x2="24" y2="5" stroke="var(--graph-edge-referral)" stroke-width="2"/><path d="M24 1L31 5 24 9Z" fill="var(--graph-edge-referral)"/></svg>Referral</span></div></div>
</section>
</main></body></html>'''
open('/workspace/claimshield-review/brand-evidence/palette.html','w').write(html)
print('ok')
