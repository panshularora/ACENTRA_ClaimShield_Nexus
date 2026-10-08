import itertools, sys
from colorlib import *
KINDS=('normal','deuteranopia','protanopia','tritanopia')
def sims(c): return {k:(c if k=='normal' else simulate(c,k)) for k in KINDS}
# risk tuning
for hL,cL in [(.56,.42),(.54,.42),(.53,.40),(.55,.43)]:
    med=from_oklch(.65,.14,75); hi=from_oklch(hL,.16,47); cr=from_oklch(cL,.16,25)
    S=[sims(x) for x in (med,hi,cr)]
    print('risk',hL,cL,med,hi,cr,[ (k,round(de2000(S[0][k],S[1][k]),1),round(de2000(S[1][k],S[2][k]),1)) for k in KINDS], round(contrast(hi,'#ffffff'),2))
# chart palette greedy search
cands=[]
for L in (.42,.48,.54,.60):
    for H in range(0,360,10):
        for C in (.06,.10,.14,.18):
            h=from_oklch(L,C,H)
            if contrast(h,'#ffffff')>=3.0 and abs(oklch(h)[1]-C)<.02: cands.append(h)
cands=sorted(set(cands)); print(len(cands),'cands')
def mind(c,chosen):
    s=sims(c); best=999
    for o in chosen:
        so=sims(o); best=min(best,min(de2000(s[k],so[k]) for k in KINDS))
    return best
def bad(h):  # avoid violet/purple (H 280-330) per art direction
    H=oklch(h)[2]; C=oklch(h)[1]; return 275<H<335 and C>.05
fixed=['#209b47','#0072b2']
chosen=list(fixed)
while len(chosen)<8:
    best=max((c for c in cands if not bad(c) and c not in chosen), key=lambda c: mind(c,chosen))
    print('add',best, round(mind(best,chosen),1), 'L=%.2f C=%.2f H=%.0f'%oklch(best)); chosen.append(best)
print(chosen)
