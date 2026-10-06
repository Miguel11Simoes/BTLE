# RF interface and measurement audit - 2026-10-05

**Historical report, superseded for current lint/RTL by [LINT_CLOSURE.md](LINT_CLOSURE.md).**

**Digital campaigns recorded here: passed. ASIC/market release: NOT READY.** This report is the latest continuation of [PRODUCT_VALIDATION.md](PRODUCT_VALIDATION.md). It adds a real RF-valid correction and rejects incomplete measurement evidence. The previous report and its logs remain historical evidence; do not substitute their old source hashes for this revision.

## RF-valid defect and correction

`clock_domain_conversion_iq` used to generate a receive-valid pulse every second baseband cycle even when `rx_iq_valid_ext` was zero. The supported 2:1 sampling phase now has its own register and the output-valid pulse is qualified by the external valid signal. Gaps no longer create phantom samples or reset/shift the sample phase. Continuous valid input retains its previous timing.

The independent interface contract test uses four clock phases and three source patterns: no valid data, continuous data and repeated gaps. It checks the valid schedule and I/Q values, includes an intervening reset and requires positive coverage. Before the repair: **4 continuous scenarios passed, 8 quiet/gapped scenarios failed**. After the repair: **12/12 passed**. Both deliberate defects (ignoring valid and deriving phase from the gated output) are detected. All 16 branches share this module and were tested separately: **192/192 scenarios and 32/32 detected mutants**.

This is a correction under the documented related 2:1 clock contract. It does not synchronize an arbitrary asynchronous multibit interface, replace CDC/RDC analysis, or establish a physical timing margin.

## Measurements must fail on missing evidence

The audit reproduced five formerly successful commands that had invalid inputs: an empty sequential-cell list, a cell absent from the timing library, an empty SAIF file, a missing standard-cell area, and an OpenRAM macro with zero width. **All five returned exit 0 before the correction and exit 1 afterward.** The paired logs and input descriptions are in `ble-opt:results/validation/measurement-guards-final/`.

The repaired tools now require:

- Timing: an explicit nonempty cell list, existing cells, clock-to-Q and setup tables, finite values and supported time units. Falling-edge flops are handled; library units are converted to ns.
- Standard-cell area: complete numeric statistics, matching selected top and per-type counts, and a positive area when standard cells exist.
- OpenRAM area: positive finite dimensions, matching memory geometry and masks, unique macros, and every requested macro present.
- Activity: nonempty setup/run SAIF data, covered nets on both sides of the subtraction, nondecreasing counters, recognized cells/pins and finite capacitances with explicit units. Incomplete reports have status `INCOMPLETE` and fail.
- Activity summaries/comparisons: explicit complete evidence, valid process exit codes, consistent scenarios/windows and valid metrics. A partial activity JSON cannot become a successful summary.

The measurement suite passed **50 test methods across 11 applicable branches**; **16 methods were explicitly skipped** where that branch has no corresponding measurement tool. Positive controls include a real Nangate45 library and a real `crc24` synthesis. These smoke checks validate the reporting path; they do not remeasure the complete transmitter.

Saved activity runs inspected during this audit contained **12 missing entries per side**. The old tool skipped these entries. Their meaning/aliasing must be resolved before those reports can be considered complete; the new tools will reject such incomplete coverage. No blanket exclusion was added to make these reports pass.

## Revalidation on the corrected RTL

Reference: corrected master `5abbbf7a093b48a64f18c2c1f84057c54d0af0e5`. Every normal matrix and each of the five one-port configurations was rerun after the RF change. The archive in each branch binds exact RTL and runner hashes to the saved results.

