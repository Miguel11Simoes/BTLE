# The packet buffer deselected, with the words the RTL leaves in it (sram_1rw_8x256, FreePDK45, ngspice)

Static power once the macro has settled (sram_leakage.py --data, 4.5-5 us). The unknown words (never
written) at 0 or random; the column that the address selects, per bit: how many of its cells hold 1, and
its sense amplifier's input at 5 us (between 0.3 and 0.7 V: a crossover current).

| Case | Address | Data in | Unknown words | Ones in the selected columns | Sense-amplifier inputs at 5 us (V) | Static power (uW) |
|---|---:|---:|---:|---|---|---:|
| idle.zero | 0 | 0 | 255 | 0 0 0 0 0 0 0 0 of 32 | 0.22 0.22 0.22 0.22 0.22 0.22 0.22 0.22 | **15.0** |
| idle.seed1 | 0 | 0 | 255 | 17 15 13 17 12 18 14 20 of 32 | 0.31 0.30 0.28 0.31 0.28 0.32 0.29 0.34 | **25.3** |
| idle.seed2 | 0 | 0 | 255 | 12 17 15 17 14 16 21 22 of 32 | 0.28 0.31 0.30 0.31 0.29 0.31 0.35 0.36 | **28.2** |
| tx.zero | 16 | 121 | 222 | 3 2 3 2 2 2 4 0 of 32 | 0.24 0.23 0.23 0.24 0.24 0.24 0.25 0.22 | **15.7** |
| tx.seed1 | 16 | 121 | 222 | 21 15 18 16 15 17 16 9 of 32 | 0.39 0.30 0.32 0.35 0.34 0.36 0.35 0.26 | **34.8** |
| tx.seed2 | 16 | 121 | 222 | 14 18 19 17 14 20 17 16 of 32 | 0.33 0.32 0.33 0.35 0.33 0.38 0.36 0.31 | **35.6** |
