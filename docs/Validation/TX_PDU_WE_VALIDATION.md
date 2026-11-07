# The packet buffer written only when its pair is new (`ble-tx-pdu-we`)

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `ble-tx-pdu-we`, from `ble-tx-pdu` (`d7c65e3`)  
**Base:** tag `upstream-baseline` (`8540186`)  
**Date:** 2026-10-05  
**Author:** Miguel Simões  
**Status:** executed at commit `eec6c8f`: `tests/test_tx_pdu.py` and `tests/test_vco_sin2.py`
(with their mutants); runs `tx-pdu-we` and `tx-pdu-we-one-port` of
`scripts/validation/run_rx_regression.sh` (the strict runner of the integrity audit); run
`tx-pdu-we` of `scripts/validation/ctl_lockstep/run_ctl_lockstep.sh`,
`scripts/validation/formal_gauss/run_formal_gauss.sh` and
`scripts/validation/equiv_defaults/run_equiv_defaults.sh`; run `tx-pdu-we` of
`scripts/compare/run_compare.sh` (area, static timing, gate-level lockstep and switching
activity). Runs `sram-char` and `sram-char-trimmed` (at `f810ae4`) and `sram-char-xyce` (at
`9c9227f`) of `scripts/power/run_sram_char.sh`, their summaries rewritten at `3d94645`;
run `sram-leakage` of `scripts/power/run_sram_leakage.sh` at `3d94645`; runs `sram-energy` of
`scripts/power/run_sram_energy.sh` and `sram-idle` of `scripts/power/run_sram_idle.sh` at
`d39ee32` (the SRAM energy, new on this branch).

**Product audit:** after the runs of `eec6c8f`, the product audit of 2026-10-05
corrected the RTL of every branch and revalidated it
([`PRODUCT_VALIDATION.md`](PRODUCT_VALIDATION.md),
[`ASIC_READINESS.md`](ASIC_READINESS.md)). §§ 3, 4 and 6 describe `eec6c8f`,
before it; § 5 counts the accesses on the audited RTL.

---

## Purpose

`ble-tx-pdu` gave the packet buffer one port and kept upstream's way of filling
it: the pair (address, data) of the Link Layer's register 8 is written into the
memory on **every** clock of the AXI clock, whether it changed or not. That
costs no area, but each of those writes is an access of the SRAM. The
processor changes the pair once per packet byte, up to a few hundred times
per packet; the memory is written 16 million times per second at a 16 MHz AXI
clock, and more at a faster one, with or without a packet.

Power is part of the thesis, so this branch writes the buffer only when its
pair is new: the Link Layer already knows the AXI clock that follows a write of
register 8, and passes it on as a write strobe. The transmitter's outputs are
the same as on `ble-tx-pdu` on every clock; the price is two flip-flops.

The branch also measures what the change is for. The activity flow of
`TX_BRANCH_COMPARISON.md` § 6 leaves the SRAMs out (they are macros, not cells),
and OpenRAM's analytical `.lib` gives a macro the same clock power whether it
reads, writes or is deselected, so neither can tell a write from an idle
clock. § 5 counts the accesses of the transmitter's memories on the workloads
of the activity flow and prices them with a SPICE characterization of their
OpenRAM macros, for `master`, `ble-tx-pdu` and this branch.

## 1. What the branch contains

| Part | Taken from | Files | How it is selected |
|---|---|---|---|
| Everything of `ble-tx-pdu`: B2 paired, the quarter sine table, the one-port packet buffer, the exact rewrites | `ble-tx-pdu` | as there | as there (`GAUSS_TABLE=1`; the rest structural) |
| The packet buffer's write strobe | new | `btle_ll.v` (output `tx_pdu_octet_mem_we`), `btle_controller.v`, `btle_phy.v`, `btle_tx.v` (`pdu_buffer`) | `PDU_WRITE_STROBE=1`; the default, 0, is the buffer of `ble-tx-pdu`, written on every clock |
| The SRAM energy measurement | new | `scripts/power/run_sram_char.sh`, `openram_char.py`, `summarize_sram_char.py`, `run_sram_leakage.sh`, `sram_leakage.py`, `run_sram_energy.sh`, `sram_count_models.v`, `summarize_sram_energy.py` | — |
| Receiver, Link Layer (but the new output), IQ-capture RAM, everything else | upstream | unchanged | — |

