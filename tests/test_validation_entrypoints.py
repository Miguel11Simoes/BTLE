"""Run the actual shell/Python entry points against failing external tools.

These are harness fault-injection tests, not RTL validation. The fixture uses a
private clone, real RTL compilation and vector generation, and fake simulators
or proof engines. A fake engine never provides evidence of design correctness.
"""
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CAD = Path(os.environ.get('OSS_CAD', str(Path.home()/'eda/oss-cad-suite-20260907')))


class EntryPointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='btle-guard-test-')
        cls.work=Path(cls.temp.name);cls.repo=cls.work/'repo';cls.bin=cls.work/'cad/bin';cls.bin.mkdir(parents=True)
        subprocess.run(['git','clone','--quiet','--shared','--no-checkout',str(ROOT),str(cls.repo)],check=True)
        subprocess.run(['git','-C',str(cls.repo),'read-tree','HEAD'],check=True)
        subprocess.run(['git','-C',str(cls.repo),'update-ref','refs/heads/master','refs/remotes/origin/master'],check=True)
        for folder in ('scripts','verilog','tests','python'):
            if (ROOT/folder).exists():shutil.copytree(ROOT/folder,cls.repo/folder)
        # This fixture tests failing engines, not RTL equivalence. Snapshot the
        # common dependency files into its PRIVATE reference so the RX runner's
        # shared-source guard remains satisfied even with uncommitted RTL edits.
        # Functional reference comparisons are separate real-simulator campaigns.
        shared = ['search_unique_bit_sequence.v', 'scramble_core.v', 'crc24_core.v',
                  'serial_in_ram_out.v', 'sdpram_two_clk.v']
        subprocess.run(['git', '-C', str(cls.repo), 'read-tree', 'master'], check=True)
        subprocess.run(['git', '-C', str(cls.repo), 'add', *['verilog/'+f for f in shared]], check=True)
        tree = subprocess.check_output(['git', '-C', str(cls.repo), 'write-tree'], text=True).strip()
        identity = dict(os.environ, GIT_AUTHOR_NAME='Harness fixture', GIT_AUTHOR_EMAIL='fixture@localhost',
                        GIT_COMMITTER_NAME='Harness fixture', GIT_COMMITTER_EMAIL='fixture@localhost')
        fixture_ref = subprocess.check_output(['git', '-C', str(cls.repo), 'commit-tree', tree, '-p', 'master',
            '-m', 'Private fault-injection fixture: align common dependency sources'], env=identity, text=True).strip()
        subprocess.run(['git', '-C', str(cls.repo), 'update-ref', 'refs/heads/master', fixture_ref], check=True)
        for name in ('iverilog','yosys'):
            p=cls.bin/name;p.write_text('#!/bin/sh\nexec '+str(CAD/'bin'/name)+' "${@}"\n');p.chmod(0o755)
        cls.env=dict(os.environ,OSS_CAD=str(cls.bin.parent),VVP=str(cls.bin/'vvp'),IVERILOG=str(cls.bin/'iverilog'))

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def tool(self,name,body):
        p=self.bin/name
        prefix='import pathlib,json,sys\npathlib.Path('+repr(str(self.work/'calls.jsonl'))+').open("a").write(json.dumps({"tool":'+repr(name)+',"argv":sys.argv})+"\\n")\n'
        p.write_text('#!/usr/bin/python3\n'+prefix+body);p.chmod(0o755)

    def reject(self,cmd,expect_tool="vvp",expect_mutant=False):
        calls=self.work/'calls.jsonl'
        calls.unlink(missing_ok=True)
        p=subprocess.run(cmd,cwd=self.repo,env=self.env,capture_output=True,text=True,timeout=180)
        self.assertNotEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertNotIn('RESULT: PASS',p.stdout+p.stderr)
        if expect_tool:
            self.assertTrue(calls.exists(), 'intended fake engine was never invoked: '+p.stdout+p.stderr)
            records=[json.loads(line) for line in calls.read_text().splitlines()]
            self.assertIn(expect_tool,[row['tool'] for row in records])
            if expect_mutant:
                self.assertTrue(any('/mut_' in arg or '/m1_' in arg for row in records for arg in row['argv']), 'intended mutant engine was never invoked')

    def test_mutation_tool_crash_is_not_detection(self):
        if not any((self.repo/'scripts/validation'/r).exists() for r in ('ctl_lockstep/run_ctl_lockstep.sh','rx_lockstep/run_rx_lockstep.sh','table_random/run_table_random.sh')):
            self.skipTest('this branch has no shell mutation runner')
        self.tool('vvp',"import sys\nprint('CTL LOCKSTEP PASS');print('LOCKSTEP PASS');print('TABLE RANDOM PASS');print('FIR2 RANDOM PASS');print('PASS sweep: complete')\nraise SystemExit(42 if any('/mut_' in a or '/m1_' in a for a in sys.argv) else 0)\n")
        for relative,extra in [('ctl_lockstep/run_ctl_lockstep.sh',['1','1']),('rx_lockstep/run_rx_lockstep.sh',['1','1']),('table_random/run_table_random.sh',['1'])]:
            if (self.repo/'scripts/validation'/relative).exists():
                with self.subTest(runner=relative):
                    self.reject(['bash','scripts/validation/'+relative,'injected-mutant-crash-'+Path(relative).stem,*extra,*(['master'] if relative.startswith(('ctl_lockstep/','rx_lockstep/')) else [])],expect_mutant=True)

    def test_exit_after_pass_is_rejected(self):
        if not (self.repo/'tests/test_vco_sin4.py').exists() and not any((self.repo/'scripts/validation'/r).exists() for r in ('ctl_lockstep/run_ctl_lockstep.sh','rx_lockstep/run_rx_lockstep.sh','table_random/run_table_random.sh')):
            self.skipTest('this branch has no applicable VCO/lockstep runner')
        self.tool('vvp',"import sys\nprint('CTL LOCKSTEP PASS');print('LOCKSTEP PASS');print('TABLE RANDOM PASS');print('PASS: 3072 cycles matched master VCO')\nraise SystemExit(42)\n")
        for relative,extra in [('ctl_lockstep/run_ctl_lockstep.sh',['1','1']),('rx_lockstep/run_rx_lockstep.sh',['1','1']),('table_random/run_table_random.sh',['1'])]:
            if (self.repo/'scripts/validation'/relative).exists():
                with self.subTest(runner=relative):
                    self.reject(['bash','scripts/validation/'+relative,'injected-post-pass-'+Path(relative).stem,*extra,*(['master'] if relative.startswith(('ctl_lockstep/','rx_lockstep/')) else [])])
        if (self.repo/'tests/test_vco_sin4.py').exists():
            self.reject(['python3','tests/test_vco_sin4.py'])

    def test_proof_status_cannot_hide_engine_error(self):
        if not any((self.repo/'scripts/validation'/r).exists() for r in ('formal_gauss/run_formal_gauss.sh','formal_demod/run_formal.sh')):
            self.skipTest('this branch has no applicable formal runner')
        self.tool('sby',"from pathlib import Path\nimport sys\ns=next(a for a in sys.argv if a.endswith('.sby'));i=sys.argv.index(s);task=sys.argv[i+1:];d=Path(Path(s).stem+('' if not task else '_'+task[0]));d.mkdir(exist_ok=True);(d/'status').write_text('FAIL' if 'mut_' in str(Path.cwd()) else 'PASS');raise SystemExit(16)\n")
        for relative in ('formal_gauss/run_formal_gauss.sh','formal_demod/run_formal.sh'):
            if (self.repo/'scripts/validation'/relative).exists():
                with self.subTest(runner=relative):
                    self.reject(['bash','scripts/validation/'+relative,'injected-proof-error'],expect_tool='sby')

    def test_empty_campaign_is_rejected(self):
        if not any((self.repo/'scripts/validation'/r).exists() for r in ('ctl_lockstep/run_ctl_lockstep.sh','rx_lockstep/run_rx_lockstep.sh','table_random/run_table_random.sh')):
            self.skipTest('this branch has no shell campaign runner')
        for relative in ('ctl_lockstep/run_ctl_lockstep.sh','rx_lockstep/run_rx_lockstep.sh','table_random/run_table_random.sh'):
            if (self.repo/'scripts/validation'/relative).exists():
                with self.subTest(runner=relative):
                    self.reject(['bash','scripts/validation/'+relative,'injected-empty','0'],expect_tool=None)

    def test_activity_wait_checks_every_process(self):
        runner=self.repo/'scripts/power/run_activity.sh'
        if not runner.exists():self.skipTest('this branch has no activity runner')
        source=runner.read_text();start=source.index('# 4. runs:');end=source.index('for s in "${scenarios[@]}"; do\n  if sim_pass',start)
        block=source[start:end]
        work=self.work/'activity';(work/'obj').mkdir(parents=True);(work/'vec/verilog').mkdir(parents=True)
        sim=work/'obj/sim';sim.write_text('#!/usr/bin/python3\nimport os,sys\nprint("ACTIVITY RUN PASS")\nraise SystemExit(42 if "+scenario="+os.environ.get("BAD_SCENARIO", "none") in sys.argv else 0)\n');sim.chmod(0o755)
        for scenario in ('none','setup','tx'):
            out=work/scenario;out.mkdir()
            script='set -euo pipefail\nrepo='+str(self.repo)+'\nsource "$repo/scripts/validation/result_guard.sh"\nwork='+str(work)+'\nout='+str(out)+'\nseed=1\nwindow=100000\nscenarios=(rx tx mixed idle idle0)\n'+block+'\nexit "$status"\n'
            p=subprocess.run(['bash','-c',script],env=dict(self.env,BAD_SCENARIO=scenario),capture_output=True,text=True)
            with self.subTest(scenario=scenario):self.assertEqual(p.returncode,0 if scenario=='none' else 1,p.stdout+p.stderr)

    def test_full_regression_simulator_error(self):
        vectors=os.environ.get('REGRESSION_VECTORS')
        if not vectors:self.skipTest('set REGRESSION_VECTORS to a complete saved matrix')
        self.tool('vvp',"print('output I Test PASS.');print('output Q Test PASS.');raise SystemExit(42)\n")
        self.reject(['bash','scripts/validation/run_rx_regression.sh','injected-regression-error'])
        result=(self.repo/'results/validation/injected-regression-error/rx_regression/result.txt').read_text()
        self.assertIn('PASS=0',result)
        errors=int(re.search(r'ERROR=(\d+)',result).group(1))
        missing=int(re.search(r'NO_STIMULUS=(\d+)',result).group(1))
        self.assertGreater(errors,0)
        self.assertEqual(errors+missing,270)


    def test_stale_outputs_do_not_satisfy_regression(self):
        vectors=os.environ.get('REGRESSION_VECTORS')
        if not vectors:self.skipTest('set REGRESSION_VECTORS to a complete saved matrix')
        copied=self.work/'stale-vectors'
        shutil.copytree(vectors,copied)
        # Deliberately seed old, correct-looking results alongside the inputs.
        for ref in copied.rglob('*_ref.txt'):
            shutil.copy2(ref,ref.with_name(ref.name.replace('_ref.txt','.txt')))
        markers=['output bit Test PASS.','output signal for decision Test PASS.',
                 'Test PASS.','0 difference found','output I Test PASS.','output Q Test PASS.',
                 'output tx I Test PASS.','output tx Q Test PASS.','rx CRC Test PASS.',
                 'rx PDU Test PASS.','TEST FINISH.','VERIFIED_REJECTION: injected stale output test']
        self.tool('vvp','print('+repr('\n'.join(markers))+')\n')
        previous=self.env.get('REGRESSION_VECTORS')
        try:
            self.env['REGRESSION_VECTORS']=str(copied)
            self.reject(['bash','scripts/validation/run_rx_regression.sh','injected-stale-outputs','master'])
        finally:
            if previous is None:self.env.pop('REGRESSION_VECTORS',None)
            else:self.env['REGRESSION_VECTORS']=previous
        result=(self.repo/'results/validation/injected-stale-outputs/rx_regression/result.txt').read_text()
        self.assertIn('PASS=0',result)



if __name__=='__main__':unittest.main()
