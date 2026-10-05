# SRAM accesses and energy of the transmitter

Window: 100000 clocks of bb_clk = s00_axi_aclk (16 MHz), 6.25 ms, setup subtracted. Energies from the SPICE characterization of each OpenRAM macro (`/home/msmiguel/btle-runs/pduwe-int/results/power/sram-char/char.json`): every clock costs the energy of a deselected clock (the macro's clock buffers and input flip-flops), every access its energy relative to a deselected clock; dynamic power = their sum / window time, the clock part and the access part shown apart. Leakage: char.json's, the same in every scenario.

Not characterized (counts only, no energy): `sram_1rw1r_8x2048`, `sram_1rw1r_8x512`.

## Scenario rx

| Configuration | Memory | Macro | Writes | Reads | Deselected | Clocks (uW) | Accesses (uW) | Dynamic (uW) | Leakage (uW) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| master | packet buffer | `sram_1rw1r_8x512` | 100000 | 100000 | - | — | — | — | — |
| master | VCO cos table | `sram_1rw1r_8x2048` | 100000 | 100000 | - | — | — | — | — |
| master | VCO sin table | `sram_1rw1r_8x2048` | 100000 | 100000 | - | — | — | — | — |
| ble-tx-pdu | packet buffer | `sram_1rw_8x256` | 100000 | 0 | 0 | 5.17 | 14.22 | 19.40 | 15.02 |
| ble-tx-pdu | VCO quarter sine table | `sram_1rw_8x512` | 0 | 100000 | 0 | 5.95 | 17.08 | 23.03 | 25.11 |
| ble-tx-pdu-we | packet buffer | `sram_1rw_8x256` | 0 | 0 | 100000 | 5.17 | 0.00 | 5.17 | 15.02 |
| ble-tx-pdu-we | VCO quarter sine table | `sram_1rw_8x512` | 0 | 100000 | 0 | 5.95 | 17.08 | 23.03 | 25.11 |

## Scenario tx

| Configuration | Memory | Macro | Writes | Reads | Deselected | Clocks (uW) | Accesses (uW) | Dynamic (uW) | Leakage (uW) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| master | packet buffer | `sram_1rw1r_8x512` | 100000 | 100000 | - | — | — | — | — |
| master | VCO cos table | `sram_1rw1r_8x2048` | 100000 | 100000 | - | — | — | — | — |
| master | VCO sin table | `sram_1rw1r_8x2048` | 100000 | 100000 | - | — | — | — | — |
| ble-tx-pdu | packet buffer | `sram_1rw_8x256` | 99405 | 595 | 0 | 5.17 | 14.22 | 19.39 | 15.02 |
| ble-tx-pdu | VCO quarter sine table | `sram_1rw_8x512` | 0 | 100000 | 0 | 5.95 | 17.08 | 23.03 | 25.11 |
| ble-tx-pdu-we | packet buffer | `sram_1rw_8x256` | 612 | 595 | 98793 | 5.17 | 0.17 | 5.34 | 15.02 |
| ble-tx-pdu-we | VCO quarter sine table | `sram_1rw_8x512` | 0 | 100000 | 0 | 5.95 | 17.08 | 23.03 | 25.11 |

## Scenario mixed

| Configuration | Memory | Macro | Writes | Reads | Deselected | Clocks (uW) | Accesses (uW) | Dynamic (uW) | Leakage (uW) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| master | packet buffer | `sram_1rw1r_8x512` | 100000 | 100000 | - | — | — | — | — |
| master | VCO cos table | `sram_1rw1r_8x2048` | 100000 | 100000 | - | — | — | — | — |
| master | VCO sin table | `sram_1rw1r_8x2048` | 100000 | 100000 | - | — | — | — | — |
| ble-tx-pdu | packet buffer | `sram_1rw_8x256` | 99712 | 288 | 0 | 5.17 | 14.22 | 19.39 | 15.02 |
| ble-tx-pdu | VCO quarter sine table | `sram_1rw_8x512` | 0 | 100000 | 0 | 5.95 | 17.08 | 23.03 | 25.11 |
| ble-tx-pdu-we | packet buffer | `sram_1rw_8x256` | 306 | 288 | 99406 | 5.17 | 0.08 | 5.26 | 15.02 |
| ble-tx-pdu-we | VCO quarter sine table | `sram_1rw_8x512` | 0 | 100000 | 0 | 5.95 | 17.08 | 23.03 | 25.11 |

## Scenario idle

| Configuration | Memory | Macro | Writes | Reads | Deselected | Clocks (uW) | Accesses (uW) | Dynamic (uW) | Leakage (uW) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| master | packet buffer | `sram_1rw1r_8x512` | 100000 | 100000 | - | — | — | — | — |
| master | VCO cos table | `sram_1rw1r_8x2048` | 100000 | 100000 | - | — | — | — | — |
| master | VCO sin table | `sram_1rw1r_8x2048` | 100000 | 100000 | - | — | — | — | — |
| ble-tx-pdu | packet buffer | `sram_1rw_8x256` | 100000 | 0 | 0 | 5.17 | 14.22 | 19.40 | 15.02 |
| ble-tx-pdu | VCO quarter sine table | `sram_1rw_8x512` | 0 | 100000 | 0 | 5.95 | 17.08 | 23.03 | 25.11 |
| ble-tx-pdu-we | packet buffer | `sram_1rw_8x256` | 0 | 0 | 100000 | 5.17 | 0.00 | 5.17 | 15.02 |
| ble-tx-pdu-we | VCO quarter sine table | `sram_1rw_8x512` | 0 | 100000 | 0 | 5.95 | 17.08 | 23.03 | 25.11 |

## Scenario idle0

| Configuration | Memory | Macro | Writes | Reads | Deselected | Clocks (uW) | Accesses (uW) | Dynamic (uW) | Leakage (uW) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| master | packet buffer | `sram_1rw1r_8x512` | 100000 | 100000 | - | — | — | — | — |
| master | VCO cos table | `sram_1rw1r_8x2048` | 100000 | 100000 | - | — | — | — | — |
| master | VCO sin table | `sram_1rw1r_8x2048` | 100000 | 100000 | - | — | — | — | — |
| ble-tx-pdu | packet buffer | `sram_1rw_8x256` | 100000 | 0 | 0 | 5.17 | 14.22 | 19.40 | 15.02 |
| ble-tx-pdu | VCO quarter sine table | `sram_1rw_8x512` | 0 | 100000 | 0 | 5.95 | 17.08 | 23.03 | 25.11 |
| ble-tx-pdu-we | packet buffer | `sram_1rw_8x256` | 0 | 0 | 100000 | 5.17 | 0.00 | 5.17 | 15.02 |
| ble-tx-pdu-we | VCO quarter sine table | `sram_1rw_8x512` | 0 | 100000 | 0 | 5.95 | 17.08 | 23.03 | 25.11 |

## Totals: the transmitter's SRAMs, dynamic power (uW)

| Configuration | rx | tx | mixed | idle | idle0 | of which clocks | Leakage (uW) |
|---|---:|---:|---:|---:|---:|---:|---:|
| master | — | — | — | — | — | — | — |
| ble-tx-pdu | 42.43 | 42.42 | 42.42 | 42.43 | 42.43 | 11.12 | 40.13 |
| ble-tx-pdu-we | 28.20 | 28.37 | 28.28 | 28.20 | 28.20 | 11.12 | 40.13 |

— : a memory of that configuration is not characterized. The clock part is the same in every scenario: every memory takes every clock.

## Check failures

- incomplete energy characterization: sram_1rw1r_8x2048, sram_1rw1r_8x512

CHECKS: FAIL
RESULT: FAIL