The branch is measured with both parameters on (`scripts/branch_config.sh`
gives `GAUSS_TABLE=1 PDU_WRITE_STROBE=1`).

## 2. The write strobe

- **Link Layer.** `tx_pdu_octet_mem_we` is 1 in the AXI clock after each
  write of register 8, the clock in which the register holds the new pair:
  `slv_reg_wren` and `axi_awaddr_core` come from registers of `ll_s_axi` that
  are updated with `slv_reg8` (the receive buffer's pointer reset, `rx_ram`,
  uses the same two signals). It is also 1 while the AXI reset holds the
  register at 0: upstream's buffer then takes byte 0 = 0 on every clock, and so
  does this one.
- **Controller.** In Link Layer mode the strobe is the Link Layer's; in
  baremetal mode it is held at 1, because the `ext_tx_pdu_octet_mem_*` inputs
  come without one, and the buffer then takes the pair on every clock, as on
  `ble-tx-pdu`. When the controller leaves baremetal mode it is 1 for one
  clock: upstream then writes register 8's pair again at once, and an `ext_`
  pair may have overwritten that byte.
- **Buffer.** With the strobe on, the memory is written in the clock of the
  strobe, or in the next one if that clock reads (`write_pending`); the
  register of byte 256 takes its byte in the clock of the strobe. One write per
  new pair instead of one per clock.
- **Contract.** As on `ble-tx-pdu`: the packet is written before `tx_start`,
  and while a packet is sent a new pair must stay two AXI clocks, the clock of
  its strobe and the next. Register 8 keeps every pair at least three (two AXI
  writes are at least three clocks apart); in baremetal mode the `ext_` pair
  must stay two clocks while sending, as on `ble-tx-pdu`, and leaving baremetal
  mode counts as a new pair.
- **Cost.** Two flip-flops (`write_pending`, and `baremetal_phy_intf_mode` one
  clock ago) and a few gates (§ 4).

## 3. Evidence

At `eec6c8f`, before the product audit, which reports its own campaigns on
the corrected RTL in `PRODUCT_VALIDATION.md`.

| Check | What it compares | Result |
|---|---|---|
| The transmitter (`tests/test_tx_pdu.py`) | `btle_tx` against upstream's `btle_tx`, every output on every clock, with `PDU_WRITE_STROBE` 0 and 1; each pair comes with a one-clock strobe and stays two AXI clocks; while a packet is sent, the bytes of the next one that it does not use are written with their final values, half of them aimed at the clock in which the buffer reads; random packets (255 and 0 bytes first), resets that abort packets, CRC and channel loads, access-address changes, extra `tx_start`, table rewrites; `clkb` = `clk` and free at 100, 33.3, 16.1, 10 and 8 MHz; the repository's RAM models and one-port macro models of both memories. With the strobe on, the memory must be written exactly once per new pair | **72/72 runs, no difference**: per strobe setting and memory model, 2 344 632 clocks compared, 116 packets sent of 180 started (82 resets), 1 037 735 I/Q samples, 211 987 pairs written while sending, 3 243 of them bytes of the next packet, 1 656 new pairs in a clock that reads. **The memory is written 59 563 times for 59 563 new pairs with the strobe, 1 169 498 times without it.** **13/13 mutants** caught (the 11 of `ble-tx-pdu`, one of them now a write in the reading clock with the strobe; the pending write dropped; the pair written on every clock despite the strobe, caught by the write count) |
| The VCO (`tests/test_vco_sin2.py`) | the same `vco.v` as `ble-tx-pdu` | **5 120 clocks and 2 629 325 comparisons, no difference, the one-port macro model identical on every clock (as on `ble-tx-pdu`)**; **11/11 mutants** |
| Controller through the registers (`ctl_lockstep`, run `tx-pdu-we`) | the whole controller with `PDU_WRITE_STROBE=1` against upstream, the tables and the packets written through the AXI registers; half of the packets get a baremetal window before `tx_start` (`ext_` pairs over the packet, then back to the Link Layer, whose register-8 pair upstream writes again) | **15/15 runs, 922 759 cycles compared, every output and every register read identical**; 90 packets sent, 90 received; 40 baremetal windows, 212 `ext_` pairs; **8/8 mutants** (the 5 of `ble-tx-pdu`; the strobe taken from register 9, no strobe when leaving baremetal mode, no strobe in baremetal mode) |
| Formal (`formal_gauss`, run `tx-pdu-we`) | `gauss_filter` with `GAUSS_TABLE=1` (unchanged from `ble-tx-pdu`) against the upstream FIR, unbounded | **PASS**; 3/3 mutants make the proof fail |
| Defaults (`equiv_defaults`, run `tx-pdu-we`) | `gauss_filter` with its default parameters against `upstream-baseline` | **equivalent** (450 `$equiv` cells) |
| Upstream testbenches, strict (run `tx-pdu-we`, `GAUSS_TABLE=1` and, on `btle_controller`, `PDU_WRITE_STROBE=1`) | the 5 upstream testbenches over the 54 saved conditions of the integrity audit, against upstream | **FAIL, as on every branch**: 118 PASS, 20 BOTH_FAIL, 18 NO_STIMULUS, 114 ERROR, **0 DIFFERENT**; all 270 rows (statuses, exit codes, outputs, details) equal to `master`'s strict run and to `ble-tx-pdu`'s |
| The same on one-port macro models (run `tx-pdu-we-one-port`) | the same, with the buffer's and the VCO's memories on one-port macro models | **the same 270 rows, 0 DIFFERENT** |
| Gate-level lockstep (run `tx-pdu-we`, `TX_BRANCH_COMPARISON.md` § 6.1) | both synthesised controllers, this branch and upstream, every output on every clock, 5 scenarios, the packets written through register 8 | **5/5 scenarios, no mismatch**; 25 packets transmitted and 27 sent to the receiver, the tables and the packets written through the registers |
| Integrity tests (`tests/test_validation*.py`) | the verdict guards of the integrity audit | 21 tests: 20 pass, 1 skipped (not applicable to this branch) |

