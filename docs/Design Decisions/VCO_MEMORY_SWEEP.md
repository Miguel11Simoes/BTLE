> **Status update, 2026-10-05:** the corrected RTL and strict results are documented in [PRODUCT_VALIDATION.md](../Validation/PRODUCT_VALIDATION.md) and [ASIC_READINESS.md](../Validation/ASIC_READINESS.md). This document preserves historical implementation/measurement results. Its PPA values do not describe the corrected circuit; earlier equality/PASS claims are not product signoff.

# Single-port memory for the VCO tables: the OpenRAM sweep, and the branches it decides

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** every branch carries this same file (`master`, `risc-v-ble`, `ble-tx-table`, `ble-tx-table-reg`, `ble-tx-table-sram`, `ble-tx-fir2`, `ble-tx-sin4`, `ble-tx-sin8`, `ble-tx-sin8-1rw`, `ble-tx-sin2`, `ble-tx-1--8`, `ble-tx-opt`, `ble-tx-pdu`, `ble-tx-pdu-we`, `ble-tx-rom`, `ble-tx-cordic`, `ble-rx-dm`, `ble-opt`)  
**Base:** tag `upstream-baseline` (`8540186`)  
**Date:** 2026-10-03; updated 2026-10-04 (the two branches built and measured, and the 256 × 16 as `ble-tx-1--8`, § 5; the 512 × 8 again on `ble-tx-pdu`, with B2 and a one-port packet buffer, § 5) and 2026-10-05 (the last column of § 2.2 corrected: OpenRAM's analytical clock power, not an energy per access; `ble-tx-pdu-we`; `ble-tx-rom` and `ble-tx-cordic`, the VCO without memory, § 5)  
**Author:** Miguel Simões  
**Status:** executed: run `openram-1rw-sweep` of `scripts/area/run_openram.sh` on branch
`ble-tx-sin8-1rw` (commit `176a79b`): 9 single-port macros requested, 8 generated. Measured
before any RTL of the new branches; `ble-tx-sin128` was deleted after it (§ 4).
`ble-tx-sin8-1rw` and `ble-tx-sin2` were then built and measured (run `tx-1rw`,
`docs/Validation/BRANCH_COMPARISON.md`; their reports `TX_SIN8_1RW_COMPARISON.md` and
`TX_SIN2_COMPARISON.md`, at the root of each), and so was the 256 × 16 memory, as branch
`ble-tx-1--8` (run `tx-1--8`; report `TX_1--8_COMPARISON.md`). `ble-tx-pdu` reuses the
512 × 8 memory of `ble-tx-sin2` with B2 and a one-port packet buffer (run `tx-pdu`;
report `docs/Validation/TX_PDU_VALIDATION.md`), and `ble-tx-pdu-we` the same
transmitter (run `tx-pdu-we`). `ble-tx-rom` and `ble-tx-cordic` then remove the VCO memory
(run `tx-vco`, on the audited RTL; reports `docs/Validation/TX_ROM_VALIDATION.md` and
`TX_CORDIC_VALIDATION.md`).

---

## Purpose

On `ble-tx-sin8` the VCO keeps the first quarter of the cosine and sine tables
in one 512 × 16 memory with two ports, one read/write and one read (1RW1R):
37 703.9 µm², 56 % of its transmitter and 59 % of the transmitter of
`ble-tx-opt` (`docs/Validation/BRANCH_COMPARISON.md` § 4). Two levers are
left on that memory: the number of ports, and its geometry (how many words of
how many bits). Three branches were cut from `ble-tx-sin8` (`00ad076`), one per
alternative, so that each can be built and measured on its own; the third was
deleted after this sweep (§ 4):

| Branch | Memory | Reads per sample | What it stores |
|---|---|---:|---|
| `ble-tx-sin8-1rw` | 512 × 16, one port | 1 | the two quarter tables, {cos, sin} per word, as `ble-tx-sin8` |
| `ble-tx-sin2` | 512 × 8, one port | 2 | the quarter sine table only; the cosine is read from it, cos θ = sin(90° − θ) |
| `ble-tx-sin128` (deleted after this sweep) | 128 × 32, one port | 1 | an eighth of the wave, {cos, sin} of 0°–45°, two entries per word |

This document measures the candidate memories before any of them is written in
RTL, checks that one port at 16 MHz is fast enough, and records what the
numbers decide.

## 1. Why one port is enough

Upstream writes each table on every clock through its own port, which is why
the memories of `ble-tx-sin4` and `ble-tx-sin8` have two ports. Three facts of
the RTL make one port sufficient:

1. **The transmitter produces one sample every two clocks.** The upsampler
   toggles its valid on every 16 MHz clock (`bit_repeat_upsample.v:72`), the
   Gaussian filter only registers it (`gauss_filter.v:112`), and it is the
   VCO's input valid (`gfsk_modulation.v:108`). The VCO's address changes at
   most once every two clocks: 8 Msample/s at 16 MHz.
2. **`ble-tx-sin8` already writes a table only when its register changes**
   (`vco.v:119-122` on that branch), not on every clock. Writes happen when the
   processor programs the tables.
3. **The transmitter outputs are forced to zero when it is idle**
   (`btle_tx.v:104-105`), so the VCO's output only matters while transmitting.

So a single port has two clocks per sample: one read and one free clock for a
write (`ble-tx-sin8-1rw`, and an eighth-wave memory), or two reads
(`ble-tx-sin2`, which then has no free clock while transmitting). No second,
faster clock is needed.

## 2. The sweep

`scripts/area/run_openram.sh`, the script of runs `openram-tx` and
`openram-sin8`: OpenRAM 1.2.48, FreePDK45, default layout, nominal corner
(TT, 1.0 V, 25 °C), analytical timing model, no DRC/LVS. Single-port (1RW)
macros only. A word that holds more than one 8-bit table entry gets an 8-bit
write mask (OpenRAM `write_size = 8`), because the registers write one entry at
a time; the same geometries without the mask measure what the mask costs. The
array organisation (rows, columns, column multiplexing) is OpenRAM's own
choice, read from the SPICE netlist of each macro while the run was going
(`arrays.txt` in the results; the netlists themselves are not kept).

### 2.1 Area

| Memory | Write mask | Bits | Cell array: rows × columns, column mux | Sense amplifiers and write drivers | Size (µm) | **Area (µm²)** | µm² per bit |
|---|---|---:|---|---:|---|---:|---:|
| 512 × 16 | 8-bit | 8 192 | 64 × 128, 8:1 | 16 | 135.157 × 126.627 | **17 114.7** | 2.09 |
| 512 × 16 | — | 8 192 | 64 × 128, 8:1 | 16 | 135.157 × 126.627 | 17 114.7 | 2.09 |
| 512 × 8 | — | 4 096 | 64 × 64, 8:1 | 8 | 85.285 × 125.507 | **10 703.9** | 2.61 |
| 256 × 16 | 8-bit | 4 096 | 64 × 64, 4:1 | 16 | 86.385 × 120.680 | **10 424.9** | 2.55 |
| 256 × 16 | — | 4 096 | 64 × 64, 4:1 | 16 | 86.385 × 118.915 | 10 272.5 | 2.51 |
| 128 × 32 | 8-bit | 4 096 | 64 × 64, 2:1 | 32 | 133.810 × 124.340 | **16 637.9** | 4.06 |
| 128 × 32 | — | 4 096 | 64 × 64, 2:1 | 32 | 122.370 × 120.895 | 14 793.9 | 3.61 |
| 64 × 64 | 8-bit | 4 096 | — | — | not generated: OpenRAM's pin router stops ("Couldn't route") | — | — |
| 64 × 64 | — | 4 096 | not read | 64 (one per bit of the word, as in the others) | 218.180 × 126.620 | 27 626.0 | 6.74 |

With two ports, from runs `openram-sin8` and `openram-tx`: 512 × 16 1RW1R
37 703.9 µm², 512 × 8 1RW1R 23 708.0 µm².

What the table shows:

- **One port instead of two halves the memory.** 512 × 16: 37 703.9 →
  17 114.7 µm² (−54.6 %); 512 × 8: 23 708.0 → 10 703.9 µm² (−54.9 %).
- **With the same bits, the width of the word decides.** Every 4 096-bit
  memory has the same 64 × 64 cell array; the word width only changes the
  column multiplexing and the circuitry behind each output bit (sense
  amplifier, write driver, data flip-flops, pins). 256 × 16 is 4.0 % smaller
  than 512 × 8 with twice that circuitry; 128 × 32, with four times, is 38 %
  larger without the mask and 55 % larger with it; 64 × 64, with eight times,
  is 2.6 times larger, and took 21 minutes to route against 1.5 to 5.3 for the
  others.
- **The write mask** costs nothing on 512 × 16 (the same footprint),
  152.4 µm² (1.5 %) on 256 × 16 and 1 844.0 µm² (12.5 %) on 128 × 32.
- **The ~7 000 µm² quoted for a public 128 × 32 OpenRAM example is not
  reproduced** with this OpenRAM version and these options: 14 793.9 µm²
  without the mask and 16 637.9 µm² with the mask the tables need, 2.1 to
  2.4 times that figure.

### 2.2 Timing and power, from each `.lib`

| Memory | Data valid after the **falling** clock edge | Minimum clock period | Setup / hold | Leakage | Clock power, analytical model (every gate at 100 MHz) |
|---|---:|---:|---:|---:|---:|
| 512 × 16 (mask) | 0.321 ns | 1.188 ns | 0.009 / 0.001 ns | 8.6 µW | 1.30 mW |
| 512 × 8 | 0.286 ns | 1.058 ns | 0.009 / 0.001 ns | 4.5 µW | 0.72 mW |
| 256 × 16 (mask) | 0.285 ns | 1.054 ns | 0.009 / 0.001 ns | 4.5 µW | 0.73 mW |
| 128 × 32 (mask) | 0.287 ns | 1.062 ns | 0.009 / 0.001 ns | 4.5 µW | 0.77 mW |
| 64 × 64 (no mask) | 0.271 ns | 1.001 ns | 0.009 / 0.001 ns | 4.5 µW | 0.82 mW |

The variants without the mask have the same delays and minimum period. The
last column is the `internal_power` of the clock pin written by OpenRAM's
analytical model: one estimate of the whole array's dynamic power, in mW, with
every gate switching at 100 MHz (FreePDK45's `default_event_frequency`),
written alike for a write, a read and a deselected clock. It is neither an
energy per access nor different for an idle clock. (This table first read it
as pJ per access, in the energy unit of the `.lib`; OpenRAM writes average
power there, mW, from its model or, with SPICE, from its measurement. A SPICE
characterization of the 512 × 8 one-port macro, and of the 256 × 8 packet
buffer of `ble-tx-pdu`, is in `BRANCH_COMPARISON.md` § 6.6.)

## 3. Timing at 16 MHz

The memory samples address and data on the rising edge and its data is valid
0.271 to 0.321 ns after the falling edge: at most 31.6 ns after the rising
edge, with at least 30.9 ns left before the next rising edge, where the VCO
uses it. The minimum clock period is 1.001 to 1.188 ns, 53 to 62 times shorter
than the 62.5 ns of the 16 MHz clock; setup and hold are 0.009 and 0.001 ns.

- One read per sample (`ble-tx-sin8-1rw`, an eighth-wave memory) and two reads
  per sample (`ble-tx-sin2`, one in each clock of the sample) both fit with
  this margin.
- No memory needs a faster clock. A 32 MHz clock would also fit, but the
  transmitter's two clocks per sample make it unnecessary (§ 1).
- These are the analytical model at the nominal corner. A slow-corner SPICE
  characterisation would give longer delays, but not 50 times longer.

## 4. What the numbers decide

| Alternative | Memory | Area (µm²) | vs the memory of `ble-tx-sin8` | Reads per sample | Free clock for writes while transmitting | Decision |
|---|---|---:|---:|---:|---|---|
| `ble-tx-sin8` (today) | 512 × 16, two ports | 37 703.9 | — | 1 | — (second port) | reference |
| `ble-tx-sin8-1rw` | 512 × 16, one port | 17 114.7 | −54.6 % | 1 | yes | **implement** (built, § 5) |
| `ble-tx-sin2` | 512 × 8, one port | 10 703.9 | −71.6 % | 2 | no | **implement** (built, § 5) |
| eighth wave, one entry per word | 256 × 16, one port | 10 424.9 | −72.4 % | 1 | yes | **the best 4 096-bit memory** (built as `ble-tx-1--8`, § 5) |
| `ble-tx-sin128` | 128 × 32, one port | 16 637.9 | −55.9 % | 1 | yes | **not supported: branch deleted** |
| 64 × 64 | 64 × 64, one port, no mask (with the mask: not generated) | 27 626.0 | −26.7 % | 1 | yes | **no branch** |

1. **`ble-tx-sin8-1rw`: implement.** The same 512 × 16 memory and the same
   tables as `ble-tx-sin8`, with one port: −20 589.2 µm² of memory and no new
   restriction on the tables. The mask is free at this size. The only new
   limit: while transmitting, a table write waits for the clock without a read
   (one write per two clocks); outside transmission it is the limit of
   `ble-tx-sin8`. As built, a waiting write is held in the table registers
   instead of a queue, so a table's pair must not change again before it is
   written, and a write to the entry being read is shown through a 16-bit
   register, which costs no clock of the port (`TX_SIN8_1RW_COMPARISON.md`).
2. **`ble-tx-sin2`: implement.** 512 × 8 with one port, 37.5 % below the
   memory of `ble-tx-sin8-1rw`. Its costs: two reads per sample, so no clock is
   free while transmitting and table writes wait for the end of the packet;
   the cosine is the sine read at 90° − θ, so the COS table can no longer be
   programmed on its own (the project's tables satisfy cos θ = sin(90° − θ)
   exactly: checked on all 513 positions of the quarter, 0 violations); and
   cos 0° = sin 90° falls outside the 512 words, in an 8-bit register. As
   built, entry b of the next phase is read ahead in the clock of the sample, so
   the outputs change in the same clock as upstream's, and the VCO takes at
   most one sample every two clocks and none in the clock after a reset, as
   the transmitter gives (`TX_SIN2_COMPARISON.md`).
3. **`ble-tx-sin128`: not supported by the numbers.** 128 × 32 measures
   16 637.9 µm² with the mask its writes need, far from the ~7 000 µm² that
   motivated it: 55 % above the 512 × 8 of `ble-tx-sin2`, with the same bits,
   and close to the 512 × 16 of `ble-tx-sin8-1rw`, which holds twice as many.
   Its 32-bit word quadruples the output circuitry of the same 64 × 64 array.
   The branch was deleted on 2026-10-03, before any RTL, and never pushed.
4. **The 4 096-bit {cos, sin} memory the numbers support is 256 × 16**, an
   eighth of the wave with one entry per word: 10 424.9 µm² with the mask, the
   smallest memory of the sweep, 2.6 % below 512 × 8, and with one read per
   sample it keeps a free clock for writes, which `ble-tx-sin2` does not. Its
   costs: the eighth-wave symmetry couples the COS and SIN tables, as in
   `ble-tx-sin2` (exact for the project's tables: 0 violations over 513
   positions); a second reflection and swap at 45°; and the 45° entry, [90, 90]
   in the project's tables, falls outside the 256 words, in a register (8 bits
   suffice: the symmetry that couples the tables makes cos 45° = sin 45°). It
   is the natural replacement for the 128 × 32 of the deleted `ble-tx-sin128`,
   and is built as branch `ble-tx-1--8` (`TX_1--8_COMPARISON.md`): both tables
   are written, each entry into the half where it is stored.
5. **64 × 64: no branch.** With the mask its writes need (four entries of each
   table per word), OpenRAM 1.2.48 cannot route its pins in FreePDK45: the
   escape router stops with "Couldn't route". Without the mask it routes, after
   21 minutes, at 27 626.0 µm²: the largest memory of the sweep, 2.7 times the
   256 × 16 with the same bits and 1.6 times the 512 × 16 that holds twice as
   many. The trend of the sweep says why: the cell array stays the same, and
   the 64-bit word brings 64 sense amplifiers and write drivers.
6. **No faster clock** (§ 3).

## 5. What the transmitter would measure

Estimates: the transmitter logic of the branch each alternative starts from
(measured), plus its memory, plus the 512 × 8 packet buffer with two ports
(23 708.0 µm²). The logic each alternative adds or removes (Δ) is not known
until it is built; on `ble-tx-sin8` the shared write port cost 597.7 µm².

| Alternative | Memory (µm²) | TX, from `ble-tx-sin8` (FIR) | vs `master` | vs `ble-tx-sin8` | TX, from `ble-tx-opt` (B2) | vs `master` |
|---|---:|---:|---:|---:|---:|---:|
| `ble-tx-sin8` / `ble-tx-opt` (measured) | 37 703.9 | 67 437.3 | −59.8 % | — | 64 440.8 | −61.6 % |
| `ble-tx-sin8-1rw` | 17 114.7 | 46 848.1 + Δ | −72.1 % | −30.5 % | 43 851.6 + Δ | −73.9 % |
| `ble-tx-sin2` | 10 703.9 | 40 437.3 + Δ | −75.9 % | −40.0 % | 37 440.8 + Δ | −77.7 % |
| 256 × 16, eighth wave | 10 424.9 | 40 158.3 + Δ | −76.1 % | −40.5 % | 37 161.8 + Δ | −77.8 % |
| `ble-tx-sin128` (128 × 32, deleted) | 16 637.9 | 46 371.3 + Δ | −72.4 % | −31.2 % | 43 374.8 + Δ | −74.1 % |

`master` is 167 731.4 µm². With any of these memories, the packet buffer
becomes the largest part of the transmitter: 51 % of it with
`ble-tx-sin8-1rw`, 59 % with `ble-tx-sin2` or 256 × 16.

**Built and measured** (run `tx-1rw`, `docs/Validation/BRANCH_COMPARISON.md`
§ 4.2): `ble-tx-sin8-1rw` measures **46 772.8 µm²** (Δ = −75.2 µm²: the waiting
writes held in the table registers and a 16-bit held entry cost less than the
queues of `ble-tx-sin8`), −72.1 % against `master` and −30.6 % against
`ble-tx-sin8`; `ble-tx-sin2` measures **40 292.6 µm²** (Δ = −144.7 µm²),
−76.0 % and −40.3 %. With these Δ, the column from `ble-tx-opt` becomes
43 776.4 and 37 296.1 µm²; neither combination with B2 is built
(`BRANCH_COMPARISON.md` § 4.2 estimates the second from `ble-tx-table`,
37 295.3 µm²; the 0.8 µm² is the residual of `ble-tx-opt`).

The 256 × 16 eighth wave, built as `ble-tx-1--8` (run `tx-1--8`), measures
**40 358.6 µm²** (Δ = +200.3 µm²), −75.9 % against `master` and −40.2 % against
`ble-tx-sin8`. Its logic, the second reflection of the address, the swap past
45°, the 45° register and the routing of each write to its half, costs 345.0 µm²
more than that of `ble-tx-sin2`, which takes back the 279.0 µm² its memory
saves: the best memory of the sweep gives a transmitter 66.0 µm² (0.2 %) above
`ble-tx-sin2`, the same size within the resolution of the flow, but with one
read per sample (writes while transmitting, a sample on any clock).

**The packet buffer next.** With a one-port VCO memory, the two-port 512 × 8
packet buffer is the largest part of the transmitter. `ble-tx-pdu` keeps the
memory of `ble-tx-sin2` and gives the buffer one port too, 256 words and a
register for byte 256 (6 979.1 µm², run `openram-pdu`), with B2 and exact
rewrites of the logic: the transmitter measures **20 098.5 µm²**, −88.0 %
against `master` (run `tx-pdu`, `BRANCH_COMPARISON.md` § 4.2). `ble-tx-pdu-we`
keeps it and writes the buffer only when its pair is new; the VCO memory, read
on every clock, then takes most of the transmitter's SRAM dynamic power (§ 6.6
there).

