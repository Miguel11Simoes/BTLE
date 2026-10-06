> **Later revision:** [RF interface and measurement audit](RF_INTERFACE_REVIEW.md) records the current RF-valid correction, rerun matrices and stricter PPA evidence checks. This document records the preceding packet-validation campaign.

Latest controller lint and revalidation: [LINT_CLOSURE.md](LINT_CLOSURE.md).

# Product validation - 2026-10-05

**Digital verification passed the campaigns below. ASIC/product readiness: NOT READY.** See [ASIC_READINESS.md](ASIC_READINESS.md) for unresolved work. This report replaces the current-status claims in earlier regression summaries; historical files remain available as evidence of the failures that were found.

## What was corrected

The runners require a successful tool exit, a complete explicit verdict, real stimulus and complete known outputs. Two failures or two empty verdicts never count as a pass. A stale output in the saved input directory is not copied into a simulation run. Rejection tests require an explicit rejection result and independently expected CRC failure with an empty accepted PDU; an absent RX input is still an error. Mutation tests require a concrete failing assertion and evidence that the intended engine ran.

These stricter checks exposed real defects. The RX model now rejects truncated declared PDUs and validates CRC at the declared boundary; it no longer exports repeated fake decisions or returns a rejected PDU. TX now emits the complete 16-sample Gaussian tail with the correct last marker, including coefficient changes on the FIR clock. Bit repetition restarts per bit, so arbitrary gaps between packets cannot lose completion. Channel 0 and CRC seed 0 are honored. Reserved register/event reads are known zero. Controller tests require actual TX/RX completion, qualified known outputs and correct acceptance/rejection of complete packets with deliberately valid/invalid CRCs.

On `ble-tx-pdu-we`, the SRAM tools also reject empty/incomplete/duplicate/impossible counts and invalid numeric characterization. Missing macro characterization makes the energy summary fail, while retaining explicitly incomplete diagnostic tables. Characterization requires a nonempty unique macro list, matching positive periods and finite physical measurements. Signed deselected-clock energy relative to static leakage is retained as a diagnostic; access energy is measured relative to the deselected clock.

## Reference and evidence

The reference is **corrected master**, commit `6589489b71704d0ff5d8eae499a6522ade0ac680`, not the unmodified upstream circuit. The tail, zero channel/seed and completion fixes intentionally change upstream behavior. Waveform/PDU checks against the independent Python model supplement branch-to-reference equality.

Tests ran on isolated working trees before their final commits. The `dut` SHA in an old run's provenance identifies its base commit, not the complete tested source. Each matrix includes exact RTL hashes and the runner hash; `results/validation/product-evidence-20261005/source_sha256.json` binds the final source files. Before integration these hashes were checked against the saved runs. One-port model hashes were regenerated from the committed test helpers and checked separately.

Each branch contains:

- `results/validation/product-evidence-20261005/`: cross-branch summary, exact source hashes, tools, focused checks and the common input archive.
- The matrix directories listed in `branch_summary.json`: `summary.tsv`, `result.txt`, `provenance.json` and `logs.tar.gz` (raw logs, output hashes, vector hashes and compilation logs).
- `product-mutations-final` (or `product-mutations-strobe`), and `product-structure-final` under `results/validation/`.
- Where supported, `product-controller-audited` or `product-controller-strobe`: controller lockstep statistics and concrete mutation witnesses.

The 54 input configurations use three examples, SNR 20/12/8, clock offsets 0/20/50 ppm and delays 0/5. The 270 original full RX I/Q, TX input and full golden TX I/Q files were verified byte-identical to the previous saved stimuli. Only invalid RX reference/export handling was repaired. `unchanged_stimuli.json` records that comparison. Input archive SHA-256: `10c5cff448797924a8c94e2d33ce76da0ea10d5e65edc915a3b1920b93a95349`.

## Results

Every 270-case matrix contains **210 data comparisons and 60 explicitly verified packet rejections**. Each has zero BOTH_FAIL, NO_STIMULUS, DIFFERENT and ERROR cases. Rejections are checks that invalid traffic is rejected; they are not successfully decoded packets.

| Branch | RTL matrix | One-port matrix | Full TX/model checks | Harness checks passed / skipped | Lint diagnostics |
|---|---:|---:|---:|---:|---:|
| `ble-opt` | 270/270 | not run | 167 | 23 / 0 | 160 |
| `ble-rx-dm` | 270/270 | not run | 167 | 23 / 0 | 149 |
| `ble-tx-1--8` | 270/270 | 270/270 | 167 + 16 | 19 / 4 | 150 |
| `ble-tx-fir2` | 270/270 | not run | 167 | 18 / 5 | 146 |
| `ble-tx-opt` | 270/270 | not run | 167 | 23 / 0 | 150 |
| `ble-tx-sin2` | 270/270 | 270/270 | 167 + 16 | 19 / 4 | 146 |
| `ble-tx-sin4` | 270/270 | not run | 167 | 19 / 4 | 145 |
| `ble-tx-sin8` | 270/270 | not run | 167 | 19 / 4 | 146 |
| `ble-tx-sin8-1rw` | 270/270 | 270/270 | 167 + 16 | 19 / 4 | 146 |
| `ble-tx-table` | 270/270 | not run | 167 | 23 / 0 | 149 |
| `ble-tx-table-reg` | 270/270 | not run | 167 | 22 / 1 | 150 |
| `ble-tx-table-sram` | 270/270 | not run | 167 | 22 / 1 | 149 |
| `master` | 270/270 | not run | 167 | 18 / 5 | 145 |
| `risc-v-ble` | 270/270 | not run | 167 | 18 / 5 | 145 |
| `ble-tx-pdu` | 270/270 | 270/270 | 167 + 16 | 23 / 0 | 154 |
| `ble-tx-pdu-we` | 270/270 | 270/270 | 167 + 16 | 27 / 0 | 154 |