The upstream controller testbench runs in baremetal mode
(`baremetal_phy_intf_mode = 1`), where the strobe is held at 1, so the strict
regression sees the buffer of `ble-tx-pdu`. The Link Layer's strobe is checked
by the controller lockstep, the gate-level lockstep and the transmitter test.
The regression's FAIL is upstream's own matrix (`VALIDATION_INTEGRITY.md`): it
shows no difference, not more than the 118 checks that pass.

## 4. Area

Yosys 0.68 + ABC, Nangate45, SRAMs blackboxed and counted in bits (run
`tx-pdu-we`, at `eec6c8f`, before the product audit; `ble-tx-pdu` is run
`tx-pdu` of the same harness). Each top is synthesised alone, with
`GAUSS_TABLE=1 PDU_WRITE_STROBE=1` where it declares them.

| Top | `master` | `ble-tx-pdu` | **`ble-tx-pdu-we`** |
|---|---:|---:|---:|
| `btle_tx`: cells / flip-flops | 3 409 / 404 | 1 305 / 256 | **1 299 / 257** |
| `btle_tx`: cell area (µm²) | 5 322.9 | 2 415.5 | **2 415.0** |
| `btle_ll`: cells / cell area (µm²) | 9 453 / 16 746.3 | 9 453 / 16 746.3 | **9 478 / 16 748.2** |
| `btle_controller`: cells / flip-flops | 50 295 / 4 578 | 48 164 / 4 430 | **48 056 / 4 432** |
| `btle_controller`: cell area (µm²) | 71 706.4 | 68 767.1 | **68 767.4** |
| `btle_controller`: SRAM bits | 1 136 070 | 1 105 350 | **1 105 350** |

The strobe costs two flip-flops (`write_pending` in the buffer, and
`baremetal_phy_intf_mode` one clock ago in the controller) and the Link
Layer's comparator (+25 cells, +1.9 µm² in `btle_ll`). The rest is below the
resolution of the flow: `btle_tx` comes out 6 cells and 0.5 µm² smaller than
on `ble-tx-pdu`, the controller 108 cells smaller and 0.3 µm² larger, and the
receiver, the same RTL, moves by 30 cells. The memories are those of
`ble-tx-pdu`, so the transmitter with its macros measures 2 415.0 + 10 703.9 +
6 979.1 = **20 098.0 µm²**, −88.0 % against `master`, the same as `ble-tx-pdu`
(20 098.5).

## 5. SRAM energy

### 5.1 Why a SPICE characterization, and which leakage