**No memory at all.** The last step fixes the tables. `ble-tx-rom` and
`ble-tx-cordic` keep the transmitter of `ble-tx-pdu` and give the VCO the
project's tables from the first eighth of the wave, as `ble-tx-1--8` stores
them, but in logic: a ROM of 257 pairs, or an exact CORDIC. Measured on the
audited RTL (run `tx-vco`, `BRANCH_COMPARISON.md` § 4.4), the ROM is 593.2 µm²,
against 635.7 µm² of logic and 10 703.9 µm² of memory for the sine table of
`ble-tx-pdu`, and the transmitter 9 488.5 µm², −53.1 % against `ble-tx-pdu`;
the CORDIC is 2 317.9 µm², and its transmitter 11 121.3 µm². The tables are
then not programmable at all.

## 6. What this does not claim

- **The macros are OpenRAM layouts in FreePDK45**, an academic PDK, generated
  without DRC/LVS and never placed with the logic; a commercial SRAM compiler
  would give other absolute areas. The comparison between geometries uses one
  tool, one version and one set of options.
- **Default layout options.** OpenRAM chose the column multiplexing of every
  memory; other choices, which might let the 64 × 64 with its mask route, were
  not tried.
- **Timing and power are OpenRAM's analytical model**, at the nominal corner
  only, not a SPICE characterisation. Its power does not tell a read from an
  idle clock, so it cannot rank `ble-tx-sin2`, which reads twice per sample,
  against `ble-tx-1--8`, which reads once; § 6.6 of `BRANCH_COMPARISON.md`
  measures the 512 × 8 macro with SPICE (1.07 pJ per read), not the
  256 × 16 one.
