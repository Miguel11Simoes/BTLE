"""Reclassify legacy records without inventing missing process-exit evidence.

Raw logs/provenance remain historical evidence. The original CSV verdict is kept
in legacy_result. Reclassification is idempotent; it is NOT a new simulation.
"""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys

INPUTS = {
    'gfsk_demodulation_tb': ['btle_rx_gfsk_demodulation_test_input_i.txt','btle_rx_gfsk_demodulation_test_input_q.txt'],
    'btle_rx_core_tb': ['btle_rx_btle_rx_core_test_input_i.txt','btle_rx_btle_rx_core_test_input_q.txt'],
    'btle_rx_tb': ['btle_rx_test_input_i.txt','btle_rx_test_input_q.txt'],
    'btle_tx_tb': ['btle_tx_test_input.txt'],
    'btle_controller_tb': ['btle_rx_test_input_i.txt','btle_rx_test_input_q.txt','btle_tx_test_input.txt'],
}
EMPTY = hashlib.sha256(b'').hexdigest()


def audit(summary):
    raw = summary.read_bytes()
    with summary.open(newline='') as f:
        reader = csv.DictReader(f, delimiter='\t'); fields = reader.fieldnames; rows = list(reader)
    if 'ref_verdict' not in fields or 'legacy_result' in fields:
        return None
    for row in rows:
        old = row['result']; row['legacy_result'] = old
        source = summary.parent / ('vectors_' + row['config'] + '.sha256')
        hashes = dict((line.split()[-1],line.split()[0]) for line in source.read_text().splitlines()) if source.exists() else None
        missing = [name for name in INPUTS[row['testbench']] if name not in hashes or hashes[name] == EMPTY] if hashes is not None else []
        if missing:
            row['result'] = 'NO_STIMULUS'
        elif not row['ref_verdict'].strip() or not row['dut_verdict'].strip():
            row['result'] = 'INCOMPLETE_VERDICT'
        elif old == 'SAME_BOTH_FAIL':
            row['result'] = 'BOTH_FAIL'
        elif old == 'SAME_PASS' and row['ref_verdict'] == row['dut_verdict'] and row['outputs'] == 'yes':
            row['result'] = 'MATCH_UNVERIFIED_EXIT'
        else:
            row['result'] = 'DIFFERENT' if old == 'DIFFERENT' else 'UNVERIFIED'
    with summary.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields+['legacy_result'],delimiter='\t');writer.writeheader();writer.writerows(rows)
    counts=Counter(row['result'] for row in rows)
    evidence=dict(original_summary_sha256=hashlib.sha256(raw).hexdigest(), records=len(rows),counts=dict(counts),
                  prior_false_pass_no_stimulus=sum(r['legacy_result']=='SAME_PASS' and r['result'] in {'NO_STIMULUS','INCOMPLETE_VERDICT'} for r in rows),
                  note='Historical reclassification only. Process exit codes were not recorded; no legacy row is promoted to a verified PASS.')
    (summary.parent/'integrity_audit.json').write_text(json.dumps(evidence,indent=2)+'\n')
    (summary.parent/'result.txt').write_text('Historical records reclassified; no new simulation.\n'+' '.join(f'{k}={v}' for k,v in sorted(counts.items()))+'\nRESULT: LEGACY_UNVERIFIED (use the strict-20261004-checked regression)\n')
    return evidence


def main():
    root=Path(sys.argv[1] if len(sys.argv)>1 else Path(__file__).resolve().parents[2])
    for path in sorted((root/'results/validation').glob('*/rx_regression/summary.tsv')):
        result=audit(path)
        if result:print(path.parent.parent.name,json.dumps(result['counts']))


if __name__=='__main__':main()
