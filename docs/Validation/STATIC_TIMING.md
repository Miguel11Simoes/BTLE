# Static timing: upstream vs the reduced configuration

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `ble-opt`  
**Date:** 2026-09-19  
**Author:** Miguel Simões  
**Status:** executed (harness `scripts/timing/`, RTL `0290e87`). Pre-layout
static timing on the mapped netlist, ideal wires and ideal clock.

---

## Purpose

The area and activity work answered "how much smaller" and "how much less
switching". This report answers the question that has to come before any
further optimisation: **does this implementation close frequency, and what
limits it?** The comparison is upstream `btle_controller` (default parameters)
against the `ble-opt` reduced configuration (`ENABLE_IQ_CAPTURE=0,
LL_MINIMAL=1, GAUSS_TABLE=1`), plus the four blocks that changed, all through
the same flow.

The target is the **16 MHz baseband clock, 62.5 ns**.

## 1. Method

`scripts/timing/run_sta.sh sticker-vs-upstream 62.5`; results in
[`results/timing/sticker-vs-upstream/`](../../results/timing/sticker-vs-upstream/summary.txt).

1. **Netlist.** Same synthesis as the area runs: Yosys `synth -flatten`,
   `dfflibmap`, `abc -liberty`, Nangate45, RAMs as macros. Upstream is read
   from tag `upstream-baseline`; the reduced configuration from the working
   tree.
2. **Cut to a combinational network** ([`cut_flops_blif.py`](../../scripts/timing/cut_flops_blif.py)).
   ABC's timing engine ignores sequential cells, so every flip-flop is removed
   and replaced by the boundary it stands for: its `Q`/`QN` become primary
   inputs (launch points), its `D` becomes a primary output (capture point).
   The RAM macros and the Yosys `$print` cell have no library timing, so they
   are cut the same way. What ABC then times is exactly the register-to-register
   logic.
3. **Legalise before timing.** The Yosys+ABC netlist contains no buffer trees:
   in the upstream controller one net drives 867 loads, 999 fF against a
   26.7 fF library limit. Timing it as it stands is meaningless. The flow runs
   `buffer -N 16 -p` (maximum fanout 16) and then `upsize`/`dnsize`, which is
   what a real flow does, and reports **both** delays so the difference is
   visible.
4. **Period.** ABC's `stime` gives only the logic. The period also needs the
   launch and capture times of the registers:
   `T ≥ t_CQ + t_comb + t_setup`. [`seq_constraints.py`](../../scripts/timing/seq_constraints.py)
   takes the **worst** clock-to-Q and setup in the liberty tables, over every
   characterised slew and load, for the flip-flop types actually used:
   0.347 ns for `DFF_X1`, 0.359 ns where upstream also uses `DFFR_X1`/`DFFS_X1`.

Two details of the netlist had to be handled explicitly, and both are recorded
per design in `<design>.cut.txt`:

- **Undriven nets become primary inputs**, not constant 0. The design really
  has them — 573 in the upstream controller, 488 in the reduced one — and they
  are the unconnected Link-Layer register bits already recorded as issue U8.
  Tying them low, which is ABC's default, would delete the logic behind them
  and hide paths. As inputs they are pessimistic start points instead.
- **Aliases and constants** are resolved (a buffer alias becomes a net rename,
  an inverting one an `INV_X1`), because ABC rejects `.names` nodes in a mapped
  network.

## 2. Results

### 2.1 Period and slack at 16 MHz

| Design | Unbuffered | Logic path | Register overhead | **Min period** | **Slack at 62.5 ns** | Fmax |
|---|---:|---:|---:|---:|---:|---:|
| Controller, upstream | 6.073 ns | 1.631 ns | 0.359 ns | 1.991 ns | **+60.51 ns** | 502 MHz |
| Controller, reduced | 4.044 ns | 1.597 ns | 0.347 ns | **1.944 ns** | **+60.56 ns** | 514 MHz |
| `btle_rx`, upstream | 7.016 ns | 1.515 ns | 0.347 ns | 1.862 ns | +60.64 ns | 537 MHz |
| `btle_rx`, shared demodulator | 3.223 ns | 1.588 ns | 0.347 ns | 1.935 ns | +60.57 ns | 517 MHz |
| `btle_ll`, upstream | 1.547 ns | 1.171 ns | 0.359 ns | 1.530 ns | +60.97 ns | 654 MHz |
| `btle_ll`, minimal | 1.552 ns | 1.171 ns | 0.347 ns | 1.518 ns | +60.98 ns | 659 MHz |
| Gaussian filter, FIR | 1.553 ns | 1.382 ns | 0.347 ns | 1.729 ns | +60.77 ns | 578 MHz |
| Gaussian filter, table | 0.766 ns | 0.664 ns | 0.347 ns | **1.011 ns** | +61.49 ns | 989 MHz |
| Demodulator, one upstream copy | 1.945 ns | 1.510 ns | 0.347 ns | 1.857 ns | +60.64 ns | 539 MHz |
| Demodulator, shared | 1.943 ns | 1.493 ns | 0.347 ns | 1.840 ns | +60.66 ns | 543 MHz |

