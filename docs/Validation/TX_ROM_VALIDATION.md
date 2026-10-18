# The VCO without memory: its tables in a ROM (`ble-tx-rom`)

For subsequent lint corrections and revalidation, see [LINT_CLOSURE.md](LINT_CLOSURE.md). The measurements below retain their stated source revisions.

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `ble-tx-rom`, from `ble-tx-pdu` (`4e6ffc2`, after the product audit)  
**Base:** tag `upstream-baseline` (`8540186`)  
**Date:** 2026-10-05  
**Author:** Miguel Simões  
**Status:** executed on commit `144d51b`, against corrected `master` (`5abbbf7`): the product
audit's campaign (`PRODUCT_VALIDATION.md`, `RF_INTERFACE_REVIEW.md`), each part in its own
checkout, with `tests/test_vco_fixed.py` and `tests/test_tx_pdu.py` and their mutants;
evidence in `results/validation/rom-*` (commit `1f1bb76`). Run `tx-vco` (`8083f77` and
`bb2cbaa`, made on `ble-tx-rom`): `scripts/area/run_area.sh` for the VCO and the
transmitter of every branch, and `scripts/timing/run_sta.sh` for `ble-tx-pdu`,
`ble-tx-rom` and `ble-tx-cordic`, all on the audited RTL. These are digital campaigns and
pre-layout measurements: ASIC readiness is NOT READY, as on every branch
(`ASIC_READINESS.md`).

---

## Purpose

`ble-tx-pdu` is the smallest transmitter whose COS and SIN tables can still be
written: 20 236.9 µm² on the audited RTL, of which 10 703.9 µm² is the one-port
512 × 8 memory of its quarter sine table, the larger of its two macros. Its report
set the next step aside: a fixed VCO table would remove that memory, but the
tables would stop being programmable. This branch takes that step: the tables
become the project's (`python/btlelib.py`), fixed, and the VCO has no memory. With
`ble-tx-cordic`, which builds the same tables the other way, it answers how small
the transmitter gets with fixed tables, and whether a ROM or a CORDIC is the
better fixed table.

## 1. What the branch contains

| Part | Taken from | Files | How it is selected |
|---|---|---|---|
| VCO: the project's COS and SIN tables, fixed: a ROM in logic of the first eighth of the wave (257 pairs), unfolded to the whole wave | new | `vco.v` | structural, always on |
| Gaussian filter (B2, paired), one-port packet buffer, exact rewrites of the counters | `ble-tx-pdu` at `4e6ffc2`, after the product audit, unchanged | — | `GAUSS_TABLE=1`, as on `ble-tx-pdu` |
| Tests | new | `tests/test_vco_fixed.py`; `tests/test_vco_sin2.py` removed (no memory to test); `tests/test_tx_pdu.py` without the VCO's macro model | — |
| Receiver, Link Layer, IQ-capture RAM, everything else | upstream, with the product audit's corrections | unchanged | — |

## 2. The VCO

Upstream's VCO adds the voltage samples into a 16-bit phase register and reads
both tables at its 11 low bits on every clock, from two 2 048 × 8 memories that
the host fills through the Link Layer's registers. The project's tables are cos[k]
= round(127 cos(2πk / 2048)) and sin[k] = round(127 sin(2πk / 2048)). The outputs
are registered: they show the entries of the phase of the clock before, with
`valid` and `last` delayed to match.

This VCO keeps the phase register and the output registers, and builds both
entries from the first eighth of the wave. The two top bits of the phase are the
quadrant q, the other nine the offset o (0 to 511). Above 256 the offset is
folded, f = 512 − o, where sine and cosine swap. The ROM gives s = |sin f| and c =
|cos f| for f = 0 to 256: 257 pairs of 7 bits (0 ≤ s ≤ 90, 90 ≤ c ≤ 127), a `case`
on f that synthesis turns into logic. With a = |sin o| (c if o > 256, else s) and
b = |cos o| (s if o > 256, else c):

