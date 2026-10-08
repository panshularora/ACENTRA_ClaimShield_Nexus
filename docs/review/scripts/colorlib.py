"""Small colour toolkit: sRGB <-> OKLab/OKLCH, WCAG contrast, CVD simulation (Machado 2009, severity 1.0), CIEDE2000."""
import math
def hex2rgb(h):
    h=h.lstrip('#'); return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))
def rgb2hex(c): return '#'+''.join('%02x'%max(0,min(255,round(v*255))) for v in c)
def lin(c): return c/12.92 if c<=0.04045 else ((c+0.055)/1.055)**2.4
def delin(c): return 12.92*c if c<=0.0031308 else 1.055*c**(1/2.4)-0.055
def lum(h):
    r,g,b=[lin(v) for v in hex2rgb(h)]; return 0.2126*r+0.7152*g+0.0722*b
def contrast(a,b):
    la,lb=sorted([lum(a),lum(b)],reverse=True); return (la+0.05)/(lb+0.05)
def blend(fg,bg,alpha):
    f,b=hex2rgb(fg),hex2rgb(bg); return rgb2hex(tuple(alpha*x+(1-alpha)*y for x,y in zip(f,b)))
def rgb2oklab(h):
    r,g,b=[lin(v) for v in hex2rgb(h)]
    l=0.4122214708*r+0.5363325363*g+0.0514459929*b; m=0.2119034982*r+0.6806995451*g+0.1073969566*b; s=0.0883024619*r+0.2817188376*g+0.6299787005*b
    l,m,s=[math.copysign(abs(x)**(1/3),x) for x in (l,m,s)]
    return (0.2104542553*l+0.7936177850*m-0.0040720468*s, 1.9779984951*l-2.4285922050*m+0.4505937099*s, 0.0259040371*l+0.7827717662*m-0.8086757660*s)
def oklab2rgb(L,a,b):
    l=L+0.3963377774*a+0.2158037573*b; m=L-0.1055613458*a-0.0638541728*b; s=L-0.0894841775*a-1.2914855480*b
    l,m,s=l**3,m**3,s**3
    r=4.0767416621*l-3.3077115913*m+0.2309699292*s; g=-1.2684380046*l+2.6097574011*m-0.3413193965*s; bb=-0.0041960863*l-0.7034186147*m+1.7076147010*s
    return (r,g,bb)
def in_gamut(rgb): return all(-1e-4<=v<=1+1e-4 for v in rgb)
def oklch(h):
    L,a,b=rgb2oklab(h); return L, math.hypot(a,b), (math.degrees(math.atan2(b,a))%360)
def from_oklch(L,C,H):
    # reduce chroma until in gamut
    while True:
        a=C*math.cos(math.radians(H)); b=C*math.sin(math.radians(H)); rl=oklab2rgb(L,a,b)
        if in_gamut(rl) or C<=0: break
        C-=0.002
    return rgb2hex(tuple(delin(max(0,min(1,v))) for v in rl))
MACHADO={'deuteranopia':[[0.367322,0.860646,-0.227968],[0.280085,0.672501,0.047413],[-0.011820,0.042940,0.968881]],
         'protanopia':[[0.152286,1.052583,-0.204868],[0.114503,0.786281,0.099216],[-0.003882,-0.048116,1.051998]],
         'tritanopia':[[1.255528,-0.076749,-0.178779],[-0.078411,0.930809,0.147602],[0.004733,0.691367,0.303900]]}
def simulate(h,kind):
    r=[lin(v) for v in hex2rgb(h)]; M=MACHADO[kind]
    o=[sum(M[i][j]*r[j] for j in range(3)) for i in range(3)]
    return rgb2hex(tuple(delin(max(0,min(1,v))) for v in o))
def rgb2lab(h):
    r,g,b=[lin(v) for v in hex2rgb(h)]
    X=(0.4124*r+0.3576*g+0.1805*b)/0.95047; Y=(0.2126*r+0.7152*g+0.0722*b); Z=(0.0193*r+0.1192*g+0.9505*b)/1.08883
    f=lambda t: t**(1/3) if t>0.008856 else 7.787*t+16/116
    return 116*f(Y)-16, 500*(f(X)-f(Y)), 200*(f(Y)-f(Z))
def de2000(h1,h2):
    L1,a1,b1=rgb2lab(h1); L2,a2,b2=rgb2lab(h2)
    C1=math.hypot(a1,b1); C2=math.hypot(a2,b2); Cb=(C1+C2)/2
    G=0.5*(1-math.sqrt(Cb**7/(Cb**7+25**7))); a1p=(1+G)*a1; a2p=(1+G)*a2
    C1p=math.hypot(a1p,b1); C2p=math.hypot(a2p,b2)
    h1p=math.degrees(math.atan2(b1,a1p))%360; h2p=math.degrees(math.atan2(b2,a2p))%360
    dLp=L2-L1; dCp=C2p-C1p
    dhp=0 if C1p*C2p==0 else (h2p-h1p if abs(h2p-h1p)<=180 else (h2p-h1p-360 if h2p>h1p else h2p-h1p+360))
    dHp=2*math.sqrt(C1p*C2p)*math.sin(math.radians(dhp/2))
    Lbp=(L1+L2)/2; Cbp=(C1p+C2p)/2
    hbp=h1p+h2p if C1p*C2p==0 else ((h1p+h2p)/2 if abs(h1p-h2p)<=180 else ((h1p+h2p+360)/2 if h1p+h2p<360 else (h1p+h2p-360)/2))
    T=1-0.17*math.cos(math.radians(hbp-30))+0.24*math.cos(math.radians(2*hbp))+0.32*math.cos(math.radians(3*hbp+6))-0.20*math.cos(math.radians(4*hbp-63))
    dth=30*math.exp(-((hbp-275)/25)**2); RC=2*math.sqrt(Cbp**7/(Cbp**7+25**7))
    SL=1+0.015*(Lbp-50)**2/math.sqrt(20+(Lbp-50)**2); SC=1+0.045*Cbp; SH=1+0.015*Cbp*T; RT=-math.sin(math.radians(2*dth))*RC
    return math.sqrt((dLp/SL)**2+(dCp/SC)**2+(dHp/SH)**2+RT*(dCp/SC)*(dHp/SH))
