# Controller lint closure and documentation paths - 2026-10-06

**Result: all 18 local branches pass the documented lint gate, with explicit exceptions. ASIC/tapeout readiness remains NOT READY.**

## Scope and changes

Documentation subfolders have no numeric prefix: `Architecture`, `Design Decisions`, `Validation`, `Guides`, and `Reference Manual`. Planned folder names in indexes are also unnumbered. Live references were updated, including URLs with encoded spaces. Historical evidence archives remain unchanged. The newer user commits adding SRAM measurements and the ROM/CORDIC branches were preserved; the three shared comparison/design documents remain identical across all 18 branches.

The lint target is the synthesizable native `btle_controller` hierarchy, at its documented default numeric widths and clocks. Every combination of the exposed Boolean architecture parameters is checked: `ENABLE_IQ_CAPTURE`, `LL_MINIMAL`, `GAUSS_TABLE`, and `PDU_WRITE_STROBE`, where present. This is **35 configurations**, not every possible numeric parameter value. FPGA vendor wrappers/Xilinx primitives and simulation testbenches are outside this ASIC controller lint target.

Corrections include explicit counter/constant widths and Boolean conditions, zero extension where intended, named optional diagnostic connections, dead undriven declarations removed, a three-octet RX packing register without its unused fourth byte, and simple constant UART parity selection. Unused compatibility/debug fields and reserved bit slices are marked explicitly; software readback and external ports remain compatible. Fixed VCOs explicitly ignore their programming ports. The CORDIC's unused final residual-angle update was removed; its output arithmetic is unchanged.

Previously unhandled LL, RX and three-state CRC encodings now recover to idle. RX/CRC valid/result strobes are cleared on that recovery. The one-bit CRC implementation in the four PDU-derived branches has no unused binary encoding. These are RTL recovery checks, not a physical fault-tolerance claim.

## Exact exceptions: a passing gate is not an exception-free source tree

`verilator --lint-only --Wall` runs with warnings fatal. There is no `-Wno-fatal` or global warning-category suppression. Two types of narrowly scoped source exception remain:

- **DECLFILENAME:** individual helper-module declarations bundled in an existing source file. This preserves the single-file interface consumed by existing synthesis and simulation scripts. The exception ends immediately after the declaration line; module bodies remain checked.
- **SYNCASYNCNET:** only the declaration of `s00_axi_aresetn`. AXI logic samples this reset synchronously while the legacy UART asserts it asynchronously. That established behavior is preserved and exercised by UART equivalence tests. **This exception does not establish safe reset release or CDC/RDC closure.** Clock/reset constraints and physical/domain verification remain open.

The exact per-branch inventory is `scripts/validation/lint_exceptions.json` (12-15 declaration entries, including bundled helpers behind preprocessor guards). `run_lint.py` rejects an unmatched, broadened or additional source directive, or any difference from that reviewed inventory. Intentional unused interface connections are visible as `unused_*` wires, restricted to the documented unused fields/bits. A new orphan signal still fails lint.

## Executed results

| Branch | Lint configurations passed | Complete regression cases passed | TX waveforms / Python loopbacks passed |
|---|---:|---:|---:|
| `ble-opt` | 8 | 270 | 167 |
| `ble-rx-dm` | 1 | 270 | 167 |
| `ble-tx-1--8` | 1 | 540 | 183 |
| `ble-tx-fir2` | 1 | 270 | 167 |
| `ble-tx-opt` | 2 | 270 | 167 |
| `ble-tx-sin2` | 1 | 540 | 183 |
| `ble-tx-sin4` | 1 | 270 | 167 |
| `ble-tx-sin8` | 1 | 270 | 167 |
| `ble-tx-sin8-1rw` | 1 | 540 | 183 |
| `ble-tx-table` | 2 | 270 | 167 |
| `ble-tx-table-reg` | 2 | 270 | 167 |
| `ble-tx-table-sram` | 2 | 270 | 167 |
| `master` | 1 | 270 | 167 |
| `risc-v-ble` | 1 | 270 | 167 |
| `ble-tx-pdu` | 2 | 540 | 183 |
| `ble-tx-pdu-we` | 4 | 540 | 183 |
| `ble-tx-rom` | 2 | 540 | 183 |
| `ble-tx-cordic` | 2 | 540 | 183 |