OpenRAM writes the clock pin's `internal_power` of each macro for four cases:
write, read, and deselected with the write enable low or high. Its analytical
model, which `scripts/area/run_openram.sh` uses, fills the four with one number:
an estimate of the whole array's dynamic power, in mW, with every gate
switching at 100 MHz (FreePDK45's `default_event_frequency`). It cannot tell an
access from an idle clock, and it is a power, not an energy per access.
(`TX_BRANCH_COMPARISON.md`, `VCO_MEMORY_SWEEP.md` and `TX_PDU_VALIDATION.md` had
read it as pJ per access; they are corrected.)

OpenRAM's SPICE characterization measures each case:
`scripts/power/run_sram_char.sh` builds the netlist of each macro (FreePDK45, as
`run_openram.sh`) and characterizes it with ngspice (revision 26, the one in
OpenRAM's environment) at the nominal corner (TT, 1.0 V, 25 °C), one input slew
and one output load, at a 5 ns cycle (`openram_char.py`: no search for the
minimum period, which would add some ten SPICE runs per port and does not change
the energy of a cycle). Each case is the average supply power over one clock
cycle, with the other port deselected. What the runs showed decides how they are
read:

- **The whole netlist.** OpenRAM trims it by default to the bitcells of the
  outer rows and columns, which leaves the other bitlines and wordlines without
  most of their load: 0.741 against 0.889 pJ for a write on the 256 × 8 macro,
  17 % less, and 35 % less on the 512 × 8 one (run `sram-char-trimmed`).
- **An access is priced against a deselected clock** of the same port,
  (P_access − P_deselected) × period: what a write turned into an idle clock
  saves.
- **A deselected clock costs energy too**, (P_deselected − leakage) × period:
  0.323 pJ on the 256 × 8 macro and 0.372 pJ on the 512 × 8 one. The macro gates
  its array with the chip select, not its clock buffers and input flip-flops,
  which take every clock; it is charged on every clock of every memory, on both
  branches alike.
- **The leakage, settled, with every cell at 0** (run `sram-leakage`,
  `scripts/power/run_sram_leakage.sh`). OpenRAM's own figure, 115.1 µW on the
  256 × 8 macro and 130.3 µW on the 512 × 8 one, is the supply power 5–10 ns
  after a power-up from 0 V, with every port deselected. Nothing drives the
  bitlines of a deselected macro, nor the sense amplifiers' inputs, which follow
  them through the column multiplexer; 10 ns after the power-up they still sit
  between the rails, and the sense amplifiers draw a crossover current. The same
  measure, with every bitcell started at 0, after one deselected clock and for 5
  µs instead of 10 ns, gives 239.3 and 95.9 µW over its own first 5–10 ns, and
  settles at **15.0 and 25.1 µW**: its last three windows, 3–5 µs, agree within
  0.1 %, and its summary shows the bitlines and the sense amplifier's input
  reaching their levels. The content must be fixed: the leakage of a deselected
  macro depends on the data of the columns its address selects (§ 5.5). Against
  OpenRAM's figure, a deselected clock would cost less than nothing.

Xyce, the other simulator of OpenRAM's environment, is faster but not usable
here (run `sram-char-xyce`): on the 256 × 8 netlist its access energies are
within 4 % of ngspice's (0.921 and 0.848 pJ), and its leakage, 13.3 µW, from its
operating point, is near the settled one, but on the 512 × 8 netlist it gives
3.5 mW of leakage and 3.8 mW for a write of a 0, artefacts.

| Macro | Memory | Write (pJ) | Read (pJ) | Deselected clock (pJ) | Leakage (µW) | OpenRAM's figure (µW) |
|---|---|---:|---:|---:|---:|---:|
| `sram_1rw1r_8x2048` | COS and SIN tables of `master` | — | — | — | — | — |
| `sram_1rw1r_8x512` | packet buffer of `master` | — | — | — | — | 126.7 |
| `sram_1rw_8x512` | quarter sine table of `ble-tx-pdu` and `ble-tx-pdu-we` | 1.161 | 1.068 | 0.372 | 25.1 | 130.3 |
| `sram_1rw_8x256` | packet buffer of `ble-tx-pdu` and `ble-tx-pdu-we` | 0.889 | 0.821 | 0.323 | 15.0 | 115.1 |

### 5.2 Accesses

`scripts/power/run_sram_energy.sh` runs the workloads of the activity flow
(`tb_activity.v`: the same setup, the same five scenarios, 100 000 clocks of
`bb_clk` = `s00_axi_aclk` = 16 MHz, the vectors of run `all-branches`) at RTL,
the reference and the measured branch side by side, every output compared on
every clock, with every RAM model replaced by one that counts its accesses
(`sram_count_models.v`), and subtracts a setup-only run. It counts on the
audited RTL: the reference is the corrected `master` of the product audit, after
its RF-valid correction (`5abbbf7`, `RF_INTERFACE_REVIEW.md`), `ble-tx-pdu` is
`4e6ffc2` and this branch `cfa24a4`. A two-port memory (`sdpram_one_clk`,
`sdpram_two_clk`) writes in each clock with its write enable and reads on every
clock of its read port, as upstream's tables and buffer do; a one-port memory
writes, reads, or is deselected.

| Configuration | Memory | Macro | Writes, `idle` / `tx` | Reads, `idle` / `tx` | Dynamic power, `idle` / `tx` (µW) |
|---|---|---|---:|---:|---:|
| `master` | packet buffer | `sram_1rw1r_8x512` | 100 000 / 100 000 | 100 000 / 100 000 | — / — |
| `master` | VCO cos table | `sram_1rw1r_8x2048` | 100 000 / 100 000 | 100 000 / 100 000 | — / — |
| `master` | VCO sin table | `sram_1rw1r_8x2048` | 100 000 / 100 000 | 100 000 / 100 000 | — / — |
| `ble-tx-pdu` | packet buffer | `sram_1rw_8x256` | 100 000 / 99 405 | 0 / 595 | 19.40 / 19.39 |
| `ble-tx-pdu` | VCO quarter sine table | `sram_1rw_8x512` | 0 / 0 | 100 000 / 100 000 | 23.03 / 23.03 |
| `ble-tx-pdu-we` | packet buffer | `sram_1rw_8x256` | 0 / 612 | 0 / 595 | 5.17 / 5.34 |
| `ble-tx-pdu-we` | VCO quarter sine table | `sram_1rw_8x512` | 0 / 0 | 100 000 / 100 000 | 23.03 / 23.03 |

### 5.3 Energy

Dynamic power of the transmitter's SRAMs, per scenario (µW), the part of it that
the clocks take, and the leakage (µW):

| Configuration | `rx` | `tx` | `mixed` | `idle` | `idle0` | of which clocks | Leakage |
|---|---:|---:|---:|---:|---:|---:|---:|
| `master` | — | — | — | — | — | — | — |
| `ble-tx-pdu` | 42.43 | 42.42 | 42.42 | 42.43 | 42.43 | 11.12 | 40.1 |
| `ble-tx-pdu-we` | 28.20 | 28.37 | 28.28 | 28.20 | 28.20 | 11.12 | 40.1 |

— : a memory of that configuration is not characterized.

### 5.4 What it says

1. **`ble-tx-pdu` accesses both memories on every clock.** It reads the quarter
   sine table on every clock, with or without traffic, and writes the packet
   buffer on every AXI clock but the ones that read it, as upstream does: the
   transmitter's SRAMs take 42.4 µW of dynamic power in every scenario,
   14.2 µW to write the buffer, 17.1 µW to read the sine table and 11.1 µW for the
   clocks of the two macros (5.2 and 5.9 µW), which every clock costs.
2. **The strobe removes the buffer's writes.** `ble-tx-pdu-we` writes the
   buffer once per new pair: never in `idle`, `idle0` and `rx`, 612 times in
   `tx` (the 34 bytes of each of the 18 packets written in the window, against
   99 405 writes on `ble-tx-pdu`), 306 in `mixed`. Its writes and reads take
   0.17 µW in `tx` and nothing without packets, so the transmitter's SRAMs drop to
   28.20–28.37 µW: **14.1–14.2 µW less, −34 %**.
   At this 16 MHz AXI clock the saving is 14.2 µW; it grows with the
   AXI clock, since `ble-tx-pdu` writes its buffer on every one of them
   (44.4 µW at 50 MHz, 88.9 µW at 100 MHz), while `ble-tx-pdu-we` writes it
   once per packet byte whatever the clock.
3. **What is left is the clocks and the sine table's reads**: 11.1 µW for the
   clocks of both macros on both branches, and 17.1 µW to read the table, on every
   clock and in every scenario: the VCO reads entry a of its phase on every
   clock it does not write, also when the phase does not move. Reading it only
   when the phase moves, or a sample is taken, would remove almost all of the
   reads without traffic; it is not built.
4. **The leakage is of the same order**: 15.0 µW for the 256 × 8 macro and 25.1
   µW for the 512 × 8 one with every cell at 0, 40.1 µW in all, in every
   scenario and the same on both branches: about as much as the dynamic power of
   `ble-tx-pdu`, more than that of `ble-tx-pdu-we`. OpenRAM's own figures, 115.1
   and 130.3 µW, are not the leakage (§ 5.1). With random data in the words
   never written, this branch's buffer at rest takes 10.3 to 19.8 µW more (§
   5.5).
5. **`master` is not priced.** Its 2 048 × 8 two-port tables are too large for
   this ngspice, and the measurement run of its 512 × 8 two-port buffer did not
   finish in 6 h; their accesses are counted all the same: upstream writes and
   reads each of its three memories on every clock, in every scenario. The
   summary's checks fail on that alone (`incomplete energy characterization`);
   every other check passes.

### 5.5 The buffer at rest, with the words the RTL leaves in it

§ 5.1 prices the leakage with every cell at 0. A deselected macro does not
drive its bitlines: the address it holds connects one column per bit to the
sense amplifier, through the column multiplexer, and when the cells of that
column disagree, the bitline settles between the rails, the amplifier's input
with it, and the amplifier draws a crossover current. Run `sram-idle`
(`scripts/power/run_sram_idle.sh`) measures this branch's buffer as the RTL
leaves it, deselected, with the measure of § 5.1: the words the RTL wrote and
the address and data at its inputs at the end of the `idle` and `tx` windows of
§ 5.2 (`sram_count_models.v` dumps them), and the words never written at 0 or
random (two seeds), as a power-up leaves them.

| Window | Address, data in | Words never written | Their fill | Ones in the selected column of each bit (of 32) | Sense-amplifier inputs at 5 µs (V) | Static power (µW) |
|---|---:|---:|---|---|---|---:|
| `idle` | 0, 0 | 255 | 0 | 0 0 0 0 0 0 0 0 | 0.22 0.22 0.22 0.22 0.22 0.22 0.22 0.22 | 15.0 |
| `idle` | 0, 0 | 255 | random, seed 1 | 17 15 13 17 12 18 14 20 | 0.31 0.30 0.28 0.31 0.28 0.32 0.29 0.34 | 25.3 |
| `idle` | 0, 0 | 255 | random, seed 2 | 12 17 15 17 14 16 21 22 | 0.28 0.31 0.30 0.31 0.29 0.31 0.35 0.36 | 28.2 |
| `tx` | 16, 121 | 222 | 0 | 3 2 3 2 2 2 4 0 | 0.24 0.23 0.23 0.24 0.24 0.24 0.25 0.22 | 15.7 |
| `tx` | 16, 121 | 222 | random, seed 1 | 21 15 18 16 15 17 16 9 | 0.39 0.30 0.32 0.35 0.34 0.36 0.35 0.26 | 34.8 |
| `tx` | 16, 121 | 222 | random, seed 2 | 14 18 19 17 14 20 17 16 | 0.33 0.32 0.33 0.35 0.33 0.38 0.36 0.31 | 35.6 |

With the words never written at 0 the buffer stays at 15.0–15.7 µW; with
them random it takes 25.3–35.6 µW, **10.3 to 19.8 µW more**, as much as
the strobe saves (§ 5.4). It concerns a deselected macro, the buffer of this
branch between packets: `ble-tx-pdu` writes its buffer on every AXI clock,
which drives its bitlines on every clock, and both branches read the sine
table on every clock. Writing the whole buffer once after reset would keep it
near 15.0 µW; it is not built.

## 6. Timing and switching activity

Run `tx-pdu-we`, at `eec6c8f`, before the product audit, the whole controller
against upstream (`TX_BRANCH_COMPARISON.md` §§ 5 and 6):

- **Timing:** minimum period 2.050 ns at the 62.5 ns (16 MHz) target, against
  1.919 ns on `ble-tx-pdu` and 1.991 ns upstream. The worst path is now the
  Link Layer's 64-bit `timestamp` counter (`btle_ll_i…write_data[16]` →
  `[76]`), the same RTL as upstream's and the worst path of `ble-tx-table`,
  `ble-tx-sin8` and `ble-opt` too; the strobe's comparator is elsewhere in
  `btle_ll`. 0.131 ns above `ble-tx-pdu`, it is within the 0.15 ns of the
  flow's noise.
