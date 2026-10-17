# Static leakage of SRAM macros, FreePDK45, ngspice, every cell at 0, settled

OpenRAM's leakage run (UIC, every port deselected, average supply power) with every bitcell holding 0,
after one deselected clock, for 5 us instead of 10 ns (scripts/power/sram_leakage.py). The leakage is
the last window, 4.5-5 us; the first, 5-10 ns, is OpenRAM's own window.

| Macro | 5-10 ns (uW) | 0.5-1 us | 1-2 us | 3-4 us | 4-4.5 us | **Leakage, 4.5-5 us (uW)** |
|---|---:|---:|---:|---:|---:|---:|
| `sram_1rw_8x32` | 133.82 | 28.36 | 17.75 | 16.39 | 16.41 | **16.41** |

The selected column of each bit (address 0): its bitline and its sense amplifier's input (V), at
10 ns, 1 us and 5 us:

| Macro | Bit | bitline | sense-amplifier input |
|---|---:|---|---|
| `sram_1rw_8x32` | 0 | 0.574 / 0.328 / 0.311 | 0.574 / 0.328 / 0.312 |
| `sram_1rw_8x32` | 1 | 0.574 / 0.328 / 0.311 | 0.574 / 0.328 / 0.312 |
| `sram_1rw_8x32` | 2 | 0.574 / 0.328 / 0.311 | 0.574 / 0.328 / 0.312 |
| `sram_1rw_8x32` | 3 | 0.574 / 0.328 / 0.311 | 0.574 / 0.328 / 0.312 |
| `sram_1rw_8x32` | 4 | 0.574 / 0.328 / 0.311 | 0.574 / 0.328 / 0.312 |
| `sram_1rw_8x32` | 5 | 0.574 / 0.328 / 0.311 | 0.574 / 0.328 / 0.312 |
| `sram_1rw_8x32` | 6 | 0.574 / 0.328 / 0.311 | 0.574 / 0.328 / 0.312 |
| `sram_1rw_8x32` | 7 | 0.574 / 0.328 / 0.311 | 0.574 / 0.328 / 0.312 |
