> **Status update, 2026-10-05:** the corrected RTL and strict results are documented in [PRODUCT_VALIDATION.md](PRODUCT_VALIDATION.md) and [ASIC_READINESS.md](ASIC_READINESS.md). This document preserves historical implementation/measurement results. Its PPA values do not describe the corrected circuit; earlier equality/PASS claims are not product signoff.

# Validation integrity audit ? 2026-10-04

The upstream regression is **FAIL on every branch**, including `master`.
Identical failures, missing stimuli, empty verdicts, unknown outputs and incomplete
output files are not successful checks. The hardware was not changed by this fix.

## Scope and result

All 14 local branches carry the strict regression and verdict guards. Existing
VCO, controller/RX/table lockstep, mutation, formal, power, area and timing runners
were hardened where present. The new `ble-tx-1--8` branch is included.
There are 17 real upstream campaigns: one per branch, plus one-port memory models
on `ble-tx-sin2`, `ble-tx-sin8-1rw` and `ble-tx-1--8`.
The same 54 saved vector sets are used everywhere (3 examples ? 3 SNR values
20/12/8 dB ? 3 clock errors 0/20/50 ppm ? 2 delays 0/5), with 5 benches per set.

| Result | Per campaign | All 17 campaigns |
|---|---:|---:|
| Verified PASS | 118 | 2,006 |
| BOTH_FAIL, reference and DUT fail their checks | 20 | 340 |
| NO_STIMULUS, not simulated | 18 | 306 |
| ERROR: OUTPUT_COUNT, incomplete output/reference comparison | 96 | 1,632 |
| ERROR: UNKNOWN_OUTPUT, X/Z data | 18 | 306 |
| DIFFERENT between reference and DUT | 0 | 0 |
| Total attempted checks | 270 | 4,590 |

Every campaign returns exit **1** and writes `RESULT: FAIL`.
Zero differences does not make failed or unperformed checks pass. Counts use the
first failing condition per check; a controller case can have several problems.

| Bench | PASS | BOTH_FAIL | NO_STIMULUS | ERROR |
|---|---:|---:|---:|---:|
| Demodulator | 39 | 0 | 9 | 6 |
| RX core | 45 | 0 | 9 | 0 |
| RX | 34 | 10 | 0 | 10 |
| TX | 0 | 0 | 0 | 54 |
| Controller | 0 | 10 | 0 | 44 |

The errors also occur in upstream. They disprove the claimed complete validation;
they do not demonstrate a new optimization-specific RTL defect. Resolving the
Python/RTL output-length contract or receive errors is separate from making the
verdict truthful. No vectors were removed or shortened to turn these results green.

## False-PASS paths closed

- Simulator errors, timeouts, absent executables and partial verdicts cannot pass,
  even after a PASS message. Every sub-check and output file is required;
  failure diagnostics override PASS. Missing or empty input files are checked
  before simulation. Empty verdict pairs never pass; shared failures are BOTH_FAIL.
- Outputs must be nonempty and contain known data. Numerical checks against the
  Python reference cover every expected value and enforce output counts.
  Demodulation uses the bench's explicit one-sample offset. RX-core octets use
  the checked PDU prefix (CRC is checked separately); its raw bit dump is compared
  between implementations, not confused with Python's decoded PDU bits.
- TX uses `!=` on array entries beyond recorded data; X makes that condition
  unknown, which does not enter the error branch. For example, `ex0_snr20_ppm0_d0`
  records 2,688 I and Q samples against 2,704 expected and prints PASS. The strict
  runner reports OUTPUT_COUNT. Both TX and controller exhibit this problem.
- Six demodulator cases lack the final comparison sample after the offset. RX
  `ex1_snr12_ppm50_d0` dumps 2 octets against 14 expected and prints PASS.
  These incomplete comparisons are now OUTPUT_COUNT errors.
- Nine RX and nine controller cases dump unknown PDU data. CRC/reference indicates
  failed decoding and the PDU reference is empty; the previous zero-iteration
  PDU check was vacuous. They are not complete PDU validations.
- Mutations require a concrete mismatch assertion and the expected process exit.
  Crashes, missing stimuli and stimulus/queue-contract errors are not caught
  mutants. Campaign sizes must be positive.
- Formal runs require agreement between exit and proof status. FIR2 keeps its
  qualified UNKNOWN-plus-concrete-simulation-mismatch result; UNKNOWN is not a
  failed proof. Equivalence requires nonempty proved cells and successful exit.
- Every parallel activity child, including setup, has its exit checked. Missing
  scenarios, empty windows and absent exit evidence cannot produce successful
  aggregates. Area/timing summaries require measured outputs; required OpenRAM
  artifact copy failures propagate.

## Historical correction

**288 proven false SAME_PASS records caused by absent/empty stimuli** occur across
**13 distinct historical regressions** (17 stored copies across branches).
This expands the initial 43 empty-verdict finding: some benches printed PASS
without exercising input. Duplicate copies are not counted twice.