- **5,670/5,670 matrix cases:** 4,320 across the 16 normal configurations, plus 1,350 across five one-port configurations. Total: 4,410 data comparisons and 1,260 verified rejections.
- **2,752/2,752 TX checks:** 167 per branch, plus 16 in each of the five one-port configurations. Each checks the complete waveform and independent Python decoding. The 167 cases cover all 40 channels, payloads 0/1/8/31 bytes, advertising payloads of 37 bytes on channels 37-39 and additional CRC seeds including zero.
- **501/501 actual TX-to-RTL-RX packet checks:** 167 each on `ble-tx-sin4`, `ble-tx-pdu` and `ble-tx-pdu-we`. These overlap the TX coverage and are not added to it as independent extra packet scenarios.
- **335 harness test methods passed; 37 explicitly skipped** because the corresponding branch has no such runner. No skipped method is counted as passed. The SRAM suite includes 13 invalid-count/energy subcases and 10 invalid-characterization subcases, plus positive evidence.
- All 16 branches passed focused RX-model, Gaussian-tail, bit-repeat and reserved-register checks. The model checks include 160 valid packets, 2,432 truncations and 104 corruptions; Gaussian-tail checks compare 1,040 samples with changing signed coefficients; bit-repeat checks cover 64 packets/2,024 samples with varying gaps. The old bit-repeat implementation fails the saved reproduction.
- **64/64 deliberate product defects detected** across the 16 branches (four each), with successful non-mutated baselines. A tool crash is not counted as detection.
- Controller lockstep: **42/42 runs**, 252 TX completions and 252 RX completions across seven branches; **34/34 controller mutations detected**. Each run includes both valid and deliberately invalid complete packets. `ble-tx-pdu-we` also exercises register and baremetal write strobes.
- Packet-buffer stress: `ble-tx-pdu` **24/24 runs, 11/11 mutations**; `ble-tx-pdu-we` **48/48 runs, 13/13 mutations**, covering write-strobe settings 0 and 1. Six clock relationships and both RAM models are exercised; resets intentionally abort some started packets. These are lockstep tests, not independent protocol proof for maximum-length packets.
- **Yosys structural checks: 16/16 passed. Strict Verilator lint: 16/16 failed**, with 145-160 diagnostics per branch. Both exit codes and all diagnostics are retained. Structural elaboration is not mapped timing, CDC/RDC, formal equivalence or physical signoff.

Normal runs use the branch's intended configuration: `GAUSS_TABLE=1` on the table/opt/PDU branches; `PDU_WRITE_STROBE=1` additionally on `ble-tx-pdu-we`. Other parameters retain their defaults. The latter branch's final normal matrix is `product-strobe-audited`; its TX check is `product-strobe-final/tx_packets.json`, and its one-port matrix is `product-strobe-final-one-port`. The earlier normal compilation failure is excluded, not reclassified as a pass. All other branches use `product-final-20261005` and, where present, `product-final-20261005-one-port`.

## Reproduction (Linux/WSL)

Use Python 3.11 with NumPy 2.4.6 and the compiler/runtime versions in `tool_versions.txt`. Set `PY` to that Python interpreter and put Icarus and Yosys in PATH. Run from the selected branch root. Choose a new output label: existing campaign evidence is not overwritten.

```bash
mkdir -p /tmp/btle-product-vectors
tar -xzf results/validation/product-evidence-20261005/vectors.tar.gz -C /tmp/btle-product-vectors
export REGRESSION_VECTORS=/tmp/btle-product-vectors/vectors
export REGRESSION_JOBS=3
# Table/opt/PDU branches:
# export DUT_DEFAULTS='gauss_filter.v:GAUSS_TABLE=1'
# ble-tx-pdu-we instead:
# export DUT_DEFAULTS='gauss_filter.v:GAUSS_TABLE=1 btle_tx.v:PDU_WRITE_STROBE=1 btle_controller.v:PDU_WRITE_STROBE=1'
bash scripts/validation/run_rx_regression.sh my-product-check 6589489b71704d0ff5d8eae499a6522ade0ac680
"$PY" tests/test_tx_packet.py --rtl-rx --output /tmp/tx-packets.json
"$PY" -m unittest discover -s tests -p 'test_validation*.py' -v
"$PY" tests/test_rx_model.py
"$PY" tests/test_gauss_tail.py
"$PY" tests/test_upsample.py
"$PY" tests/test_control_readback.py
"$PY" tests/test_product_mutations.py --output results/validation/my-product-mutations
# Branches with controller lockstep:
bash scripts/validation/ctl_lockstep/run_ctl_lockstep.sh my-controller-check 2 6 6589489b71704d0ff5d8eae499a6522ade0ac680
# PDU branches:
"$PY" tests/test_tx_pdu.py --seeds 2 --packets 6 --jobs 3 --mutants --ref-rev 6589489b71704d0ff5d8eae499a6522ade0ac680
```

For a one-port run, use a separate disposable checkout and the relevant `tests/test_vco_*.py --write-one-port verilog/vco.v` helper; PDU branches additionally use `tests/test_tx_pdu.py --write-one-port verilog/btle_tx.v`. Then run the same matrix and `test_tx_packet.py --quick`. These are behavioral one-port models, not characterized foundry SRAMs.

The independent packet model covers legacy-shaped LE 1M formats, not the complete modern Bluetooth feature set. Existing branch restrictions on table programming, input sample rate and packet-buffer updates still apply. Previously published area/timing/activity/energy figures belong to earlier RTL; the changes here require new measurements. No PDK has been selected, no tapeout signoff has been completed, and no claim of zero remaining defects or maximum possible optimization is made.
