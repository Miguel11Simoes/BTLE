"""Reintroduce each repaired defect and require its concrete failure witness."""
import argparse,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    mutations=[
      ('truncated_tail','gfsk_modulation.v',"assign last = raw_valid && ({27'b0, padding} == NUM_TAPS-1);",'assign last = raw_last;','test_tx_packet.py','TX output length differs from the complete reference'),
      ('channel_zero_remapped','scramble_core.v','assign channel_number_internal = channel_number;',"assign channel_number_internal = (channel_number == 0) ? 6'd63 : channel_number;",'test_tx_packet.py','error found!'),
      ('crc_zero_replaced','crc24_core.v','assign crc_state_init_bit_internal = crc_state_init_bit;',"assign crc_state_init_bit_internal = (crc_state_init_bit == 0) ? 24'h555555 : crc_state_init_bit;",'test_tx_packet.py','error found!'),
      ('undriven_reserved','btle_ll.v',"assign slv_reg42 = {C_S00_AXI_DATA_WIDTH{1'b0}};",'','test_control_readback.py','reserved read 42 is not known zero'),
    ]
    rows=[]
    with tempfile.TemporaryDirectory(prefix='btle-product-mutations-') as temp:
        work=Path(temp)
        for d in ('python','tests','scripts/validation','verilog'):
            shutil.copytree(ROOT/d,work/d,ignore=shutil.ignore_patterns('*.txt','*.vcd','__pycache__'))
        def execute(name,test,mutated,witness=''):
            cmd=[sys.executable,str(work/'tests'/test)]+(['--quick'] if test=='test_tx_packet.py' else [])
            r=subprocess.run(cmd,cwd=work,capture_output=True,text=True,timeout=180)
            log=r.stdout+r.stderr;(args.output/(name+'.log')).write_text(log)
            good=(r.returncode==1 and witness in log) if mutated else r.returncode==0
            rows.append(dict(name=name,exit=r.returncode,expected_failure=mutated,witness=witness,result='PASS' if good else 'FAIL'))
            if not good:raise RuntimeError(name+' did not produce its required outcome: '+log[-2000:])
        execute('baseline_tx','test_tx_packet.py',False)
        execute('baseline_readback','test_control_readback.py',False)
        for name,file,before,after,test,witness in mutations:
            path=work/'verilog'/file;original=path.read_text()
            if original.count(before)!=1:raise RuntimeError('mutation did not apply exactly once: '+name)
            try:
                path.write_text(original.replace(before,after));execute(name,test,True,witness)
            finally:path.write_text(original)
    (args.output/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('PASS: 2 baselines, 4 defects caught by concrete data/length/readback failures')
if __name__=='__main__':main()
