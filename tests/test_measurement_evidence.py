"""Positive controls and malformed-evidence tests for PPA reporting tools."""
import importlib.util,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class MeasurementEvidenceTests(unittest.TestCase):
    def run_tool(self,script,*args):
        path=ROOT/script
        if not path.exists():self.skipTest('measurement tool absent on this branch')
        return subprocess.run([sys.executable,str(path),*map(str,args)],capture_output=True,text=True,timeout=20)
    def area_fixture(self,root,fault='positive'):
        d=root/'btle_controller';d.mkdir();(d/'stage.ys').write_text('fixture')
        design={'num_cells':1,'num_cells_by_type':{'DFF_X1':1},'area':2.}
        modules={'btle_controller':{'attributes':{'top':'1'},'cells':{'ff':{'type':'DFF_X1'}}}}
        if fault=='missing_area':design.pop('area')
        if fault=='nan':design['area']=float('nan')
        if fault=='negative':design['area']=-1
        if fault=='zero':design['area']=0
        if fault=='missing_types':design['num_cells_by_type']={}
        if fault=='wrong_types':design['num_cells_by_type']={'OTHER':1}
        if fault=='wrong_top':modules={'wrong':modules['btle_controller']}
        if fault=='multiple_tops':modules['second']=modules['btle_controller']
        (d/'stat.json').write_text(json.dumps({'design':design}));(d/'netlist.json').write_text(json.dumps({'modules':modules}))
    def test_openram_geometry(self):
        if not (ROOT/'scripts/area/summarize_openram.py').exists():self.skipTest('OpenRAM tool absent on this branch')
        for fault in ['positive','zero','negative','infinite','empty','duplicate','wrong_geometry','wrong_mask','missing_macro']:
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);row=['sram_1rw_8x256','1rw','8','256','16','10','']
                if fault=='zero':row[4]='0'
                if fault=='negative':row[4]='-1'
                if fault=='infinite':row[4]='1e999'
                if fault=='wrong_geometry':row[2]='16'
                if fault=='wrong_mask':row[6]='3'
                data='\t'.join(row)+'\n'
                if fault=='empty':data=''
                if fault=='duplicate':data+=data
                file=root/'sizes.tsv';file.write_text(data)
                names=['sram_1rw_8x256']+(['sram_1rw_8x512'] if fault=='missing_macro' else [])
                r=self.run_tool('scripts/area/summarize_openram.py',file,'fixture',*names)
                self.assertEqual(r.returncode==0,fault=='positive',r.stdout+r.stderr)

    def test_area_evidence(self):
        if not (ROOT/'scripts/area/summarize_area.py').exists():self.skipTest('measurement tool absent on this branch')
        for fault in ['positive','missing_area','nan','negative','zero','missing_types','wrong_types','wrong_top','multiple_tops']:
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);self.area_fixture(root,fault);r=self.run_tool('scripts/area/summarize_area.py',root)
                self.assertEqual(r.returncode==0,fault=='positive',r.stdout+r.stderr)
    def timing_fixture(self,root,fault='positive'):
        unit='1ps' if fault=='picoseconds' else '1ns'
        edge='falling_edge' if fault=='falling_edge' else 'rising_edge'
        values='0.2, NaN, 0.3' if fault=='nan' else '0.2, 1e999' if fault=='infinite' else '0.2, 0.3'
        cq=f'pin(Q) {{ timing() {{ timing_type : {edge}; cell_rise(tbl) {{ values("{values}"); }} }} }}'
        setup='pin(D) { timing() { timing_type : setup_rising; rise_constraint(tbl) { values("0.1"); } } }'
        if fault=='missing_cq':cq=''
        if fault=='missing_setup':setup=''
        text=f'library(test) {{ time_unit : "{unit}"; cell(DFF_X1) {{ {cq} {setup} }} }}'
        if fault=='unclosed':text=text[:-2]
        if fault=='missing_unit':text=text.replace(f'time_unit : "{unit}";','')
        f=root/'test.lib';f.write_text(text)
        cells=[] if fault=='no_cells' else ['DFF_X1','DFF_X1'] if fault=='duplicates' else ['MISSING'] if fault=='unknown_cell' else ['DFF_X1']
        return [f,*cells]
    def test_timing_evidence(self):
        if not (ROOT/'scripts/timing/seq_constraints.py').exists():self.skipTest('measurement tool absent on this branch')
        for fault in ['positive','falling_edge','picoseconds','no_cells','duplicates','unknown_cell','missing_cq','missing_setup','nan','infinite','missing_unit']:
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as temp:
                args=self.timing_fixture(Path(temp),fault);r=self.run_tool('scripts/timing/seq_constraints.py',*args)
                positive=fault in ('positive','falling_edge','picoseconds')
                self.assertEqual(r.returncode==0,positive,r.stdout+r.stderr)
                if positive:self.assertIn('sequential_overhead_ns '+('0.0004' if fault=='picoseconds' else '0.4000'),r.stdout)
    def activity_fixture(self,root,fault='positive'):
        lib=root/'test.lib';lib.write_text('capacitive_load_unit (1, ff); cell(BUF_X1) { pin(A) { direction : input; capacitance : 1.0; } pin(Z) { direction : output; } }')
        if fault=='missing_cap':lib.write_text(lib.read_text().replace('capacitance : 1.0;',''))
        if fault=='nan_cap':lib.write_text(lib.read_text().replace('capacitance : 1.0;','capacitance : NaN;'))
        if fault=='missing_unit':lib.write_text(lib.read_text().replace('capacitive_load_unit (1, ff);',''))
        for side,top in [('ref','btle_controller_ref'),('dut','btle_controller')]:
            typ='MISSING' if fault=='unknown_cell' else 'BUF_X1'
            (root/(side+'.v')).write_text(f'module {top} (a,z);\n input a;\n output z;\n {typ} inst (.A(a),.Z(z));\nendmodule\n')
        def saif(count):
            text='(INSTANCE tb_activity\n'
            for side in ('ref','dut'):
                text+=f'(INSTANCE u_{side}\n(NET\n'
                for net in ('a','z'):
                    if fault=='missing_net' and side=='ref' and net=='z' and count:continue
                    text+=f'({net} (T0 0) (T1 0) (TX 0) (TC {count}))\n'
                text+=')\n)\n'
            return text+')\n'
        run=root/'run.saif';setup=root/'setup.saif'
        run.write_text('' if fault=='empty' else saif(20));setup.write_text('' if fault=='missing_setup' else saif(30 if fault=='decreasing' else 0))
        if fault=='duplicate':run.write_text(run.read_text().replace('(a (T0 0) (T1 0) (TX 0) (TC 20))','(a (T0 0) (T1 0) (TX 0) (TC 20))\n(a (T0 0) (T1 0) (TX 0) (TC 20))',1))
        return [run,setup,root/'ref.v',root/'dut.v',lib,'0' if fault=='zero_window' else '100','tx',root/'result.json']
    def test_activity_evidence(self):
        if not (ROOT/'scripts/power/saif_activity.py').exists():self.skipTest('measurement tool absent on this branch')
        for fault in ['positive','empty','missing_setup','missing_net','decreasing','unknown_cell','duplicate','zero_window','missing_cap','nan_cap','missing_unit']:
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);args=self.activity_fixture(root,fault);r=self.run_tool('scripts/power/saif_activity.py',*args)
                self.assertEqual(r.returncode==0,fault=='positive',r.stdout+r.stderr)
                if fault=='positive':self.assertEqual(json.loads((root/'result.json').read_text())['status'],'COMPLETE')
                if fault=='missing_net':self.assertEqual(json.loads((root/'result.json').read_text())['status'],'INCOMPLETE')
    def test_activity_saif_names(self):
        """Verilator's SAIF names: bits from 0 whatever the LSB, [0:0] without index, escaped names with brackets."""
        if not (ROOT/'scripts/power/saif_activity.py').exists():self.skipTest('measurement tool absent on this branch')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);lib=root/'test.lib'
            lib.write_text('capacitive_load_unit (1, ff); cell(BUF_X1) { pin(A) { direction : input; capacitance : 1.0; } pin(Z) { direction : output; } }')
            for side,top in [('ref','btle_controller_ref'),('dut','btle_controller')]:
                (root/(side+'.v')).write_text(f'module {top} (a);\n input a;\n wire [9:8] \\x.buf ;\n wire [0:0] st;\n wire [1:0] \\d[0] ;\n wire o;\n'
                    ' BUF_X1 b8 (.A(a),.Z(\\x.buf [8]));\n BUF_X1 b9 (.A(a),.Z(\\x.buf [9]));\n BUF_X1 s (.A(\\x.buf [9]),.Z(st));\n'
                    ' BUF_X1 u (.A(st),.Z(\\d[0] [0]));\n BUF_X1 v (.A(\\d[0] [0]),.Z(\\d[0] [1]));\n BUF_X1 w (.A(\\d[0] ),.Z(o));\nendmodule\n')
            def saif(scale):
                text='(INSTANCE tb_activity\n'
                for side in ('ref','dut'):
                    text+=f'(INSTANCE u_{side}\n(NET\n'
                    for net,count in [('a',1),('x.buf\\[0\\]',2),('x.buf\\[1\\]',3),('st',4),('d[0]\\[0\\]',5),('d[0]\\[1\\]',6),('o',7)]:
                        text+=f'({net} (T0 0) (T1 0) (TX 0) (TC {count*scale}))\n'
                    text+=')\n)\n'
                return text+')\n'
            (root/'run.saif').write_text(saif(10));(root/'setup.saif').write_text(saif(0))
            r=self.run_tool('scripts/power/saif_activity.py',root/'run.saif',root/'setup.saif',root/'ref.v',root/'dut.v',lib,'100','tx',root/'result.json')
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            d=json.loads((root/'result.json').read_text())
            self.assertEqual(d['status'],'COMPLETE')
            # loads: a 2 (b8, b9), x.buf[9] 1, st 1, d[0][0] 2 (v, w), d[0][1] 1 (w); a wrong bit would change the sum
            self.assertEqual(d['ref']['data_cap_tog'],10*2+30*1+40*1+50*2+60*1)
            self.assertEqual(d['ref']['toggles'],10+20+30+40+50+60+70)
    def test_activity_summary_evidence(self):
        if not (ROOT/'scripts/power/summarize_activity.py').exists():self.skipTest('activity summary absent on this branch')
        for fault in ['positive','missing_status','missing_nets','negative','nonfinite','empty_cells','null_exit','wrong_window']:
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);args=self.activity_fixture(root);r=self.run_tool('scripts/power/saif_activity.py',*args)
                self.assertEqual(r.returncode,0,r.stdout+r.stderr)
                d=json.loads((root/'result.json').read_text())
                if fault=='missing_status':d.pop('status')
                if fault=='missing_nets':d['ref']['missing']=1
                if fault=='negative':d['ref']['data_cap_tog']=-1
                if fault=='nonfinite':d['ref']['data_cap_tog']=float('nan')
                if fault=='empty_cells':d['ref']['cells']=0
                scenarios=['rx','tx','mixed','idle','idle0']
                for scenario in scenarios:
                    d['scenario']=scenario
                    if fault=='wrong_window' and scenario=='idle0':d['window_cycles']=101
                    (root/(scenario+'.json')).write_text(json.dumps(d))
                codes={name:0 for name in scenarios+['setup']}
                if fault=='null_exit':codes['rx']=None
                (root/'exit_codes.json').write_text(json.dumps(codes))
                r=self.run_tool('scripts/power/summarize_activity.py',root)
                self.assertEqual(r.returncode==0,fault=='positive',r.stdout+r.stderr)

    def test_summary_rejects_unverified_activity(self):
        script=ROOT/'scripts/compare/summarize_compare.py'
        if not script.exists():self.skipTest('comparison tool absent on this branch')
        spec=importlib.util.spec_from_file_location('compare_under_test',script);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'exit_codes.json').write_text(json.dumps({s:0 for s in mod.SCENARIOS+['setup']}));(root/'rx.json').write_text(json.dumps({'window_cycles':100,'ref':{'missing':12},'dut':{'missing':12}}))
            with self.assertRaisesRegex(RuntimeError,'incomplete/unverified'):mod.read_activity(root)

if __name__=='__main__':unittest.main(verbosity=2)
