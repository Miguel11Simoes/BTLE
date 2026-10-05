"""Test valid gaps on the documented 2:1 clock interface; this is not CDC signoff."""
import argparse,json,os,re,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--mutants',action='store_true')
    parser.add_argument('--rtl',type=Path,default=ROOT/'verilog/clock_domain_conversion_iq.v')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    compiler=os.environ.get('IVERILOG','/home/msmiguel/eda/oss-cad-suite-20260907/bin/iverilog')
    simulator=os.environ.get('VVP','/home/msmiguel/eda/oss-cad-suite-20260907/bin/vvp')
    source=args.rtl.read_text();results=[]
    variants={'baseline':source}
    if args.mutants:
        old='rx_iq_valid <= (~rx_sample_phase) && rx_iq_valid_ext;'
        if source.count(old)!=1:raise SystemExit('mutation target missing')
        variants['ignore_valid']=source.replace(old,'rx_iq_valid <= (~rx_sample_phase);')
        variants['gate_feedback']=source.replace(old,'rx_iq_valid <= (~rx_iq_valid) && rx_iq_valid_ext;')
    with tempfile.TemporaryDirectory() as directory:
        work=Path(directory)
        for name,rtl in variants.items():
            src=work/(name+'.v');src.write_text(rtl);binary=work/(name+'.out')
            build=subprocess.run([compiler,'-g2012','-s','tb_clock_domain_contract','-o',str(binary),str(ROOT/'tests/clock_domain_contract_tb.v'),str(src)],capture_output=True,text=True,timeout=30)
            (args.output/(name+'-compile.log')).write_text(build.stdout+build.stderr)
            if build.returncode:raise SystemExit('clock contract compilation failed')
            caught=False
            for mode in (0,1,2):
                for phase in (1250,3750,6250,8750):
                    run=subprocess.run([simulator,'-n',str(binary),f'+mode={mode}',f'+phase_ps={phase}'],capture_output=True,text=True,timeout=15)
                    log=run.stdout+run.stderr;(args.output/f'{name}-{mode}-{phase}.log').write_text(log)
                    marker=re.search(r'CLOCK CONTRACT PASS mode (\d+) phase_ps (\d+) checked (\d+) accepted (\d+) quiet (\d+)',log)
                    if name=='baseline':
                        passed=run.returncode==0 and marker is not None and int(marker[3])>=400 and 'FATAL' not in log
                        results.append(dict(variant=name,mode=mode,phase_ps=phase,exit=run.returncode,result='PASS' if passed else 'FAIL',statistics=marker.group(0) if marker else ''))
                    elif run.returncode!=0 and 'RX valid contract:' in log:
                        caught=True;results.append(dict(variant=name,mode=mode,phase_ps=phase,exit=run.returncode,result='DETECTED',witness=next(l for l in log.splitlines() if 'RX valid contract:' in l)));break
                    elif run.returncode!=0 or marker is None:
                        raise SystemExit('mutant engine error or missing verdict is not a detection')
                if caught:break
            if name!='baseline' and not caught:results.append(dict(variant=name,result='ESCAPED'))
    (args.output/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    if not results or any(r['result'] not in ('PASS','DETECTED') for r in results):raise SystemExit('CLOCK CONTRACT FAIL')
    print(f"CLOCK CONTRACT PASS: {sum(r['result']=='PASS' for r in results)} scenarios; {sum(r['result']=='DETECTED' for r in results)} mutants detected")
if __name__=='__main__':main()
