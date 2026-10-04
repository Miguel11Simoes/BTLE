"""Adversarial tests for validation infrastructure, including simulator failures."""
import importlib.util
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/validation'))
import result_guard as guard
import rx_regression as rx


class VerdictTests(unittest.TestCase):
    def test_exit_zero_alone_is_not_success(self):
        for log in ('', 'finished', 'NO INPUT!', 'NOT INPUT!', 'FATAL: missing file'):
            with self.subTest(log=log):
                self.assertNotEqual(rx.classify(0, log, 'btle_tx_tb'), 'PASS')

    def test_complete_tx(self):
        self.assertEqual(rx.classify(0, '0 error found! output I Test PASS.\n0 error found! output Q Test PASS.', 'btle_tx_tb'), 'PASS')

    def test_partial_tx(self):
        self.assertEqual(rx.classify(0, '0 error found! output I Test PASS.', 'btle_tx_tb'), 'INCOMPLETE')

    def test_partial_controller(self):
        log = '\n'.join(rx.MARKERS['btle_controller_tb'][:-1])
        self.assertEqual(rx.classify(0, log, 'btle_controller_tb'), 'INCOMPLETE')

    def test_failure_after_pass(self):
        for fault in ('Test FAIL.', '1 difference found', '10 error found!', 'FATAL: stopped', 'ERROR: file missing'):
            with self.subTest(fault=fault):
                self.assertEqual(rx.classify(0, '\n'.join(rx.MARKERS['btle_tx_tb'])+'\n'+fault, 'btle_tx_tb'), 'FAIL')

    def test_bad_exit_even_with_complete_verdict(self):
        for code in (1, 42, 124, 127, -11):
            with self.subTest(code=code):
                self.assertNotEqual(rx.classify(code, '\n'.join(rx.MARKERS['btle_tx_tb']), 'btle_tx_tb'), 'PASS')

    def test_pair_fail_closed(self):
        for status in ('FAIL', 'ERROR', 'TIMEOUT', 'INCOMPLETE', 'NO_STIMULUS', 'MISSING_OUTPUT', 'UNKNOWN_OUTPUT'):
            with self.subTest(status=status):
                self.assertNotEqual(rx.pair_verdict(status, status, True), 'PASS')
        self.assertEqual(rx.pair_verdict('PASS', 'PASS', False), 'DIFFERENT')
        self.assertEqual(rx.pair_verdict('PASS', 'FAIL', True), 'DIFFERENT')
        self.assertEqual(rx.pair_verdict('PASS', 'PASS', True), 'PASS')

    def test_matrix_never_passes_with_missing_or_failed_rows(self):
        for counts in ({}, {'PASS':269}, {'PASS':269,'NO_STIMULUS':1}, {'PASS':269,'BOTH_FAIL':1}, {'PASS':269,'ERROR':1}, {'PASS':269,'DIFFERENT':1}):
            with self.subTest(counts=counts):
                self.assertNotEqual(rx.final_status(counts,270)[1],0)
        self.assertEqual(rx.final_status({'PASS':270},270),('PASS',0))

    def test_normal_guard(self):
        self.assertTrue(guard.sim_pass(0,'CTL LOCKSTEP PASS\n','CTL LOCKSTEP PASS'))
        for code,log in [(42,'CTL LOCKSTEP PASS'),(0,''),(0,'CTL LOCKSTEP PASS\nMISMATCH outputs'),(0,'NOT CTL LOCKSTEP PASS')]:
            with self.subTest(code=code,log=log):
                self.assertFalse(guard.sim_pass(code,log,'CTL LOCKSTEP PASS'))

    def test_mutation_requires_concrete_assertion(self):
        self.assertTrue(guard.mutant_caught(1,'MISMATCH outputs at cycle 10\nFATAL: test'))
        self.assertTrue(guard.mutant_caught(1,'FAIL macro at clock 10: I/Q differs'))
        for code,log in [(0,''),(1,''),(42,'MISMATCH outputs'),(124,'MISMATCH outputs'),(1,'FATAL: missing vectors'),(0,'PASS'),(1,'FAIL random seed 1 clock 9: the reference queue overflows')]:
            with self.subTest(code=code,log=log):
                self.assertFalse(guard.mutant_caught(code,log))

    def test_empty_campaign_rejected(self):
        for value in ('0','-1','abc'):
            with self.subTest(value=value):
                with self.assertRaises((ValueError, argparse.ArgumentTypeError)):
                    guard.positive(value)

    def test_outputs_must_exist_and_be_known(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);p=d/'sample.txt'
            self.assertEqual(rx.output_problem(d,['sample.txt']),'MISSING_OUTPUT')
            p.write_text('xx\n')
            self.assertEqual(rx.output_problem(d,['sample.txt']),'UNKNOWN_OUTPUT')
            p.write_text('z\n')
            self.assertEqual(rx.output_problem(d,['sample.txt']),'UNKNOWN_OUTPUT')
            p.write_text('')
            (d/'sample_ref.txt').write_text('1\n')
            self.assertEqual(rx.output_problem(d,['sample.txt']),'MISSING_OUTPUT')
            p.write_text('1\n')
            self.assertIsNone(rx.output_problem(d,['sample.txt']))
            (d/'sample_ref.txt').write_text('')
            self.assertEqual(rx.output_problem(d,['sample.txt']),'EMPTY_REFERENCE')
            (d/'sample_ref.txt').write_text('1\n2\n')
            self.assertEqual(rx.output_problem(d,['sample.txt']),'OUTPUT_COUNT')
            p.write_text('2\n1\n')
            self.assertEqual(rx.output_problem(d,['sample.txt']),'FAIL')
            p.write_text('1\n2\n')
            self.assertIsNone(rx.output_problem(d,['sample.txt']))

    def test_documented_output_formats_and_truncation(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp)
            cases=[
                ('btle_rx_gfsk_demodulation_test_output_bit', '0 1 0', '1 0', None),
                ('btle_rx_gfsk_demodulation_test_output_bit', '0 1', '1 0', 'OUTPUT_COUNT'),
                ('btle_rx_btle_rx_core_test_output', 'ab cd 11 22 33', 'ab cd', None),
                ('btle_rx_btle_rx_core_test_output', 'ab', 'ab cd', 'OUTPUT_COUNT'),
                ('btle_tx_test_output_i', '50 71', '50 71 90', 'OUTPUT_COUNT'),
                ('btle_tx_test_output_i', '50 71 90', '50 71 90', None),
            ]
            for stem,actual,expected,problem in cases:
                with self.subTest(stem=stem,actual=actual):
                    (d/(stem+'.txt')).write_text(actual)
                    (d/(stem+'_ref.txt')).write_text(expected)
                    self.assertEqual(rx.output_problem(d,[stem+'.txt']),problem)

    def test_sby_exit_and_status_agree(self):
        with tempfile.TemporaryDirectory() as temp:
            status=Path(temp)/'status'
            for mode,code,word,expected in [('sby-pass',0,'PASS',0),('sby-pass',124,'PASS',1),('sby-pass',0,'',1),('sby-fail',2,'FAIL',0),('sby-fail',16,'FAIL',1),('sby-fail',2,'UNKNOWN',1)]:
                with self.subTest(mode=mode,code=code,word=word):
                    status.write_text(word)
                    p=subprocess.run([sys.executable,str(ROOT/'scripts/validation/result_guard.py'),mode,str(code),str(status)],capture_output=True)
                    self.assertEqual(p.returncode,expected)

    def test_real_process_crash_and_timeout(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);log=directory/'sim.log'
            for script,timeout,code in [("print('output I Test PASS.');print('output Q Test PASS.');raise SystemExit(42)",5,42),('import time;time.sleep(10)',0.05,124)]:
                with self.subTest(code=code):
                    actual=rx.run([sys.executable,'-c',script],directory,log,timeout)
                    self.assertEqual(actual,code)
                    self.assertNotEqual(rx.classify(actual,log.read_text(),'btle_tx_tb'),'PASS')


if __name__ == '__main__':
    unittest.main()
