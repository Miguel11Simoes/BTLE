# SRAM macros characterized with SPICE, FreePDK45

OpenRAM's measures: the average supply power of one clock cycle, at the period shown. The energy
of an access is relative to a deselected clock of the same port, (P_access - P_deselected) x period;
a deselected clock costs its own energy beyond the leakage, (P_deselected - leakage) x period: the
macro gates its array with the chip select, not its clock buffers and input flip-flops.
The leakage is OpenRAM's figure, the first 10 ns after a power-up from 0 V (sram_leakage.py), so the
last column is a signed diagnostic, not the energy of a deselected clock.

| Macro | Period (ns) | Leakage (uW) | Write (pJ) | Read (pJ) | Port 1 read (pJ) | Deselected clock vs leakage (pJ) |
|---|---:|---:|---:|---:|---:|---:|
| `sram_1rw_8x256` | 5 | 13.26 | 0.921 | 0.848 | - | +0.316 |
| `sram_1rw_8x512` | 5 | 3463.24 | 9.821 | 1.111 | - | -16.844 |
