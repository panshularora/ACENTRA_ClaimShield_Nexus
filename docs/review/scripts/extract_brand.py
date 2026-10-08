"""Extract colours / fonts / sizes from downloaded acentra.com CSS + HTML inline styles."""
import re, glob, os, csv, json
from collections import Counter, defaultdict
BE='/workspace/claimshield-review/brand-evidence'
VENDOR=('font-awesome','fancybox','tiny-slider','slick','splide','google_fonts')
urls={}
for u in open(f'{BE}/css_urls.txt').read().split():
    n=re.sub(r'[/?&=]','_',re.sub(r'https?://','',u))[:150]; urls[n]=u
PAGES={'home':'https://acentra.com/','about-us':'https://acentra.com/about-us','solutions':'https://acentra.com/solutions/','solutions_claims-and-encounters':'https://acentra.com/solutions/claims-and-encounters'}
def norm(c):
    c=c.strip().lower()
    if c.startswith('#'):
        h=c[1:]
        if len(h) in (3,4): h=''.join(ch*2 for ch in h[:3]) + (h[3]*2 if len(h)==4 else '')
        if len(h)==8:
            a=int(h[6:],16)/255; return '#'+h[:6], round(a,2)
        return '#'+h[:6], 1.0
    m=re.match(r'rgba?\(([^)]+)\)',c)
    if m:
        p=[x.strip() for x in re.split(r'[ ,/]+',m.group(1)) if x.strip()]
        try:
            r,g,b=[int(float(x.rstrip('%'))) for x in p[:3]]; a=float(p[3]) if len(p)>3 else 1.0
            return '#%02x%02x%02x'%(r,g,b), round(a,2)
        except: return None
    return None
NAMED={'white':'#ffffff','black':'#000000'}
colre=re.compile(r'#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3,4}\b|rgba?\([^)]*\)|\b(?:white|black)\b')
stats=defaultdict(lambda:{'count':0,'where':Counter(),'src':Counter(),'alphas':Counter()})
fonts=Counter(); fsizes=Counter(); lh=Counter(); radius=Counter(); maxw=Counter(); weights=Counter(); varsdef={}
headings=defaultdict(Counter); body=[]
def walk(css, src, vendor):
    css=re.sub(r'/\*.*?\*/','',css,flags=re.S)
    for m in re.finditer(r'([^{}]+)\{([^{}]*)\}',css):
        sel=' '.join(m.group(1).split())[:90]; decl=m.group(2)
        for d in decl.split(';'):
            if ':' not in d: continue
            prop,val=d.split(':',1); prop=prop.strip().lower(); val=val.strip()
            if prop.startswith('--'): varsdef[prop]=val
            if vendor: continue
            if prop=='font-family': fonts[val.replace('!important','').strip()]+=1
            if prop=='font-size': fsizes[val]+=1
            if prop=='line-height': lh[val]+=1
            if prop=='font-weight': weights[val]+=1
            if 'radius' in prop: radius[val]+=1
            if prop=='max-width' and re.search(r'container|wrapper|row-fluid|page-center|content-wrapper|dnd-section',sel): maxw[f'{val} ({sel[:50]})']+=1
            for h in ('h1','h2','h3','h4','h5','h6'):
                if re.search(rf'(^|[ ,]){h}($|[ ,.:])',sel) and prop in('font-size','font-weight','line-height'): headings[h][f'{prop}:{val}']+=1
            if re.fullmatch(r'(html|body)',sel.strip()) and prop in ('font-size','line-height','font-family','color','font-weight'): body.append((src,prop,val))
            for c in colre.findall(val):
                n=norm(NAMED.get(c.lower(),c))
                if not n: continue
                hx,a=n; s=stats[hx]; s['count']+=1; s['where'][f'{sel} {{{prop}}}']+=1; s['src'][src]+=1; s['alphas'][a]+=1
for f in sorted(glob.glob(f'{BE}/css/*.css')):
    b=os.path.basename(f); vendor=any(v in b for v in VENDOR)
    if b.startswith('inline_'): src=PAGES[b[7:-4]]+' (inline <style>)'
    else: src=urls.get(b,b)
    walk(open(f,encoding='utf8',errors='ignore').read(),src,vendor)
# inline style="" attributes in HTML
for p,u in PAGES.items():
    h=open(f'{BE}/{p}.html',encoding='utf8',errors='ignore').read()
    for m in re.finditer(r'<(\w+)[^>]*?style="([^"]*)"',h):
        walk(f'{m.group(1)}[style]{{{m.group(2)}}}',u+' (style attr)',False)
# logo pixel colours (from earlier pixel count)
logo={'#2bbc2b':('logo fill (dominant, logo-retina.png / footer-logo.svg embedded PNG / Symbol-retina.png)','https://acentra.com/hubfs/footer-logo.svg; logo-retina.png'),
      '#042126':('logo wordmark text fill (logo-retina.png, footer-logo.svg embedded PNG)','https://acentra.com/hubfs/footer-logo.svg; logo-retina.png'),
      '#b4ea54':('symbol gradient light end (Symbol-retina.png)','https://acentra.com/hubfs/AcentraHealth_December2024/images/Symbol-retina.png'),
      '#042125':('home hero background (dominant pixel of hero-bg.jpg; = #042126 ink within JPEG rounding)','https://acentra.com/hubfs/AcentraHealth_December2024/images/hero-bg.jpg'),
      '#1e373c':('home hero large "A" watermark shape (2nd pixel colour of hero-bg.jpg)','https://acentra.com/hubfs/AcentraHealth_December2024/images/hero-bg.jpg'),
      '#028202':('top announcement bar "Acentra Health Welcomes FEI Systems" (HubSpot CTA iframe, pixel-sampled from headless-Chrome render; not in site CSS, third-party embed)','https://acentra.com/ (rendered screenshot acentra_home.png)')}
rows=[]
for hx,s in sorted(stats.items(),key=lambda kv:-kv[1]['count']):
    r,g,b=int(hx[1:3],16),int(hx[3:5],16),int(hx[5:7],16)
    where='; '.join(f'{w} x{n}' for w,n in s['where'].most_common(6))
    al=dict(s['alphas']); 
    if list(al)!=[1.0]: where=f'[alphas {al}] '+where
    if hx in logo: where=logo[hx][0]+' | CSS: '+where
    rows.append([hx,f'rgb({r},{g},{b})',s['count'],where,' | '.join(f'{k} x{v}' for k,v in s['src'].most_common(4))])
for hx,(w,u) in logo.items():
    if hx not in stats:
        r,g,b=int(hx[1:3],16),int(hx[3:5],16),int(hx[5:7],16); rows.append([hx,f'rgb({r},{g},{b})',0,w+' (pixel-sampled, not in CSS)',u])
with open(f'{BE}/colors_sampled.csv','w',newline='') as fh:
    w=csv.writer(fh); w.writerow(['hex','rgb','count','where_used','source_url']); w.writerows(rows)
out={'fonts':fonts.most_common(25),'font_sizes':fsizes.most_common(30),'line_heights':lh.most_common(20),'weights':weights.most_common(),
 'radius':radius.most_common(20),'max_width':maxw.most_common(15),'headings':{k:v.most_common(8) for k,v in headings.items()},'body':body[:30],
 'css_vars':{k:v for k,v in varsdef.items() if not k.startswith('--fa')}}
json.dump(out,open(f'{BE}/typography_spacing_sampled.json','w'),indent=1)
print(len(rows),'colours')
for r in rows[:45]: print(r[0],r[2],r[3][:170])
print(json.dumps(out,indent=0)[:6000])
