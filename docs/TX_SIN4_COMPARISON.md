> **Status update, 2026-10-05:** the corrected RTL and strict results are documented in [PRODUCT_VALIDATION.md](docs/Validation/PRODUCT_VALIDATION.md) and [ASIC_READINESS.md](docs/Validation/ASIC_READINESS.md). This document preserves historical implementation/measurement results. Its PPA values do not describe the corrected circuit; earlier equality/PASS claims are not product signoff.

# Quarter-wave TX experiment (`ble-tx-sin4`)

**Area result:** the complete TX occupies **54.4% less area** than `master`:
76,551.6 µm² instead of 167,731.4 µm², counting its standard cells and its
three SRAM macros. The quarter-wave logic adds 104.8 µm² of standard cells
(about 2.0%), and the two VCO memories shrink from 2048×8 to 512×8, which
saves 91,284.6 µm² of macro area, 871 times what the logic adds. The macros
were generated with OpenRAM in FreePDK45, the process of the Nangate45 cells
used for synthesis (see "Total TX area with SRAM macros" below).

This branch starts from `master` (`fae132e`). The only RTL change is in
`verilog/vco.v`: the TX sine and cosine tables each store 512 signed 8-bit
samples instead of 2048. The Gaussian FIR, RX demodulators, packet buffers,
and the rest of the controller remain the `master` implementation.

The 11-bit phase address selects a quadrant and an offset. For the second
and fourth quadrants, the offset is reflected; signs are selected from the
quadrant. At the 90-degree and 270-degree boundaries, sine and cosine samples
from address zero are exchanged. The sign and exchange controls are registered
on the same edge as the synchronous SRAM read, preserving its one-cycle latency.

Only addresses 0..511 of the existing sine and cosine write interfaces are
stored. Writes to addresses 512..2047 are ignored. This is exact for tables
with the symmetry used by `python/btlelib.py`, but the original independent
2048-entry programming capability is reduced. Firmware that writes complete
tables still works for symmetric waveforms and may later write only the first
512 entries of each table.

## Validation

`tests/test_vco_sin4.py` loads both full tables, then compares this VCO with
the `master` VCO on every cycle. It checks all 2048 phase addresses, further
signed phase jumps, gaps, a reset, and both `valid` signals. The sine/cosine
values are the project's 8-bit, 2048-entry waveform.

**Result:** 3072 cycles compared with no mismatch (Icarus Verilog 14).

```bash
IVERILOG=/path/to/iverilog VVP=/path/to/vvp python3 tests/test_vco_sin4.py
```

The whole controller was also compared with `master` at gate level, on every
output and every clock, in the five activity scenarios of run `tx-variants`
(`docs/Validation/BRANCH_COMPARISON.md` § 6.1). The tables were written in
full, 2048 entries each, as the firmware writes them, and 25 packets were
transmitted: **no mismatch**. The switching-activity proxy changes by 0 to
+0.4%.

## TX area

`tests/measure_vco_sin4_area.py` synthesizes `master` and this branch using
Yosys 0.68, ABC, and the same Nangate45 typical liberty as the project's
previous area reports. It blackboxes the SRAMs. The `ble-tx-table` column is
the existing result in that branch's
`results/area/all-branches/ble-tx-table/summary.md`.

| Configuration | TX cells | TX flip-flops | Cell area (µm²) | SRAM bits |
|---|---:|---:|---:|---:|
| `master` | 3,409 | 404 | 5,322.9 | 36,864 |
| `ble-tx-table` | 1,392 | 248 | 2,325.6 | 36,864 |
| `ble-tx-sin4` | 3,465 | 407 | 5,427.7 | 12,288 |

Compared with `master`, this branch removes **24,576 SRAM bits** from the TX
and adds **104.8 µm² of standard-cell logic**. Two 2048×8 VCO memories become
two 512×8 memories; the 4096-bit TX packet memory is unchanged. Thus the VCO
memory bits drop by 75%, and all TX memory bits drop by 66.7%.

The cell-area figure excludes SRAM physical area; the next section adds it.

```bash
YOSYS=/path/to/yosys ABC=/path/to/yosys-abc \
LIBERTY=/path/to/NangateOpenCellLibrary_typical.lib \
python3 tests/measure_vco_sin4_area.py
```

## Total TX area with SRAM macros

The TX has three RAMs: the COS and SIN tables of `vco.v` and the 512×8 packet
buffer of `btle_tx.v`. Each was replaced by an SRAM macro generated with
OpenRAM 1.2.48 in FreePDK45 (run `openram-tx`,
`docs/Validation/BRANCH_COMPARISON.md` § 4). Every one of them is written
and read in the same cycle, so the macro is dual-port: one read/write port and
one read port (1RW1R).

| Macro (1RW1R) | Size (µm) | Area (µm²) |
|---|---|---:|
| 2048×8 | 232.930 × 297.730 | 69,350.2 |
| 512×8 | 146.120 × 162.250 | 23,708.0 |

| Configuration | TX cells (µm²) | COS + SIN macros (µm²) | Packet buffer (µm²) | **Total TX (µm²)** | vs `master` |
|---|---:|---:|---:|---:|---:|
| `master` | 5,322.9 | 138,700.5 | 23,708.0 | **167,731.4** | — |
| `ble-tx-table` | 2,325.6 | 138,700.5 | 23,708.0 | **164,734.1** | −1.8% |
| `ble-tx-sin4` | 5,427.7 | 47,415.9 | 23,708.0 | **76,551.6** | **−54.4%** |

- **The memories are 97% of the TX**, so this memory change saves 30 times
  more TX area than `ble-tx-table`, which reduces standard-cell logic.
- **A quarter of the bits is a third of the area.** A 512×8 macro costs 34% of
  a 2048×8 one, because the decoders, sense amplifiers, drivers and rings do
  not shrink with the array.
- **With single-port macros**, a lower bound that no branch can use as is
  because the RTL writes and reads in the same cycle, `master` is 79,667.6 µm²
  and this branch 37,539.4 µm² (−52.9%).
- **The two reductions are independent.** They change different modules, so
  quarter-wave tables with the Gaussian table of `ble-tx-table` are estimated
  at 73,554 µm² (−56.1%). That combination is not built.

The macros are OpenRAM layouts in an academic PDK, generated without DRC/LVS
and not placed with the logic, so the absolute areas are indicative; a
commercial SRAM compiler would be denser. Chip price also depends on the
process, die size, yield and production volume, which this comparison does
not estimate.