- **Switching activity** (pin-capacitance proxy, not power): −2.1 to −2.9 %
  over the five scenarios, within 0.1 point of `ble-tx-pdu` (−2.2 to −3.0 %);
  the clock-pin load −3.17 %, against −3.21 %, for the two flip-flops more.
  While transmitting the rest of the transmitter switches 123.6 toggles per
  cycle (`ble-tx-pdu`: 125.7), and the RAM ports 1 315 toggles fewer in `tx`
  (3 182 191 against 3 183 506): the buffer's write enable and address now
  move only for a new pair. The proxy does not see the memories themselves;
  § 5 measures them.

## 7. What the branch gives up

The same as `ble-tx-pdu`, and nothing more:

- **The runtime Gaussian taps** (as `ble-tx-table`).
- **Arbitrary COS/SIN tables** (as `ble-tx-sin2`): quarter-wave symmetry and
  cos[k] = sin[512 − k]; sine writes wait for a clock without a read, none
  while transmitting; one sample every two clocks at most.
- **Rewriting a packet byte while it is read**: the packet is written before
  `tx_start`, as the upstream testbenches do (the repository's firmware does
  not transmit); a byte rewritten in the 12 clocks between its request and its
  use may differ from upstream's; while a packet is sent, a new pair must stay
  two AXI clocks; the AXI clock must run at 8 MHz or faster.

