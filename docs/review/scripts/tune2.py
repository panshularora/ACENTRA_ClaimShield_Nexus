import itertools
from colorlib import *
KINDS=('normal','deuteranopia','protanopia','tritanopia')
pool={'green':'#209b47','blue':'#0072b2','amber':'#c47e00','verm':'#c45200','sky':'#3f8fc4','teal':'#005f68','rose':'#b05a8a',
      'gray':'#5f6b6e','navy':'#1d3b70','olive':'#7d7a1c','brown':'#8c5a2b','wine':'#8e2c48','skyl':'#2f8fd0','lime':'#5f8f00'}
S={n:{k:(c if k=='normal' else simulate(c,k)) for k in KINDS} for n,c in pool.items()}
D={}
for a,b in itertools.combinations(pool,2):
    D[(a,b)]=D[(b,a)]=min(de2000(S[a][k],S[b][k]) for k in KINDS)
def mn(seq): return min(D[(a,b)] for a,b in itertools.combinations(seq,2))
best=None
names=[n for n in pool if n!='green']
for combo in itertools.permutations(names,4):
    seq=['green',*combo]
    m4=mn(seq)
    if best is None or m4>best[0]: best=(m4,seq)
print('best first5',best)
# extend greedily to 8
seq=best[1]
while len(seq)<8:
    nxt=max((n for n in pool if n not in seq), key=lambda n: min(D[(n,s)] for s in seq))
    seq.append(nxt)
print(seq,[pool[s] for s in seq])
for i in (4,5,6,8): print(i, round(mn(seq[:i]),1))
for a,b in itertools.combinations(seq,2):
    if D[(a,b)]<10: print('weak',a,b,round(D[(a,b)],1))
for n in seq: print(n,pool[n],round(contrast(pool[n],'#ffffff'),2))
print('----- fixed candidates')
def report(seq):
    print(seq,[pool[s] for s in seq],[round(mn(seq[:i]),1) for i in (3,4,5,6,8)])
    print('  weak:',[(a,b,round(D[(a,b)],1)) for a,b in itertools.combinations(seq,2) if D[(a,b)]<10])
pool['ochre']='#a8740a'; pool['plum2']='#7e4a6e'
for n in ('ochre','plum2'):
    S[n]={k:(pool[n] if k=='normal' else simulate(pool[n],k)) for k in KINDS}
for n in ('ochre','plum2'):
    for o in pool:
        if o!=n: D[(n,o)]=D[(o,n)]=min(de2000(S[n][k],S[o][k]) for k in KINDS)
for seq in (['green','blue','amber','navy','rose','teal','brown','skyl'],
            ['green','blue','amber','navy','rose','brown','skyl','olive'],
            ['green','navy','amber','skyl','rose','brown','teal','olive'],
            ['green','blue','amber','navy','verm','skyl','brown','rose'],
            ['green','blue','ochre','navy','rose','skyl','brown','olive']):
    report(seq)
print('----- no-warm search')
P=['blue','navy','sky','skyl','teal','rose','brown','plum2']
best=None
for perm in itertools.permutations(P,7):
    seq=['green',*perm]
    key=(round(mn(seq[:4]),1),round(mn(seq[:5]),1),round(mn(seq[:6]),1),round(mn(seq),1))
    if best is None or key>best[0]: best=(key,seq)
print(best); report(best[1])
print('----- extended')
extra={'g800':'#1e672d','khaki':'#857650','steel':'#4d7389','clay':'#a0583c','denim':'#3d5f9e','pine':'#2e5e4e'}
for n,c in extra.items():
    pool[n]=c; S[n]={k:(c if k=='normal' else simulate(c,k)) for k in KINDS}
for a,b in itertools.combinations(pool,2):
    D[(a,b)]=D[(b,a)]=min(de2000(S[a][k],S[b][k]) for k in KINDS)
P=['blue','navy','skyl','teal','rose','brown','g800','khaki','steel','clay','denim','pine']
best=None
for perm in itertools.permutations(P,4):
    seq=['green',*perm]; key=(round(mn(seq),1))
    if best is None or key>best[0]: best=(key,seq)
seq=best[1]
while len(seq)<8:
    nxt=max((n for n in P if n not in seq), key=lambda n: (min(D[(n,s)] for s in seq)))
    seq.append(nxt)
report(seq)
