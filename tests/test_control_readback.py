"""Known reserved readback over AXI, with independent clocks and backpressure."""
from pathlib import Path
import os,subprocess,tempfile,sys
p=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(p/'scripts/validation'))
from result_guard import sim_pass
cad=Path(os.environ.get('OSS_CAD',str(Path.home()/'eda/oss-cad-suite-20260907')))/'bin'
with tempfile.TemporaryDirectory() as temp:
    exe=Path(temp)/'sim'
    files=[str(f) for f in (p/'verilog').glob('*.v') if not f.name.endswith('_tb.v') and f.name not in {'btle_controller_wrapper.v','sdpram_two_clk_xilinx.v'}]
    subprocess.run([str(cad/'iverilog'),'-s','reserved_registers_tb','-o',str(exe),str(p/'tests/reserved_registers_tb.v'),*files],check=True,capture_output=True,timeout=60)
    r=subprocess.run([str(cad/'vvp'),'-n',str(exe)],capture_output=True,text=True,timeout=20)
    print(r.stdout+r.stderr,end='')
    if not sim_pass(r.returncode,r.stdout+r.stderr,'READBACK PASS'):raise SystemExit(1)