### 2.2 Where the worst path is

| Design | Start | End | What it is |
|---|---|---|---|
| Controller, upstream | `btle_rx_i.genblk1[2]…gfsk_demodulation_i.i1[5]` | `…signal_for_decision[31]` | the demodulator's multiply, in one of the 8 phase copies |
| Controller, reduced | `btle_ll_i…write_data[16]` | `…write_data[76]` | `timestamp[3] → timestamp[63]`: the carry chain of the 64-bit free-running counter |
| `btle_rx`, upstream | `genblk1[7]…gfsk_demodulation_i.i0[3]` | `…signal_for_decision[31]` | demodulator multiply, phase 7 |
| `btle_rx`, shared | `gfsk_demodulation_shared_i.old_i[5]` | `…signal_for_decision[31]` | the same multiply, now from the shared history |
| `btle_ll` (both) | `clk_cross_bus_bb_to_s_axi_i.write_data[16]` | `…write_data[76]` | the 64-bit timestamp counter |
| Gaussian filter, FIR | `gauss_filter_tap0[2]` | `bit_upsample_gauss_filter[15]` | tap × sample and the adder tree |
| Gaussian filter, table | `bit_upsample_store[6]` | `bit_upsample_gauss_filter[7]` | table lookup and the three-term sum |

The reduced controller's path is a chain of 40 AND2/AND4 gates closed by an
XNOR2 — a ripple carry, which is exactly how the 64-bit increment of
`timestamp` synthesises. `timestamp` sits at bits 13–76 of the bb→AXI status
bundle, so bits 16 and 76 are `timestamp[3]` and `timestamp[63]`.

### 2.3 Size of what was timed

| Design | Flip-flops cut | Combinational gates | Macros cut |
|---|---:|---:|---:|
| Controller, upstream | 4 578 | 45 716 | 16 |
| Controller, reduced | 2 673 | 13 428 | 15 |
| `btle_rx`, upstream | 2 068 | 34 885 | 0 |
| `btle_rx`, shared demodulator | 1 416 | 8 652 | 0 |
| `btle_ll`, upstream → minimal | 2 036 → 954 | 7 417 → 3 382 | 3 |
| Gaussian filter, FIR → table | 178 → 22 | 2 108 → 231 | 0 |
| Demodulator, one copy → shared (all 8 phases) | 100 → 412 | 3 799 → 4 639 | 0 |

## 3. What the numbers say

**1. Both configurations close 16 MHz with a factor of about 31 in hand.**
The reduced controller needs 1.944 ns of a 62.5 ns period: **97 % of the clock
period is unused**. The question "does this implementation close frequency" is
answered with a very large yes, for upstream as well. Timing is not what
constrains this design; area, memory and energy are.

**2. The reduction did not cost frequency — it gained a little.** The
controller's minimum period goes from 1.991 ns to 1.944 ns (−2.4 %), and every
block is equal or faster except `btle_rx` (§ 4). This matters because
resource sharing usually buys area with delay: here it did not, since the
sharing is in *time* (one demodulator visiting 8 phases) and not in the depth
of the arithmetic.

**3. The critical path moved out of the receiver.** In upstream it is the
demodulator's multiply inside one of the eight copies. In the reduced design
the worst path is the 64-bit `timestamp` counter in the Link Layer — a
housekeeping counter, not signal processing. Its carry chain is also the worst
path of `btle_ll` alone, in both versions (1.171 ns), and `LL_MINIMAL` does not
touch it, as expected: the timestamp is kept. If the period ever mattered,
this counter is the thing to split; with 60.5 ns of slack it does not.