- **35/35 lint configurations passed**, with no unwaived warnings or errors.
- **6,750/6,750 complete regression cases:** 18 normal matrices and seven one-port matrices, each 270 cases. Coverage is 5,250 data comparisons and 1,500 explicit packet-rejection checks. No missing verdict, missing stimulus, process error, shared failure or skipped case counts as a pass.
- **3,118 TX waveform/Python loopback checks**; **835** of these additionally decoded through the RTL receiver. These are overlapping coverage figures, not counts to add together.
- **50 illegal-state recovery checks**; removing each recovery is rejected both by lint and by its concrete behavioral test.
- **172/172 negative-control executions rejected as required:** width errors, orphan signals, syntax errors, unreviewed lint suppression and removed recovery logic. Positive controls also ran. The gate additionally rejects diagnostics paired with exit zero and nonzero exits paired with empty output.
- **162 UART configurations, 6,480,000 compared cycles**, with 5-9 data bits as applicable, NONE/ODD/EVEN parity, positive TX/RX completion coverage and asynchronous resets during traffic. Outputs match each branch's pinned pre-lint implementation.
- **54 controller lockstep runs**, 324 TX and 324 RX completions, and **44/44 detected mutations**, across nine branches.
- **120 packet-buffer/transmitter lockstep runs** and **46/46 detected mutations**, across `ble-tx-pdu`, `ble-tx-pdu-we`, `ble-tx-rom`, and `ble-tx-cordic`; memory models and the write-strobe modes are exercised.
- Fixed VCOs: every phase swept, plus two seeds of 100,000 random clocks per branch; **7/7 ROM and 11/11 CORDIC mutants detected**.
- **381 harness test methods passed, 37 skipped**; skips are excluded from the pass count. Gaussian-tail, repetition, reserved-readback and RF-valid tests passed. **18/18 Yosys structural checks passed.**

During development, several mutation targets no longer matched the rewritten expressions; those attempts failed and were not counted. The targets were updated and rerun to require their concrete failure witnesses. The simulator-failure fixture now snapshots common dependency sources into its private Git reference so uncommitted edits do not prevent reaching the intended failing engine. This fixture is only a test of the harness; real-simulator comparisons above remain separate.

## Evidence and reproduction

Per-branch authoritative evidence is in `results/validation/lint-evidence-20261006/`: the common `branch_summary.json`, commands and exit codes, final source hashes, artifact hashes, compressed logs, and the exact RTL snapshot used for functional testing. On the original 16 branches, trailing whitespace on five modified RTL files was cleaned afterward; `formatting_only.json` proves that difference and the final lint was rerun on the final bytes. No functional RTL changed after those campaigns. Generated one-port models are archived and hash-checked against the regression provenance.

Detailed reports are in `lint-verified/`, `lint-guards-verified/`, `lint-recovery-final/`, `lint-uart-final/`, `lint-functional/` and, where applicable, `lint-functional-one-port/` and the controller directories named in `commands.json`. Hashes use canonical Git/LF bytes; Windows checkout CRLF may differ.

```bash
python3 scripts/validation/run_lint.py --output results/validation/my-lint
python3 tests/test_lint_guards.py --output results/validation/my-lint-guards
python3 tests/test_lint_recovery.py --output results/validation/my-state-recovery
```

Each output directory must be new. Verilator 5.020, the existing OSS CAD Suite/Icarus/Yosys toolchain and the repository's documented Python environment were used. Use the pinned references and branch-specific parameters in the saved commands to reproduce the functional campaigns.

See [ASIC_READINESS.md](ASIC_READINESS.md) for outstanding CDC/RDC, technology, physical, DFT, protocol and qualification work. Earlier PPA reports, including the newer ROM/CORDIC comparison, describe their recorded pre-lint revisions; they are not physical signoff for these changes. Passing this lint gate does not prove an error-free or market-ready ASIC.
