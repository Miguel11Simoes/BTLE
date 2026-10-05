# Static leakage of SRAM macros, FreePDK45, ngspice, every cell at 0, settled

OpenRAM's leakage run (UIC, every port deselected, average supply power) with every bitcell holding 0,
after one deselected clock, for 5 us instead of 10 ns (scripts/power/sram_leakage.py). The leakage is
the last window, 4.5-5 us; the first, 5-10 ns, is OpenRAM's own window.

| Macro | 5-10 ns (uW) | 0.5-1 us | 1-2 us | 3-4 us | 4-4.5 us | **Leakage, 4.5-5 us (uW)** |
|---|---:|---:|---:|---:|---:|---:|
| `sram_1rw_8x256` | 239.25 | 16.39 | 15.12 | 15.01 | 15.02 | **15.02** |
| `sram_1rw_8x512` | 95.93 | 25.23 | 25.10 | 25.09 | 25.11 | **25.11** |

The selected column of each bit (address 0): its bitline and its sense amplifier's input (V), at
10 ns, 1 us and 5 us:

| Macro | Bit | bitline | sense-amplifier input |
|---|---:|---|---|
| `sram_1rw_8x256` | 0 | 0.496 / 0.173 / 0.125 | 0.496 / 0.229 / 0.223 |
| `sram_1rw_8x256` | 1 | 0.496 / 0.173 / 0.125 | 0.496 / 0.229 / 0.223 |
| `sram_1rw_8x256` | 2 | 0.496 / 0.173 / 0.125 | 0.496 / 0.229 / 0.223 |
| `sram_1rw_8x256` | 3 | 0.496 / 0.173 / 0.125 | 0.496 / 0.229 / 0.223 |
| `sram_1rw_8x256` | 4 | 0.496 / 0.173 / 0.125 | 0.496 / 0.229 / 0.223 |
| `sram_1rw_8x256` | 5 | 0.496 / 0.173 / 0.125 | 0.496 / 0.229 / 0.223 |
| `sram_1rw_8x256` | 6 | 0.496 / 0.173 / 0.125 | 0.496 / 0.229 / 0.223 |
| `sram_1rw_8x256` | 7 | 0.496 / 0.173 / 0.125 | 0.496 / 0.229 / 0.223 |
| `sram_1rw_8x512` | 0 | 0.401 / 0.037 / 0.035 | 0.401 / 0.216 / 0.215 |
| `sram_1rw_8x512` | 1 | 0.401 / 0.037 / 0.035 | 0.401 / 0.216 / 0.215 |
| `sram_1rw_8x512` | 2 | 0.401 / 0.037 / 0.035 | 0.401 / 0.216 / 0.215 |
| `sram_1rw_8x512` | 3 | 0.401 / 0.037 / 0.035 | 0.401 / 0.216 / 0.215 |
| `sram_1rw_8x512` | 4 | 0.401 / 0.037 / 0.035 | 0.401 / 0.216 / 0.215 |
| `sram_1rw_8x512` | 5 | 0.401 / 0.037 / 0.035 | 0.401 / 0.216 / 0.215 |
| `sram_1rw_8x512` | 6 | 0.401 / 0.037 / 0.035 | 0.401 / 0.216 / 0.215 |
| `sram_1rw_8x512` | 7 | 0.401 / 0.037 / 0.035 | 0.401 / 0.216 / 0.215 |
