"""Build ClaimShield palette from sampled Acentra colours; print ramps, contrast table, CVD checks. Outputs palette.json."""
import json, itertools, sys
sys.path.insert(0,'/workspace/claimshield-review/scripts')
from colorlib import *

# ---------- ramps ----------
def ramp(H, steps, pins):
    out={}
    for k,(L,C) in steps.items():
        out[k]=pins.get(k) or from_oklch(L,C,H)
    return out
GREEN = ramp(147, {50:(.975,.025),100:(.95,.05),200:(.905,.09),300:(.845,.13),400:(.775,.175),500:None and (0,0) or (.695,.216),
                   600:(.606,.16),700:(.548,.144),800:(.455,.115),900:(.37,.09),950:(.285,.065)},
             {500:'#2bbc2b',600:'#209b47',700:'#1c873e'})
# neutrals: teal-tinted, hue 200 (between Acentra ink #042126 H211 and Acentra teals #11615b/#e4f3f2 H187-192)
NH=200
NEUTRAL={0:'#ffffff'}
for k,(L,C) in {25:(.985,.003),50:(.97,.005),100:(.947,.007),150:(.92,.009),200:(.885,.011),300:(.82,.013),400:(.70,.016),
                500:(.60,.018),600:(.525,.02),700:(.455,.022),800:(.37,.026),900:(.30,.03)}.items():
    NEUTRAL[k]=from_oklch(L,C,NH)
NEUTRAL[950]='#042126'  # Acentra ink (body text, logo wordmark)
# risk ramp (low slate-blue, medium amber, high orange, critical deep red)
RISK={
 'low':     {'bg':from_oklch(.965,.012,250),'border':from_oklch(.62,.05,250),'fg':from_oklch(.40,.06,252),'solid':from_oklch(.56,.06,250)},
 'medium':  {'bg':from_oklch(.965,.035,85), 'border':from_oklch(.63,.12,75), 'fg':from_oklch(.43,.09,65), 'solid':from_oklch(.65,.14,75)},
 'high':    {'bg':from_oklch(.955,.03,55),  'border':from_oklch(.56,.15,48), 'fg':from_oklch(.44,.13,45), 'solid':from_oklch(.54,.16,47)},
 'critical':{'bg':from_oklch(.95,.025,22),  'border':from_oklch(.46,.16,25), 'fg':from_oklch(.38,.14,25), 'solid':from_oklch(.42,.16,25)},
}
HARM={'bg':from_oklch(.955,.025,345),'border':from_oklch(.50,.15,345),'fg':from_oklch(.40,.13,345),'solid':from_oklch(.47,.16,345)}
STATUS={
 'info':   {'bg':from_oklch(.965,.015,245),'border':from_oklch(.58,.08,250),'fg':'#15497e','solid':'#15497e'},   # fg = Acentra link blue
 'success':{'bg':GREEN[50],'border':GREEN[600],'fg':GREEN[800],'solid':GREEN[700]},
 'warning':{'bg':RISK['medium']['bg'],'border':RISK['medium']['border'],'fg':RISK['medium']['fg'],'solid':RISK['medium']['solid']},
 'danger': {'bg':from_oklch(.955,.02,25),'border':from_oklch(.52,.16,27),'fg':from_oklch(.45,.15,27),'solid':from_oklch(.50,.17,27)},
}
# categorical chart palette: Okabe-Ito derived, harmonised to brand, darkened where needed for >=3:1 on white
CHART=['#209b47','#0072b2','#1d3b70','#005f68','#8c5a2b','#2f8fd0','#b05a8a','#b07a00']
if len(sys.argv)>1 and sys.argv[1]=='tune': pass