Legacy summaries retain `legacy_result`, original summary SHA-256 and raw logs.
Their current result is `LEGACY_UNVERIFIED`. Even apparently matching old checks
are `MATCH_UNVERIFIED_EXIT`, because process exits were not recorded. This audit
is not a historical rerun. The 288 is a lower bound: old evidence does not allow
all new output-count/X checks to be reconstructed.

| Legacy campaign | False SAME_PASS: no stimulus | Shared failures | Matches with unverified exit |
|---|---:|---:|---:|
| `shared-demod` | 22 | 16 | 232 |
| `sticker-defaults` | 24 | 21 | 225 |
| `tx-1--8` | 22 | 21 | 227 |
| `tx-1--8-one-port` | 26 | 28 | 216 |
| `tx-fir2` | 26 | 15 | 229 |
| `tx-opt` | 16 | 24 | 230 |
| `tx-sin2` | 16 | 20 | 234 |
| `tx-sin2-one-port` | 26 | 13 | 231 |
| `tx-sin8-1rw` | 20 | 20 | 230 |
| `tx-sin8-1rw-one-port` | 24 | 21 | 225 |
| `tx-table` | 20 | 17 | 233 |
| `tx-table-reg` | 24 | 17 | 229 |
| `tx-table-sram` | 22 | 19 | 229 |

## Verification of the fixes

- Adversarial tests pass on all 14 branches: 15 common verdict tests plus applicable
  entrypoint tests. Inapplicable tests are explicitly skipped. Cases include real
  subprocess errors/timeouts, exit 42 after PASS, empty/partial verdicts, zero-size
  campaigns, missing/unknown/truncated outputs, formal status/exit conflicts,
  mutation infrastructure failures and failures of individual activity processes.
  The full regression also runs with a deliberately failing simulator on `master`;
  no row becomes PASS.
- 16 real simulator/formal commands pass: VCO suites on sin4, sin8, sin8-1rw, sin2
  and 1--8; controller lockstep on four implementations; table random lockstep on
  reg/SRAM; RX lockstep; Gaussian, demodulator and FIR2 formal/mutation flows;
  and Gaussian default equivalence. Random VCO suites use the full default
  4 ? 1,000,000 cycles; mutants are 7/7, 11/11, 11/11 and 14/14 respectively.
  Controller campaigns use 1 seed ? 3 examples ? 6 packets, RX uses 1 seed ?
  3 examples ? 20 segments, and each table campaign uses 1 seed ? 200 sets ?
  5,000 samples. FIR2 uses its full 4 ? 2,000,000-cycle random campaign.
- A VCO area flow and a complete controller timing flow also finish successfully.
  Shell syntax and Python compilation are checked for every distinct source.
- A complete new gate-level activity/PPA campaign was not run. Failure propagation
  was tested at the actual parallel execution block with injected child processes.
  Old PPA and gate-level results are not claimed as newly revalidated. OpenRAM
  synthesis was not repeated.

A first sin8-1rw VCO attempt encountered the temporary one-port model of a parallel
regression and correctly failed preflight. It was repeated successfully after the
regression restored RTL. Both logs and the reason are preserved; the rejected
attempt is not counted as successful validation.

## Evidence and reproduction

`results/validation/strict-20261004-checked/rx_regression/` contains the 270-row
summary, exits, compressed logs, input/output hashes, raw failed/error outputs,
RTL hashes and provenance. Three extra campaigns use
`strict-20261004-checked-one-port`. The common ledgers, real-suite exit records,
this branch's fault-injection log, source hashes and `vectors.tar.gz` are under
`results/validation/integrity-20261004/`. Positive-suite logs are on their respective
branches, identified in the common ledger. Detailed positive-suite evidence is
under `results/validation/strict-guards-final/` where applicable.

The bundled upstream controller bench has U9's declaration-order fix for Icarus.
Only VCD dumping is disabled in temporary bench copies. Circuit, Python generator
and vector values are unchanged. On WSL/Linux with the project's OSS CAD Suite,
NumPy and Python dependencies:

```sh
python3 -m unittest discover -s tests -p 'test_validation*.py' -v
mkdir -p /tmp/btle-audited-vectors
tar -xzf results/validation/integrity-20261004/vectors.tar.gz -C /tmp/btle-audited-vectors
REGRESSION_VECTORS=/tmp/btle-audited-vectors/vectors bash scripts/validation/run_rx_regression.sh my-strict-run
```

For `ble-tx-table`, `ble-tx-table-reg`, `ble-tx-table-sram` and `ble-tx-opt`, also
set `DUT_DEFAULTS="gauss_filter.v:GAUSS_TABLE=1"`, as recorded in provenance.
Use a fresh label: earlier runs are never overwritten. Expected regression exit
is 1 for this matrix. Standalone upstream `Test PASS` messages are sub-checks,
not the strict runner's final verdict. These tests bound the verified scope;
they do not prove that no undiscovered bug can exist.

Saved vector archive SHA-256: `a49d85a18713cb9d23c531fd2e04c976b6b42fb6a053d45f24af74e2596668a5`.
