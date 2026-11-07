# The VCO without memory: its tables computed by a CORDIC (`ble-tx-cordic`)

For subsequent lint corrections and revalidation, see [LINT_CLOSURE.md](LINT_CLOSURE.md). The measurements below retain their stated source revisions.

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `ble-tx-cordic`, from `ble-tx-pdu` (`4e6ffc2`, after the product audit)  
**Base:** tag `upstream-baseline` (`8540186`)  
**Date:** 2026-10-05  
**Author:** Miguel Simões  
**Status:** executed on commit `3d9ad94`, against corrected `master` (`5abbbf7`): the product
audit's campaign (`PRODUCT_VALIDATION.md`, `RF_INTERFACE_REVIEW.md`), each part in its own
checkout, with `tests/test_vco_fixed.py` and `tests/test_tx_pdu.py` and their mutants;
evidence in `results/validation/cordic-*` (commit `aa8dd23`). Run `tx-vco` (`8083f77` and
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
`ble-tx-rom`, which builds the same tables the other way, it answers how small the
transmitter gets with fixed tables, and whether a ROM or a CORDIC is the better
fixed table.

## 1. What the branch contains

| Part | Taken from | Files | How it is selected |
|---|---|---|---|
| VCO: the project's COS and SIN tables, fixed: computed by an exact CORDIC of the first eighth of the wave (15 iterations in one clock), unfolded to the whole wave | new | `vco.v` | structural, always on |
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
folded, f = 512 − o, where sine and cosine swap. A CORDIC in rotation mode
computes c = |cos f| and s = |sin f|. The start vector is (x0, 0), x0 = 19 743 =
round(127 K 2⁸), K the gain of 15 iterations; the angle z starts at f, in units of
2π / 2048 with 8 fraction bits (18 bits signed), and x and y carry 8 fraction bits
(17 bits signed). Iteration i (0 to 14) rotates by ±atan 2⁻ⁱ: by the sign of z it
adds or subtracts y·2⁻ⁱ to x, x·2⁻ⁱ to y and atan 2⁻ⁱ to z (65 536, 38 688, 20
442, 10 377, 5 208, 2 607, 1 304, 652, 326, 163, 81, 41, 20, 10 and 5 in those
units). After the 15th, x and y, rounded, are 127 cos f and 127 sin f. The
iterations are unrolled, in one clock between the phase register and the output
registers. Fifteen are the fewest that give every entry exactly: the closest value
lies 0.001 from a rounding boundary (offset 168). With a = |sin o| (c if o > 256,
else s) and b = |cos o| (s if o > 256, else c):

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

At commit `3d9ad94`, in three checkouts of it (the matrix; the one-port model of
the packet buffer; everything else), against corrected `master` (`5abbbf7`), with
the product audit's input archive
(`results/validation/product-evidence-20261005/vectors.tar.gz`):

| Check | Result | Evidence (`results/validation/`) |
|---|---|---|
| VCO against the `master` VCO, its tables written with the project's values as the upstream testbench writes them, every output on every clock (`tests/test_vco_fixed.py`) | a sweep of every phase, by +1, −1 and 7 (6 146 clocks per seed); 4 seeds × 1 000 002 random clocks (samples on random clocks, every other clock or none, resets of 1–3 clocks, table writes): 3 991 804 comparisons, no mismatch; **11/11 mutants** | `cordic-evidence-20261005/vco.log.gz` |
| Transmitter against corrected `master`'s, every output on every clock (`tests/test_tx_pdu.py --seeds 2 --packets 6`) | 2 seeds × 6 AXI clocks × 2 memory models: 24/24 runs, 2 241 980 clocks, 102 packets sent; **11/11 mutants** | `cordic-evidence-20261005/pdu.log.gz` |
| The product audit's matrix, 270 cases (`run_rx_regression.sh`, `GAUSS_TABLE=1`) | **270/270**: 210 data comparisons, 60 verified rejections; no DIFFERENT, ERROR, BOTH_FAIL or NO_STIMULUS | `cordic-final-20261005/rx_regression/` |
| The same on the one-port model of the packet buffer | **270/270** | `cordic-final-20261005-one-port/rx_regression/` |
| TX waveforms against the Python model, every PDU decoded by the RTL receiver (`test_tx_packet.py --rtl-rx`) | **167/167**; on the one-port model 16/16 (`--quick`) | `cordic-final-20261005/tx_packets.json` |
| RF-valid contract (`test_clock_domain_contract.py --mutants`) | 12/12 scenarios, 2/2 mutants | `cordic-contract-final/` |
| Controller lockstep through the registers (`run_ctl_lockstep.sh`) | 6/6 runs, 36 TX and 36 RX completions, valid and invalid packets; 5/5 mutations | `cordic-controller-final/` |
| Product defects (`test_product_mutations.py`) | 2 baselines; 4/4 defects caught | `cordic-mutations-final/` |
| Harness, focused checks, measurement tools, suite | 23/23 harness methods; RX model, Gaussian tail, bit repetition and reserved registers pass; 6/6 measurement methods; 34/34 tests | `cordic-evidence-20261005/`, `cordic-measurement-final/` |
| Structure: Yosys elaboration, strict lint (Verilator 5.020) | Yosys passes; lint fails, as on every branch, with 159 diagnostics: those of `ble-tx-pdu` (153), 7 more `UNUSEDSIGNAL` (the four table-write ports; `z15`, the last angle, and the bits the rounding drops from `x_rounded` and `y_rounded`, which synthesis removes) and 1 `DECLFILENAME` less (`sin_table_ram` is gone) | `cordic-structure-final/` |

The mutants of the VCO, each of which a testbench must catch: one iteration fewer
(14); the rounding left out (truncation); the direction of iteration 5 inverted;
iteration 2 shifts by 3; the start vector without the CORDIC gain; the fold above
256 off by one (511 − o instead of 512 − o); cosine and sine not swapped in the
odd quadrants; the cosine sign ignores the odd quadrants; the outputs one clock
early (not registered); valid one clock early; the phase from the wrong bits of
the integral.

`cordic-evidence-20261005/` binds the tested sources (`source_sha256.json`,
canonical Git bytes) and every artifact (`artifact_sha256.json`) by hash, and sums
the campaign up (`branch_summary.json`). The `product-*` and `rf-*` folders
inherited from `ble-tx-pdu` are the evidence of that branch's RTL, not of this
one.

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
| **`ble-tx-cordic`** | 2 317.9 | 4 142.2 | 6 979.1 | **11 121.3** | **−93.5 %** |
| `ble-tx-rom` | 593.2 | 2 509.4 | 6 979.1 | **9 488.5** | −94.5 % |

1. **No memory, but not the smallest**: 11 121.3 µm², −93.5 % against `master` and
   −45.0 % against `ble-tx-pdu`. Its one macro is the packet buffer.
2. **The CORDIC is 3.9 times the ROM.** Its VCO measures 2 317.9 µm², against
   593.2 µm² for the ROM of `ble-tx-rom`, which gives the same tables, and 635.7
   µm² of logic (and 10 703.9 µm² of memory) for the sine table of `ble-tx-pdu`:
   15 stages of 17- and 18-bit adders cost more than 257 constant pairs. Its
   transmitter is 1 632.8 µm² above `ble-tx-rom`'s.
3. **For these tables a ROM is the better fixed table.** A ROM grows with the
   number of phases, a CORDIC with the number of bits; at 2 048 phases of 8 bits,
   folded to 257 entries, the ROM is smaller.

The same flow moves identical RTL by up to 317.8 µm² on the transmitters with the
runtime FIR and by 1.5 µm² on those with B2 (§ 4.4 of the comparison): far below
the differences above.

## 5. Timing

Run `tx-vco`, `scripts/timing/run_sta.sh` at 62.5 ns against corrected `master`
(`TX_BRANCH_COMPARISON.md` § 5.1). The CORDIC is the controller's worst path: its 15
add-and-shift stages, from the phase register (`vco_i.integral_voltage_signal[3]`)
to the output register (`btle_tx_i.i_internal[6]`) in one clock, take 5.142 ns of
logic, a minimum period of 5.501 ns (181.8 MHz), against 2.002 ns on `ble-tx-rom`
and 1.904 ns on `ble-tx-pdu`. It is the first change of the transmitter that puts
the worst path there; the 16 MHz clock still leaves 57.0 ns of slack, a factor of
11. Corrected `master` measures 3.458 ns, its worst path in the Gaussian tail with
the runtime taps.

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

This branch answers the question its sibling leaves: a CORDIC computes the
project's tables exactly, with no memory, but for these tables it is larger than a
ROM and slower, and it gives up the same thing, the programmability of the tables.
`ble-tx-rom` is the better fixed table; this branch is kept as the measured
alternative.

## 9. Reproducing

From WSL, at the root of this branch, with Python 3.11 and NumPy, and the tools of
`results/validation/cordic-evidence-20261005/tool_versions.txt` in `PATH`
(Verilator 5.020 for the lint, as the product audit):

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
`results/validation/cordic-structure-final/` (`elaborate.ys` with Yosys, and
`lint_command` of `result.json` with Verilator). Area and timing: run `tx-vco`,
`TX_BRANCH_COMPARISON.md` § 11.