SEM={
 'bg':NEUTRAL[50],'surface':NEUTRAL[0],'surface-raised':NEUTRAL[0],'surface-sunken':NEUTRAL[100],
 'border':NEUTRAL[200],'border-strong':NEUTRAL[500],
 'text':NEUTRAL[950],'text-muted':NEUTRAL[700],'text-subtle':NEUTRAL[600],'text-on-brand':NEUTRAL[950],
 'brand':GREEN[500],'brand-hover':GREEN[400],'brand-active':GREEN[600],'brand-subtle':GREEN[50],'brand-strong':GREEN[700],
 'focus':GREEN[700],'link':'#15497e','brand-text':GREEN[800],'selected-bar':GREEN[600],
 'chart-focus':'#15497e','chart-comparison':NEUTRAL[400],'chart-comparison-line':NEUTRAL[500],'chart-axis':NEUTRAL[500],'chart-grid':NEUTRAL[150],'chart-baseline':NEUTRAL[700],
}
DARK={'bg':'#042126','surface':from_oklch(.27,.03,208),'surface-raised':from_oklch(.31,.03,208),'surface-sunken':from_oklch(.20,.03,210),
 'border':from_oklch(.36,.025,205),'border-strong':from_oklch(.58,.02,200),'text':NEUTRAL[100],'text-muted':NEUTRAL[300],'text-subtle':from_oklch(.74,.016,200),
 'brand':GREEN[500],'text-on-brand':'#042126','focus':GREEN[400],'link':from_oklch(.80,.08,250),'brand-subtle':from_oklch(.32,.05,150),'brand-text':GREEN[300]}
DARK_RISK={k:{'bg':from_oklch(.30,.04,h),'fg':from_oklch(.88,.07,h),'border':from_oklch(.68,.11,h)} for k,h in (('low',250),('medium',75),('high',50),('critical',25),('harm',345))}
def row(name,fg,bg,need):
    c=contrast(fg,bg); return (name,fg,bg,round(c,2),need,'PASS' if c>=need else 'FAIL')
rows=[]
for t in ('text','text-muted','text-subtle','link','brand-strong'):
    for b in ('bg','surface','surface-sunken'):
        rows.append(row(f'{t} on {b}',SEM[t],SEM[b],4.5))
rows.append(row('text-on-brand on brand',SEM['text-on-brand'],SEM['brand'],4.5))
rows.append(row('text-on-brand on brand-hover',SEM['text-on-brand'],SEM['brand-hover'],4.5))
rows.append(row('text-on-brand on brand-active',SEM['text-on-brand'],SEM['brand-active'],4.5))
rows.append(row('text on brand-subtle (selected row)',SEM['text'],SEM['brand-subtle'],4.5))
rows.append(row('text-muted on brand-subtle',SEM['text-muted'],SEM['brand-subtle'],4.5))
for b in ('bg','surface','surface-sunken'):
    rows.append(row(f'brand-text on {b}',SEM['brand-text'],SEM[b],4.5))
rows.append(row('brand-text on brand-subtle',SEM['brand-text'],SEM['brand-subtle'],4.5))
rows.append(row('selected-bar on brand-subtle',SEM['selected-bar'],SEM['brand-subtle'],3))
rows.append(row('selected-bar (active nav underline) on surface',SEM['selected-bar'],SEM['surface'],3))
rows.append(row('chart-focus on surface',SEM['chart-focus'],SEM['surface'],3))
rows.append(row('chart-axis on surface',SEM['chart-axis'],SEM['surface'],3))
rows.append(row('chart-baseline on surface',SEM['chart-baseline'],SEM['surface'],3))
rows.append(row('chart-comparison-line on surface',SEM['chart-comparison-line'],SEM['surface'],3))
rows.append(row('chart-comparison (bar fill, labelled; context only) on surface',SEM['chart-comparison'],SEM['surface'],1.0))
rows.append(row('chart-grid on surface (decorative)',SEM['chart-grid'],SEM['surface'],1.0))
for b in ('bg','surface','surface-sunken'):
    rows.append(row(f'border-strong on {b}',SEM['border-strong'],SEM[b],3))
    rows.append(row(f'focus ring on {b}',SEM['focus'],SEM[b],3))