| Quadrant | cos | sin |
|---|---|---|
| 0 | b | a |
| 1 | −a | b |
| 2 | −b | −a |
| 3 | a | −b |

This gives every entry of both tables exactly, at all 2 048 phases, and the
outputs, `valid` and `last` take the same clocks as upstream's. The table-write
ports stay in the interface and are ignored: the Link Layer still accepts the
table registers, which change nothing.

## 3. Evidence

At commit `144d51b`, in three checkouts of it (the matrix; the one-port model of
the packet buffer; everything else), against corrected `master` (`5abbbf7`), with
the product audit's input archive
(`results/validation/product-evidence-20261005/vectors.tar.gz`):

| Check | Result | Evidence (`results/validation/`) |
|---|---|---|
| VCO against the `master` VCO, its tables written with the project's values as the upstream testbench writes them, every output on every clock (`tests/test_vco_fixed.py`) | a sweep of every phase, by +1, −1 and 7 (6 146 clocks per seed); 4 seeds × 1 000 002 random clocks (samples on random clocks, every other clock or none, resets of 1–3 clocks, table writes): 3 991 804 comparisons, no mismatch; **7/7 mutants** | `rom-evidence-20261005/vco.log.gz` |
| Transmitter against corrected `master`'s, every output on every clock (`tests/test_tx_pdu.py --seeds 2 --packets 6`) | 2 seeds × 6 AXI clocks × 2 memory models: 24/24 runs, 2 241 980 clocks, 102 packets sent; **11/11 mutants** | `rom-evidence-20261005/pdu.log.gz` |
| The product audit's matrix, 270 cases (`run_rx_regression.sh`, `GAUSS_TABLE=1`) | **270/270**: 210 data comparisons, 60 verified rejections; no DIFFERENT, ERROR, BOTH_FAIL or NO_STIMULUS | `rom-final-20261005/rx_regression/` |
| The same on the one-port model of the packet buffer | **270/270** | `rom-final-20261005-one-port/rx_regression/` |
| TX waveforms against the Python model, every PDU decoded by the RTL receiver (`test_tx_packet.py --rtl-rx`) | **167/167**; on the one-port model 16/16 (`--quick`) | `rom-final-20261005/tx_packets.json` |
| RF-valid contract (`test_clock_domain_contract.py --mutants`) | 12/12 scenarios, 2/2 mutants | `rom-contract-final/` |
| Controller lockstep through the registers (`run_ctl_lockstep.sh`) | 6/6 runs, 36 TX and 36 RX completions, valid and invalid packets; 5/5 mutations | `rom-controller-final/` |
| Product defects (`test_product_mutations.py`) | 2 baselines; 4/4 defects caught | `rom-mutations-final/` |
| Harness, focused checks, measurement tools, suite | 23/23 harness methods; RX model, Gaussian tail, bit repetition and reserved registers pass; 6/6 measurement methods; 34/34 tests | `rom-evidence-20261005/`, `rom-measurement-final/` |
| Structure: Yosys elaboration, strict lint (Verilator 5.020) | Yosys passes; lint fails, as on every branch, with 156 diagnostics: those of `ble-tx-pdu` (153), 4 more `UNUSEDSIGNAL` (the four table-write ports) and 1 `DECLFILENAME` less (`sin_table_ram` is gone) | `rom-structure-final/` |

The mutants of the VCO, each of which a testbench must catch: one ROM entry off by
one (|sin| at offset 168); the fold above 256 off by one (511 − o instead of 512 −
o); cosine and sine not swapped in the odd quadrants; the cosine sign ignores the
odd quadrants; the outputs one clock early (not registered); valid one clock
early; the phase from the wrong bits of the integral.

`rom-evidence-20261005/` binds the tested sources (`source_sha256.json`, canonical
Git bytes) and every artifact (`artifact_sha256.json`) by hash, and sums the
campaign up (`branch_summary.json`). The `product-*` and `rf-*` folders inherited
from `ble-tx-pdu` are the evidence of that branch's RTL, not of this one.

