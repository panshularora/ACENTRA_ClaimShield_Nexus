import csv, re
NAMES={'#042126':'Acentra Ink','#ffffff':'White','#2bbc2b':'Acentra Green (primary)','#c6c6c6':'Editor highlight gray (content artefact)','#000000':'Black (mostly as rgba shadows)',
'#acf2e5':'Mint','#209b47':'Acentra Dark Green','#b4ea54':'Lime (hover / symbol gradient)','#15497e':'Link Blue','#1c873e':'Eyebrow Green','#11615b':'Shadow Teal',
'#f2ece4':'Sand','#026780':'Teal-blue (alpha tints only)','#161616':'Near-black (shadow)','#ef6b51':'Form error coral','#333333':'Charcoal (shadow/pagination)','#e8e0d6':'Sand 2',
'#bdbdbd':'Gray rule','#e6e6e6':'Gray disabled text / rules','#f2fcff':'Alert bar pale','#999999':'Gray error text','#cdcdcd':'Search suggest border','#cccccc':'hr gray','#d0d0d0':'Disabled button gray',
'#94b4d9':'Desktop menu divider blue','#f5cd3e':'Rating star yellow','#15c0ea':'Cyan (10% overlays)','#e4f3f2':'Pale Teal','#dcdcde':'Divider gray','#767676':'Form legend gray',
'#c02b0a':'Form error red','#1c8b38':'Menu link green','#eeeeee':'Table rule gray','#467886':'Inline text teal (content)','#7a7a7a':'Shadow gray','#fff9fc':'Social icon bg',
'#ff1515':'Close-icon text-shadow red','#005f68':'Deep Teal (h2)','#495057':'Alert link gray','#12153f':'Blog panel navy','#801700':'Required-field red','#d9d9d9':'Menu divider gray',
'#d7d7d7':'404 glyph gray','#00d082':'Search hover green','#042125':'Hero Ink (image)','#1e373c':'Hero watermark teal (image)','#028202':'Announcement bar green (HubSpot CTA)'}
def short_src(s):
    out=[]
    for part in s.split(' | '):
        m=re.match(r'(\S+)(.*)',part); u,rest=m.group(1),m.group(2)
        name=u.rstrip('/').split('/')[-1] if 'hubfs' in u else u
        out.append((name+rest).strip())
    return '; '.join(out)
rows=list(csv.DictReader(open('/workspace/claimshield-review/brand-evidence/colors_sampled.csv')))
md=['| # | Hex | Swatch name | Where used on acentra.com (top selectors / element) | Source file(s) | CSS count |','|---:|---|---|---|---|---:|']
for i,r in enumerate(rows,1):
    where=re.sub(r'\[alphas [^\]]*\]\s*','',r['where_used'])
    alph=re.search(r'\[alphas ([^\]]*)\]',r['where_used'])
    parts=where.split('; ')[:3]; where='; '.join(parts).replace('|','/')
    if alph and alph.group(1)!='{1.0: %s}'%r['count']: where+=' _(alphas: '+alph.group(1).replace('{','').replace('}','')+')_'
    cnt=r['count'] if r['count']!='0' else 'pixel'
    md.append(f"| {i} | `{r['hex']}` | {NAMES.get(r['hex'],'?')} | {where[:260]} | {short_src(r['source_url'])[:140]} | {cnt} |")
open('/workspace/claimshield-review/scripts/brand_table.md','w').write('\n'.join(md)+'\n')
print(len(rows), [r['hex'] for r in rows if r['hex'] not in NAMES])
