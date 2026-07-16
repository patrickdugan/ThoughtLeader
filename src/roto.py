"""Reusable rotoscope: photo -> 48x56 sprite grid, mapped to a face palette."""
from PIL import Image
import numpy as np
import sprites as S

def luminance_map(face, w=24, h=40):
    small = face.resize((w, h), Image.LANCZOS)
    arr = np.array(small)
    lum = (0.299*arr[:,:,0]+0.587*arr[:,:,1]+0.114*arr[:,:,2]).astype(int)
    ramp = ' .:-=+*#%@'
    return '\n'.join(''.join(ramp[min(9,v*10//256)] for v in row) for row in lum)

def rotoscope(path, crop, face_keys, hx0=13, hy0=7, hw=23, hh=38, bg_cut=90, lum_cut=None):
    im = Image.open(path).convert('RGB')
    W,H = im.size
    l,t,r,b = crop
    face = im.crop((int(W*l),int(H*t),int(W*r),int(H*b)))
    pal = {k:(int(v[1:3],16),int(v[3:5],16),int(v[5:7],16)) for k,v in face_keys.items()}
    def nearest(rgb):
        best,bk=1e9,list(face_keys)[0]
        for k,(rr,gg,bb) in pal.items():
            d=(rgb[0]-rr)**2+(rgb[1]-gg)**2+(rgb[2]-bb)**2
            if d<best: best,bk=d,k
        return bk
    small = face.resize((hw,hh), Image.LANCZOS)
    arr = np.array(small)
    g = S.blank()
    from sprites import rect, run
    rect(g,0,0,S.W-1,S.H-1,'k')
    for y in range(0,S.H,2): run(g,y,0,S.W-1,'n')
    for j in range(hh):
        for i in range(hw):
            gx,gy = hx0+i, hy0+j
            if not (0<=gx<S.W and 0<=gy<S.H): continue
            rgb = tuple(int(v) for v in arr[j,i])
            r_,g_,b_ = rgb
            # reject sky/blue background: blue clearly dominant and bright
            if b_ > 120 and b_ > r_ + 25 and g_ > r_: continue
            # reject bright neutral background (windows/walls) if lum_cut set
            if lum_cut and (0.299*r_+0.587*g_+0.114*b_) > lum_cut and max(rgb)-min(rgb) < 40:
                continue
            if sum(rgb) < bg_cut: continue
            g[gy][gx] = nearest(rgb)
    return g, face