In baremetal mode the strobe is held at 1, so the buffer is written on every
clock there, as on `ble-tx-pdu`: the saving is in Link Layer mode, the path the
boards use. The receiver, the Link Layer and the IQ-capture debug memory lose
nothing.

## 8. Reproducing

From WSL, at the root of this branch. The checks and the comparison reproduce
the runs of `eec6c8f`; at the audited head they give those of
`PRODUCT_VALIDATION.md`.

```bash
python3 tests/test_tx_pdu.py --mutants                                          # IVERILOG, VVP in PATH
python3 tests/test_vco_sin2.py --mutants
python3 -m unittest discover -s tests -p 'test_validation*.py' -v
mkdir -p /tmp/btle-audited-vectors
tar -xzf results/validation/integrity-20261004/vectors.tar.gz -C /tmp/btle-audited-vectors
REGRESSION_VECTORS=/tmp/btle-audited-vectors/vectors \
  DUT_DEFAULTS="gauss_filter.v:GAUSS_TABLE=1 btle_controller.v:PDU_WRITE_STROBE=1" \
  scripts/validation/run_rx_regression.sh <label>                               # expected exit 1, 0 DIFFERENT
# the same on the one-port macro models: in a separate clone
python3 tests/test_vco_sin2.py --write-one-port /tmp/vco.v && cp /tmp/vco.v verilog/vco.v
python3 tests/test_tx_pdu.py --write-one-port /tmp/btle_tx.v && cp /tmp/btle_tx.v verilog/btle_tx.v
scripts/validation/ctl_lockstep/run_ctl_lockstep.sh <label>
scripts/validation/formal_gauss/run_formal_gauss.sh <label>
scripts/validation/equiv_defaults/run_equiv_defaults.sh <label> upstream-baseline gauss_filter
mkdir /tmp/vec && tar -xzf results/compare/all-branches/vectors.tar.gz -C /tmp/vec
VEC_DIR=/tmp/vec scripts/compare/run_compare.sh <label> master ble-tx-pdu-we
# the SRAM energy: the macros with SPICE (about 1 h and 4 h), their settled leakage with every cell
# at 0 (under 1 h), the summary with it, then the accesses against the current reference (minutes;
# exit 1 while master's macros are not characterized), then the buffer at rest (about 25 min)
PERIOD_NS=5 scripts/power/run_sram_char.sh <char-label> sram_1rw_8x256 sram_1rw_8x512
scripts/power/run_sram_leakage.sh <leak-label> sram_1rw_8x256 sram_1rw_8x512
python3 scripts/power/summarize_sram_char.py results/power/<char-label> sram_1rw_8x256 sram_1rw_8x512 \
  --leakage results/power/<leak-label>/leakage.json > results/power/<char-label>/summary.md
SRAM_CHAR=results/power/<char-label> VEC_DIR=/tmp/vec REF_REV=5abbbf7a093b48a64f18c2c1f84057c54d0af0e5 \
  scripts/power/run_sram_energy.sh <label> master ble-tx-pdu ble-tx-pdu-we
scripts/power/run_sram_idle.sh <idle-label> <label> ble-tx-pdu-we idle tx
```