- **No RTL yet.** The logic each alternative adds is estimated, not measured;
  each branch will measure it when it is built, with the validation of
  `ble-tx-sin8` (module lockstep, mutants, gate-level lockstep against
  upstream).

## 7. Reproducing

From WSL, at the root of `ble-tx-sin8-1rw` (or of a measurement branch, which
has the same script):

```bash
scripts/area/run_openram.sh <label> \
  sram_1rw_16x512_m8 sram_1rw_8x512 sram_1rw_16x256_m8 sram_1rw_32x128_m8 sram_1rw_64x64_m8 \
  sram_1rw_16x512 sram_1rw_16x256 sram_1rw_32x128 sram_1rw_64x64
```

The macro name is `sram_<ports>_<word bits>x<words>[_m<mask bits>]`. The run
takes 45 minutes: 1.5 to 5.3 minutes per macro, and 21 for the 64 × 64 without
the mask. The results, with each macro's LEF, `.lib` and log, are in
[`results/area/openram-1rw-sweep/`](../../results/area/openram-1rw-sweep/summary.md)
on `ble-tx-sin8-1rw`, `ble-tx-sin2` and the four measurement branches (`ble-opt`,
`ble-tx-table`, `ble-rx-dm`, `ble-tx-opt`). The script returns an error because
one macro (64 × 64 with the mask) failed; the other eight are complete.
