from pathlib import Path
import os,subprocess,tempfile,sys
p=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(p/'scripts/validation'))
from result_guard import sim_pass
cad=Path(os.environ.get('OSS_CAD',str(Path.home()/'eda/oss-cad-suite-20260907')))/'bin'
with tempfile.TemporaryDirectory() as temp:
    exe=Path(temp)/'sim'
    subprocess.run([str(cad/'iverilog'),'-s','tail_tb','-o',str(exe),str(p/'tests/gauss_tail_tb.v'),str(p/'verilog/gfsk_modulation.v'),str(p/'verilog/gauss_filter.v'),str(p/'verilog/sdpram_one_clk.v')],check=True,capture_output=True,timeout=60)
    r=subprocess.run([str(cad/'vvp'),'-n',str(exe)],capture_output=True,text=True,timeout=20)
    print(r.stdout+r.stderr,end='')
    if not sim_pass(r.returncode,r.stdout+r.stderr,'TAIL PASS'):raise SystemExit(1)