**4. The shared demodulator is not slower than a single upstream copy.**
Standalone: 1.857 ns for one upstream demodulator against 1.840 ns for the
shared one that serves all 8 phases. The per-phase history is read *before* the
arithmetic, so the multiplexing does not lengthen the multiply. Inside
`btle_rx` the shared version is 0.073 ns slower (1.862 → 1.935 ns, +3.9 %),
which is the operand selection merged into the surrounding logic. Both are
3.2 % of the available period.

**5. The Gaussian table is the biggest timing win: −41.5 %** (1.729 →
1.011 ns), because the table removes the tap multiply and the adder tree and
leaves a lookup plus a three-term sum. It is also 989 MHz, the fastest block
measured.

**6. Buffering is what makes these numbers real.** Unbuffered, the upstream
controller reads 6.073 ns and `btle_rx` 7.016 ns, which say nothing except that
Yosys does not build buffer trees. After legalising fanout and sizing, the
upstream controller is 1.631 ns **at 3 % less area** than the buffered netlist.
The unbuffered column is kept in the results for exactly this reason.

**7. Consequence for the next steps.** With 97 % of the period unused there is
room to trade time for area — more time-multiplexing of the arithmetic, which
is the deferred item B4 — without any timing risk from logic depth. The real
limit on further sharing is **throughput**, not delay: one I/Q sample arrives
every other 16 MHz cycle and all 8 phases must be processed before the next
one. The same slack is the argument for voltage scaling, which is the lever
that matters for a sticker-class tag, but this library is characterised at one
operating point only, so that cannot be quantified here.

## 4. What this does not claim

- **Pre-layout, ideal wires.** `WireLoad = "none"`: no interconnect RC, no
  congestion, no placement. Real nets add delay, and the 40-gate carry chain of
  the timestamp counter is the path that would grow the most.
- **Ideal clock.** No clock tree, no insertion delay, no skew, no jitter, no
  on-chip variation, and no derating. A real flow would also add uncertainty.
- **Setup only, no hold.** Hold violations are a placement and clock-tree
  matter and cannot be judged here; with a real clock tree they are the
  plausible risk in a design this fast relative to its clock, not setup.
- **One lumped clock domain.** The design has two clocks (`bb_clk` at 16 MHz
  and `axi_aclk`), and the analysis merges all registers into one network, so
  clock-crossing paths are timed as if they were single-cycle. This is
  pessimistic, and the conclusion survives it: the worst path found anywhere,
  1.991 ns, is below the period of **either** clock, so whichever domain a path
  belongs to it still meets it. No multi-cycle or false paths were declared.
- **Memories are not timed.** Paths are cut at the RAM macro pins, so the SRAM
  access time is absent. On a real macro this is the number most likely to set
  the period.
- **Pessimistic register constraints.** The worst clock-to-Q and setup in the
  whole liberty table are used, not the values at the actual slew and load.
- **Undriven nets are start points.** 573 (upstream) and 488 (reduced) inputs
  are nets nothing drives, promoted to primary inputs so no logic is deleted.
  They are conservative false start points: they can only make the reported
  path longer, never shorter.

## 5. Follow-up

1. **Clock gating of the shared demodulator's registers**, already recommended
   in [SWITCHING_ACTIVITY.md](SWITCHING_ACTIVITY.md) § 5. The slack measured
   here shows that the extra gating logic in the enable path cannot threaten
   timing.
2. **Further time-multiplexing (B4)** is unblocked from the timing side; the
   constraint to check is sample throughput, not path delay.
3. A **real power figure** now needs place and route plus a library
   characterised at more than one voltage; the SAIF from the activity harness
   and the netlist from this one are the inputs it would take.

## 6. Reproducing

```bash
scripts/timing/run_sta.sh <label> [clock-ns] [ref-rev]   # WSL/Linux, repository root
```

The script refuses to overwrite a label. It records the commits, tools and
liberty hash in `provenance.txt`, and writes per design: the cell statistics
(`.stat`), what was cut and every undriven net (`.cut.txt`), the ABC timing
report (`.stime.txt`), the full critical path translated back to the design's
own names (`.path.txt.gz`), the register constraints used (`.seq.txt`), and the
combined `summary.tsv` / `endpoints.txt`.