## 4. Area

Run `tx-vco` (`docs/Validation/TX_BRANCH_COMPARISON.md` § 4.4): every branch on
the audited RTL, Yosys + ABC, Nangate45, the SRAMs as OpenRAM macros (FreePDK45):

| Branch | `vco` cells (µm²) | `btle_tx` cells (µm²) | Macros (µm²) | **Total (µm²)** | vs `master` |
|---|---:|---:|---:|---:|---:|
| `master` (corrected, `5abbbf7`) | 150.0 | 8 875.6 | 162 408.5 | **171 284.1** | — |
| `ble-tx-sin2` | 740.0 | 9 208.4 | 34 411.9 | **43 620.3** | −74.5 % |
| `ble-tx-1--8` | 1 059.7 | 9 790.1 | 34 132.9 | **43 923.0** | −74.4 % |
| `ble-tx-pdu` | 635.7 | 2 553.9 | 17 683.0 | **20 236.9** | −88.2 % |
| `ble-tx-pdu-we` | 635.7 | 2 564.8 | 17 683.0 | **20 247.8** | −88.2 % |
| `ble-tx-cordic` | 2 317.9 | 4 142.2 | 6 979.1 | **11 121.3** | −93.5 % |
| **`ble-tx-rom`** | 593.2 | 2 509.4 | 6 979.1 | **9 488.5** | **−94.5 %** |

1. **The smallest transmitter of all the branches: 9 488.5 µm²**, −94.5 % against
   `master` and −53.1 % against `ble-tx-pdu`. Its one macro is the packet buffer,
   6 979.1 µm², 74 % of it; the logic is the other 26 %.
2. **The ROM costs less than the logic it replaces.** The 10 703.9 µm² of the sine
   table are gone, and the VCO's logic goes from 635.7 µm² (the read sequencing of
   the one-port memory, its registers and cos 0) to 593.2 µm² (−42.5): 257
   constant pairs fold into less logic than the control of a memory. The
   transmitter's logic follows, 2 553.9 → 2 509.4 µm² (−44.5).
3. **A CORDIC is not worth it here**: `ble-tx-cordic` computes the same tables
   exactly with 2 317.9 µm², 3.9 times the ROM, and its transmitter is 1 632.8 µm²
   larger (11 121.3 µm²).

The same flow moves identical RTL by up to 317.8 µm² on the transmitters with the
runtime FIR and by 1.5 µm² on those with B2 (§ 4.4 of the comparison): far below
the differences above.

## 5. Timing

Run `tx-vco`, `scripts/timing/run_sta.sh` at 62.5 ns against corrected `master`
(`TX_BRANCH_COMPARISON.md` § 5.1). The ROM is not on the critical path: the
controller's worst path is a demodulator multiply (`genblk1[2]…i0[3]` →
`…signal_for_decision[31]`), as on most branches, with 1.642 ns of logic and a
minimum period of 2.002 ns (499.6 MHz, 60.5 ns of slack at 16 MHz), against 1.904
ns on `ble-tx-pdu`, whose worst path is the Link Layer's clock crossing. The
difference is the flow's noise: the same `btle_rx` RTL times at 1.512–1.616 ns
across the three runs. Corrected `master` measures 3.458 ns, its worst path in the
Gaussian tail with the runtime taps.

## 6. SRAM energy

The VCO has no memory: the transmitter's one SRAM is the packet buffer of
`ble-tx-pdu`, with the same `btle_tx.v` and so the same accesses, written on every
AXI clock but those that read it. Its figures are those of `ble-tx-pdu`'s buffer
(`TX_BRANCH_COMPARISON.md` § 6.6, run `sram-energy`): 19.40 µW of dynamic power and
15.0 µW of leakage once settled. The quarter sine table of `ble-tx-pdu`, read on
every clock, took 23.03 µW of dynamic power (17.08 µW for the reads, 5.95 µW for
its clocks) and 25.1 µW of leakage: they are gone. The logic that replaces it
switches too; it is not priced: the activity flow has not been run on the audited
RTL, whose coverage the product audit lists as open (`RF_INTERFACE_REVIEW.md`).