| Branch | Normal matrix | One-port matrix | RF contract | Strict lint diagnostics |
|---|---:|---:|---:|---:|
| `ble-opt` | 270/270 | not run | 12/12 + 2 mutants | 159 |
| `ble-rx-dm` | 270/270 | not run | 12/12 + 2 mutants | 148 |
| `ble-tx-1--8` | 270/270 | 270/270 | 12/12 + 2 mutants | 149 |
| `ble-tx-fir2` | 270/270 | not run | 12/12 + 2 mutants | 145 |
| `ble-tx-opt` | 270/270 | not run | 12/12 + 2 mutants | 149 |
| `ble-tx-sin2` | 270/270 | 270/270 | 12/12 + 2 mutants | 145 |
| `ble-tx-sin4` | 270/270 | not run | 12/12 + 2 mutants | 144 |
| `ble-tx-sin8` | 270/270 | not run | 12/12 + 2 mutants | 145 |
| `ble-tx-sin8-1rw` | 270/270 | 270/270 | 12/12 + 2 mutants | 145 |
| `ble-tx-table` | 270/270 | not run | 12/12 + 2 mutants | 148 |
| `ble-tx-table-reg` | 270/270 | not run | 12/12 + 2 mutants | 149 |
| `ble-tx-table-sram` | 270/270 | not run | 12/12 + 2 mutants | 148 |
| `master` | 270/270 | not run | 12/12 + 2 mutants | 144 |
| `risc-v-ble` | 270/270 | not run | 12/12 + 2 mutants | 144 |
| `ble-tx-pdu` | 270/270 | 270/270 | 12/12 + 2 mutants | 153 |
| `ble-tx-pdu-we` | 270/270 | 270/270 | 12/12 + 2 mutants | 153 |

- **5,670/5,670 regression cases passed again:** 4,410 complete data comparisons and 1,260 explicit packet-rejection checks. No simulator error, missing-stimulus case or shared failure is counted as a pass.
- Controller lockstep rerun: **42/42 runs**, 252 TX completions, 252 RX completions and **34/34 mutations detected**, across seven branches.
- Common validation harness rerun: **335 methods passed, 37 skipped**; skips remain excluded from the pass count.
- Structural checks rerun: **16/16 Yosys checks passed; 16/16 strict Verilator lint runs failed**, with 144-159 diagnostics. The failed lint logs are retained.
- The previous **2,752 TX waveform/Python checks**, **501 TX-to-RTL-RX packet checks** and focused packet/tail/repetition/readback tests remain applicable to their unchanged RTL/Python/test sources. Source comparison confirmed that only `clock_domain_conversion_iq.v` changed among existing RTL and Python files; the affected system/controller campaigns above were rerun. Do not add overlapping checks or the repeated matrix to invent a larger independent coverage figure.

## Evidence and reproduction

Current per-branch evidence:

- `results/validation/rf-evidence-20261005/`: source hashes, artifact hashes, tool versions, harness logs and the common `branch_summary.json`.
- `results/validation/rf-final-20261005/rx_regression/` and, where applicable, `rf-final-20261005-one-port/rx_regression/`: summaries, provenance and full logs/output manifests in `logs.tar.gz`.
- `results/validation/rf-contract-final/`, `rf-controller-final/` where supported, and `rf-structure-final/`.
- `results/validation/measurement-guards-final/` on the 11 branches carrying measurement tools. The extra before/after measurement reproductions and real-tool smoke runs are on `ble-opt`.
- The old RF source and before/after test archives are in `ble-tx-sin4:results/validation/rf-evidence-20261005/`.

The source and artifact hashes are SHA-256 of canonical Git bytes (text files use LF). A Windows checkout may use CRLF; compare against `git show HEAD:<path>` or normalize only checkout line endings. Commits preserve the tested source content. Changes being made concurrently in another working tree are not part of this evidence unless their files and hashes are listed in the manifest.

Use the input archive, Python/tool setup and branch-specific `DUT_DEFAULTS` from [PRODUCT_VALIDATION.md](PRODUCT_VALIDATION.md), but use the current reference and a new result label:

```bash
bash scripts/validation/run_rx_regression.sh my-rf-check 5abbbf7a093b48a64f18c2c1f84057c54d0af0e5
"$PY" tests/test_clock_domain_contract.py --output results/validation/my-rf-contract --mutants
"$PY" -m unittest discover -s tests -p 'test_validation*.py' -v
# On branches carrying measurement tools:
"$PY" tests/test_measurement_evidence.py
# On branches carrying controller lockstep:
bash scripts/validation/ctl_lockstep/run_ctl_lockstep.sh my-rf-controller 2 6 5abbbf7a093b48a64f18c2c1f84057c54d0af0e5
```

Remaining work is listed in [ASIC_READINESS.md](ASIC_READINESS.md): product/technology choices, lint closure, CDC/RDC and interface timing, state recovery, complete selected-protocol coverage, current physical/PPA/DFT evidence and qualification. All earlier whole-chip PPA/activity figures remain historical. **These passing digital campaigns do not establish zero defects, maximum optimization or readiness for tapeout.**
