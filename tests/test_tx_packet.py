"""Complete TX waveform, length, packet-end and RX/CRC loopback checks."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
from btlelib import btle_tx, btle_rx, hex_string_to_bit, bit_to_hex_string, gauss_fir_gen, sin_cos_gen
sys.path.insert(0,str(ROOT/'scripts/validation'))
from result_guard import bad_lines


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quick',action='store_true')
    parser.add_argument('--rtl-rx',action='store_true',help='Also decode each actual TX waveform through the RTL receiver')
    parser.add_argument('--output',type=Path)
    a=parser.parse_args()
    cad=Path(os.environ.get('OSS_CAD',str(Path.home()/'eda/oss-cad-suite-20260907')))/'bin'
    rng=np.random.default_rng(8675309)
    cases=[(ch,n) for ch in ((0,10,37) if a.quick else range(40)) for n in (0,1,8,31)]
    if not a.quick:cases += [(ch,37) for ch in (37,38,39)]
    cases=[(ch,n,'555555') for ch,n in cases]+[(0,0,'000000'),(0,31,'000000'),(10,8,'123456'),(39,31,'ffffff')]
    rows=[]
    with tempfile.TemporaryDirectory(prefix='btle-tx-packet-') as temp:
        work=Path(temp);rtl=work/'rtl';shutil.copytree(ROOT/'verilog',rtl,ignore=shutil.ignore_patterns('*.txt','*.vcd'))
        tb=rtl/'btle_tx_tb.v';tb.write_text(re.sub(r'^\s*\$dump(?:file|vars)\b[^;]*;','',tb.read_text(),flags=re.M))
        defaults=os.environ.get('DUT_DEFAULTS','')
        for spec in defaults.split():
            file,assignment=spec.split(':');param,value=assignment.split('=');f=rtl/file
            text,n=re.subn(r'(parameter integer '+re.escape(param)+r' = )\d+',r'\g<1>'+str(int(value)),f.read_text())
            if n!=1:raise RuntimeError('parameter override not applied exactly once: '+spec)
            f.write_text(text)
        files=[str(f) for f in rtl.glob('*.v') if not f.name.endswith('_tb.v') and f.name not in {'btle_controller_wrapper.v','sdpram_two_clk_xilinx.v'}]
        subprocess.run([str(cad/'iverilog'),'-s','btle_tx_tb','-o',str(work/'sim'),str(tb),*files],check=True,capture_output=True,timeout=60)
        if a.rtl_rx:
            rx_tb=rtl/'btle_rx_tb.v';rx_tb.write_text(re.sub(r'^\s*\$dump(?:file|vars)\b[^;]*;','',rx_tb.read_text(),flags=re.M))
            subprocess.run([str(cad/'iverilog'),'-s','btle_rx_tb','-o',str(work/'rx_sim'),str(rx_tb),*files],check=True,capture_output=True,timeout=60)
        vectors=work/'vectors';vectors.mkdir()
        taps=np.int8(np.round(128*gauss_fir_gen()));cos,sin=sin_cos_gen(64)
        for name,data in [('gauss_filter_tap',taps),('cos_table',cos),('sin_table',sin)]:np.savetxt(vectors/(name+'.txt'),data,fmt='%d')
        for ch,n,init in cases:
            payload=rng.integers(0,256,n,dtype=np.uint8).tobytes()
            packet=bytes([0x42 if ch>=37 else 1,n])+payload
            pdu=hex_string_to_bit(packet.hex());crc=hex_string_to_bit(init);aa='D6BE898E' if ch>=37 else '1B0A8560'
            i,q,_,_=btle_tx(pdu,ch,crc,aa)
            (vectors/'btle_config.txt').write_text(f'{len(pdu):x}\n{ch:x}\n{init}\n{aa}\n')
            (vectors/'btle_tx_test_input.txt').write_text(''.join(f'{v:02x}\n' for v in packet))
            for name,data in [('i',i),('q',q)]:np.savetxt(vectors/f'btle_tx_test_output_{name}_ref.txt',data,fmt='%d')
            run=subprocess.run([str(cad/'vvp'),'-n',str(work/'sim')],cwd=vectors,capture_output=True,text=True,timeout=30)
            log=run.stdout+run.stderr
            if run.returncode or bad_lines(log) or not all(f'output {c} Test PASS.' in log for c in 'IQ'):
                failure=ROOT/'results/validation/product-tx'/f'failure-{ch}-{n}'
                shutil.copytree(vectors,failure,dirs_exist_ok=True);(failure/'sim.log').write_text(log)
                raise RuntimeError(f'TX channel={ch} length={n} exit={run.returncode}: '+log[-2500:])
            actual_i=np.loadtxt(vectors/'btle_tx_test_output_i.txt',dtype=np.int16)
            actual_q=np.loadtxt(vectors/'btle_tx_test_output_q.txt',dtype=np.int16)
            np.testing.assert_array_equal(actual_i,i)
            np.testing.assert_array_equal(actual_q,q)
            decoded=btle_rx(actual_i,actual_q,ch,crc,aa)
            if not decoded[1] or bit_to_hex_string(decoded[0])!=packet.hex():raise RuntimeError(f'Incomplete/wrong loopback packet channel={ch} length={n}')
            if a.rtl_rx:
                np.savetxt(vectors/'btle_rx_test_input_i.txt',actual_i,fmt='%d')
                np.savetxt(vectors/'btle_rx_test_input_q.txt',actual_q,fmt='%d')
                (vectors/'btle_rx_test_output_crc_ok_ref.txt').write_text('1\n')
                (vectors/'btle_rx_test_output_ref.txt').write_text(''.join(f'{v:02x}\n' for v in packet))
                rr=subprocess.run([str(cad/'vvp'),'-n',str(work/'rx_sim')],cwd=vectors,capture_output=True,text=True,timeout=30)
                if rr.returncode or bad_lines(rr.stdout+rr.stderr) or '0 difference found' not in rr.stdout:
                    raise RuntimeError(f'RTL RX loopback channel={ch} length={n}: '+rr.stdout[-1800:]+rr.stderr[-500:])
                if ''.join((vectors/'btle_rx_test_output.txt').read_text().split())!=packet.hex():
                    raise RuntimeError('RTL RX returned a different PDU')
            rows.append(dict(rtl_rx_checked=a.rtl_rx,channel=ch,payload_octets=n,crc_init=init,samples=len(actual_i),expected_samples=len(i),crc=True,pdu=packet.hex(),result='PASS'))
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(rows,indent=2)+'\n')
    print(f'PASS: {len(rows)} complete TX waveforms and exact CRC-valid loopback PDUs')

if __name__=='__main__':main()
