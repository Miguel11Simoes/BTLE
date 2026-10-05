"""Validate OpenRAM macro geometry before reporting area (not DRC/LVS signoff)."""
import csv,math,re,sys
from pathlib import Path

def main():
    source,label,*expected=sys.argv[1:]
    if not expected or len(expected)!=len(set(expected)):raise SystemExit('nonempty unique macro list required')
    rows=[];seen=set()
    with open(source,newline='') as stream:
        for row in csv.reader(stream,delimiter='\t'):
            if not row or not any(s.strip() for s in row):continue
            if len(row)!=7:raise SystemExit('incomplete macro dimensions')
            name,ports,ws,nw,w,h,mask=row
            match=re.fullmatch(r'sram_(1rw|1rw1r)_(\d+)x(\d+)(?:_m(\d+))?',name)
            if not match or name in seen or ports!=match[1] or int(ws)!=int(match[2]) or int(nw)!=int(match[3]) or mask!=(match[4] or ''):
                raise SystemExit('duplicate or inconsistent macro geometry')
            seen.add(name);bits=int(ws)*int(nw);width,height=float(w),float(h);area=width*height
            if int(ws)<=0 or int(nw)<=0 or any(not math.isfinite(v) or v<=0 for v in (width,height,area)):
                raise SystemExit('macro dimensions and area must be finite and positive')
            if mask and (int(mask)<=0 or int(ws)%int(mask)):raise SystemExit('invalid write-mask geometry')
            rows.append((name,ports,ws,nw,width,height,mask,bits,area))
    if seen!=set(expected):raise SystemExit('missing/unexpected macro dimensions')
    print(f'# OpenRAM macros, FreePDK45 (run {label})\n')
    print('| Macro | Ports | Words x bits | Bits | Width (um) | Height (um) | Area (um2) | um2 per bit |')
    print('|---|---|---|---:|---:|---:|---:|---:|')
    for name,ports,ws,nw,w,h,mask,bits,area in rows:
        ports=ports.upper()+(f', {mask}-bit write mask' if mask else '')
        print(f'| `{name}` | {ports} | {nw} x {ws} | {bits} | {w:.3f} | {h:.3f} | {area:.1f} | {area/bits:.2f} |')
if __name__=='__main__':main()
