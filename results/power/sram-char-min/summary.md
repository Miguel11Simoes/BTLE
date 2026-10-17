# SRAM macros characterized with SPICE, FreePDK45

OpenRAM's measures: the average supply power of one clock cycle, at the period shown. The energy
of an access is relative to a deselected clock of the same port, (P_access - P_deselected) x period;
a deselected clock costs its own energy beyond the leakage, (P_deselected - leakage) x period: the
macro gates its array with the chip select, not its clock buffers and input flip-flops.
The leakage is the settled one of run_sram_leakage.sh; OpenRAM's figure, the first 10 ns after a
power-up from 0 V, is shown beside it.

| Macro | Period (ns) | Leakage (uW) | OpenRAM's leakage (uW) | Write (pJ) | Read (pJ) | Port 1 read (pJ) | Deselected clock (pJ) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `sram_1rw_8x32` | 5 | 16.41 | 105.65 | 0.479 | 0.351 | - | +0.182 |