## 7. What the branch gives up

- **The COS and SIN tables altogether.** They are fixed to the project's; the
  table writes are ignored, so no other table can be loaded. `ble-tx-pdu` kept
  them programmable with quarter-wave symmetry and cos[k] = sin[512 − k].
- **The runtime Gaussian taps** (as `ble-tx-table` and `ble-tx-pdu`).
- **The packet's contract of `ble-tx-pdu`**: the packet is written before
  `tx_start`, as the upstream testbenches do; a byte rewritten in the 12 clocks
  between its request and its use may differ from upstream's; while a packet is
  sent, a pair must stay two AXI clocks; the AXI clock must run at 8 MHz or
  faster.

What `ble-tx-pdu`'s sine memory imposed goes with it: the VCO takes a sample on
any clock, and there is no table write to wait for. The receiver, the Link Layer
and the IQ-capture debug memory lose nothing.

## 8. Conclusion

This branch gives the smallest transmitter measured, 9 488.5 µm², half of
`ble-tx-pdu`, with the same outputs on every clock as long as the tables are the
project's, which is what `python/btlelib.py` writes. Its price is the
programmability of the tables, the last thing the VCO kept from upstream; if it is
needed, `ble-tx-pdu` is the smallest transmitter that keeps it (with the
conditions of its § 7).

## 9. Reproducing

From WSL, at the root of this branch, with Python 3.11 and NumPy, and the tools of
`results/validation/rom-evidence-20261005/tool_versions.txt` in `PATH` (Verilator
5.020 for the lint, as the product audit):

```bash
python3 tests/test_vco_fixed.py --mutants
python3 tests/test_tx_pdu.py --mutants                                  # the default campaign: 36 runs
# the product audit's campaign (PRODUCT_VALIDATION.md, RF_INTERFACE_REVIEW.md), with a new label
REF=5abbbf7a093b48a64f18c2c1f84057c54d0af0e5
mkdir -p /tmp/btle-v && tar -xzf results/validation/product-evidence-20261005/vectors.tar.gz -C /tmp/btle-v
export REGRESSION_VECTORS=/tmp/btle-v/vectors REGRESSION_JOBS=3 DUT_DEFAULTS='gauss_filter.v:GAUSS_TABLE=1'
bash scripts/validation/run_rx_regression.sh <label> $REF
python3 tests/test_tx_packet.py --rtl-rx --output /tmp/tx-packets.json
python3 tests/test_clock_domain_contract.py --output results/validation/<label>-contract --mutants
python3 -m unittest discover -s tests -p 'test_validation*.py' -v
python3 tests/test_measurement_evidence.py
python3 tests/test_rx_model.py; python3 tests/test_gauss_tail.py; python3 tests/test_upsample.py
python3 tests/test_control_readback.py
python3 tests/test_product_mutations.py --output results/validation/<label>-mutations
bash scripts/validation/ctl_lockstep/run_ctl_lockstep.sh <label>-controller 2 6 $REF
python3 tests/test_tx_pdu.py --seeds 2 --packets 6 --jobs 3 --mutants --ref-rev $REF
# the one-port packet buffer, in a separate clone
python3 tests/test_tx_pdu.py --write-one-port /tmp/btle_tx.v && cp /tmp/btle_tx.v verilog/btle_tx.v
bash scripts/validation/run_rx_regression.sh <label>-one-port $REF
python3 tests/test_tx_packet.py --quick
```

The structural check runs the commands recorded in
`results/validation/rom-structure-final/` (`elaborate.ys` with Yosys, and
`lint_command` of `result.json` with Verilator). Area and timing: run `tx-vco`,
`TX_BRANCH_COMPARISON.md` § 11.