rows.append(row('brand bar/selected bar (brand) on surface',SEM['brand'],SEM['surface'],3))
rows.append(row('selected-row bar (brand-strong) on brand-subtle',SEM['brand-strong'],SEM['brand-subtle'],3))
rows.append(row('border (decorative divider) on surface',SEM['border'],SEM['surface'],1.0))
for k,v in list(RISK.items())+[('harm',HARM)]+list(STATUS.items()):
    rows.append(row(f'{k}-fg on {k}-bg',v['fg'],v['bg'],4.5))
    rows.append(row(f'{k}-fg on surface',v['fg'],SEM['surface'],4.5))
    rows.append(row(f'{k}-border on {k}-bg',v['border'],v['bg'],3))
    rows.append(row(f'{k}-border on surface',v['border'],SEM['surface'],3))
    rows.append(row(f'{k}-solid on surface',v['solid'],SEM['surface'],3))
for i,c in enumerate(CHART,1):
    rows.append(row(f'chart-{i} on surface',c,SEM['surface'],3))
drows=[]
for t in ('text','text-muted','text-subtle','link','brand-text'):
    for b in ('bg','surface','surface-sunken','surface-raised'):
        drows.append(row(f'[dark] {t} on {b}',DARK[t],DARK[b],4.5))
drows.append(row('[dark] text-on-brand on brand',DARK['text-on-brand'],DARK['brand'],4.5))
drows.append(row('[dark] text on brand-subtle',DARK['text'],DARK['brand-subtle'],4.5))
for b in ('bg','surface'):
    drows.append(row(f'[dark] focus on {b}',DARK['focus'],DARK[b],3)); drows.append(row(f'[dark] border-strong on {b}',DARK['border-strong'],DARK[b],3))
for k,v in DARK_RISK.items():
    drows.append(row(f'[dark] {k}-fg on {k}-bg',v['fg'],v['bg'],4.5)); drows.append(row(f'[dark] {k}-border on {k}-bg',v['border'],v['bg'],3)); drows.append(row(f'[dark] {k}-border on surface',v['border'],DARK['surface'],3))
rows+=drows
fails=[r for r in rows if r[5]=='FAIL']
# CVD
def mind(cols,names):
    res={}
    for kind in ('normal','deuteranopia','protanopia','tritanopia'):
        sim=[c if kind=='normal' else simulate(c,kind) for c in cols]
        pairs=[(de2000(sim[i],sim[j]),names[i],names[j]) for i,j in itertools.combinations(range(len(cols)),2)]
        res[kind]=sorted(pairs)[:3]
    return res
chart_cvd=mind(CHART,[f'chart-{i}' for i in range(1,9)])
riskcols=[RISK[k]['solid'] for k in ('low','medium','high','critical')]+[HARM['solid']]
risk_cvd=mind(riskcols,['low','medium','high','critical','harm'])
out={'green':GREEN,'neutral':NEUTRAL,'risk':RISK,'harm':HARM,'status':STATUS,'chart':CHART,'semantic':SEM,'contrast':rows,'dark':DARK,'dark_risk':DARK_RISK,'chart_cvd':chart_cvd,'risk_cvd':risk_cvd,
     'risk_lightness':{k:round(oklch(RISK[k]['solid'])[0],3) for k in RISK}}
json.dump(out,open('/workspace/claimshield-review/scripts/palette.json','w'),indent=1)
if __name__=='__main__':
    print('DARK',DARK); print('DARK_RISK',DARK_RISK); print('GREEN',GREEN); print('NEUTRAL',NEUTRAL); print('RISK',json.dumps(RISK)); print('HARM',HARM); print('STATUS',json.dumps(STATUS))
    for r in rows: print('%-48s %s %s %6.2f  need %.1f %s'%r)
    print('FAILS',len(fails))
    for k,v in chart_cvd.items(): print('chart',k,[(round(d,1),a,b) for d,a,b in v])
    for k,v in risk_cvd.items(): print('risk',k,[(round(d,1),a,b) for d,a,b in v])
    print(out['risk_lightness'])
