# ASIC readiness - 2026-10-06

**Status: NOT READY for tapeout or a market release.** The selected target is ASIC; the foundry/PDK and the product boundary (PHY/baseband or a complete controller/Link Layer) are not decided. Passing the lint and digital campaigns in [LINT_CLOSURE.md](LINT_CLOSURE.md), [RF_INTERFACE_REVIEW.md](RF_INTERFACE_REVIEW.md) and [PRODUCT_VALIDATION.md](PRODUCT_VALIDATION.md) does not close the items below.

## Digital defects repaired

- Validation now rejects simulator/prover errors, empty verdicts, missing stimuli, incomplete/unknown outputs, shared failures and zero-work campaigns. Saved output files in an input directory cannot stand in for results from a new simulator invocation.
- The receive model validates the declared complete PDU and its CRC. It no longer moves the CRC boundary to fit a truncated capture, exports repeated fake decisions as padding, or returns rejected RAM bytes as an accepted PDU. Noise cases still supply real demodulator and RX-core input vectors.
- The TX emits the 16 samples needed to finish the Gaussian convolution. Its last marker occurs on the final tail sample. The correction uses the same coefficient epoch as the FIR, including a coefficient write on that clock.
- Bit repetition and the final marker restart from each input bit. A free-running counter previously made completion depend on idle time between packets; a repeated-packet test reproduces the old failure.
- Channel 0 and a CRC initialization of zero are honored. Hardware no longer silently substitutes channel 63 or seed 0x555555.
- Reserved registers 42-47 and reserved event counter 4 read zero. The register read multiplexer uses combinational assignments.
- Controller verification requires completed transmissions and receptions, known handshakes and valid TX samples, and known meaningful AXI read data. A deliberately wrong CRC seed produces complete invalid packets for rejection tests. Random noise is not treated as proof that a mutation was exercised.
- Harness fault-injection tests require evidence that the intended fake simulator/prover actually ran. A missing Git reference, compilation failure or vector-generation failure cannot satisfy a simulator-failure test.

- SRAM summaries reject missing counts/characterization and invalid numeric inputs. The characterization parser rejects empty campaigns, inconsistent periods and nonfinite measurements. Partial diagnostic reports have a failing exit status.

- RF receive-valid gaps are honored without changing the sample phase. Measurement tools reject incomplete timing, area and activity evidence; older activity reports with missing nets are not complete.

## Remaining engineering work

| Item | Current state | Evidence needed to close it |
|---|---|---|
| Product specification | Open | Required Bluetooth features/version, payload limits, PHY/LL/host split, register/interface contracts and supported operating modes |
| Technology | Open | Foundry, licensed PDK, standard-cell and IO libraries, memory macros, voltage/temperature/process corners and packaging |
| Lint | PASS for the documented controller configurations, with explicit exceptions | See [LINT_CLOSURE.md](LINT_CLOSURE.md): strict warnings, exact declaration-scoped exceptions, negative controls. This is not CDC/RDC signoff. |
| Clock and reset crossings | Not signed off | Clock/reset plan, CDC/RDC analysis, coherent multibit transfers, reset release and memory collision contracts |
| Protocol verification | Partial | Independent tests for the selected full feature set and limits; malformed/maximum-length traffic, state-machine recovery, sustained traffic and clock ratios |
| Formal and gate-level closure | Partial/historical | Proofs and post-synthesis checks for the final configuration and final RTL revision, with non-vacuity and mutation checks |
| PPA | Historical measurements | Re-synthesize and measure the corrected circuit with the selected macros and timing models; rerun activity/energy on that circuit |
| DFT/manufacturing test | Not implemented/signoff absent | Scan, ATPG coverage, memory BIST/repair as required, test clocks/resets and production test plan |
| Physical implementation | Not run for a selected PDK | Floorplan, power network, place/route, extracted setup/hold timing across corners, signal integrity, IR/EM, DRC/LVS/antenna/ERC and foundry signoff |
| Radio/product qualification | Not demonstrated | Defined RF front end, interoperability and relevant qualification/test evidence for the selected product |

Concrete limits already visible in the RTL:

- `clk_cross_bus` transfers a continuously changing bus through a dual-clock RAM at a constant address. Simulation equality is not a proof of coherent asynchronous transfer or metastability safety.
- `clock_domain_conversion_iq` now honors `rx_iq_valid_ext` gaps while preserving its related 2:1 sampling phase. The direct multibit crossing still requires a defined related-clock timing contract; arbitrary asynchronous clocks are not supported or signed off.
- Illegal encodings in the LL, RX and (where present) three-state CRC machines now return to idle with invalid output strobes cleared. Injection tests exercise that recovery. The one-bit CRC variant has no unused binary encoding. This RTL evidence does not establish physical fault tolerance or synthesis preservation of recovery logic.
- The AXI reset is used synchronously by AXI logic and asynchronously by the legacy UART. Its declaration has an explicit lint exception preserving the existing behavior; reset assertion/release timing and domain interactions still need RDC signoff.
- The independently checked Python packet model/test matrix covers legacy-shaped LE 1M packets (data payloads up to 31 bytes; additional advertising cases at 37). RTL has wider length fields in places. This report does not claim complete coverage of every modern Bluetooth packet format or a complete production Link Layer/HCI.
- Optimized branches retain their documented programming, table-symmetry, sample-rate, write-hold and packet-buffer restrictions. These must become enforced integration contracts for the chosen product.

The area, timing and activity numbers in earlier comparison documents describe earlier RTL. The tail and repetition fixes change the circuit and packet duration. **Do not use those historical numbers as signoff evidence for this revision.** The Yosys structural check is elaboration/driver consistency, not mapped timing or physical signoff.

The Bluetooth SIG describes product qualification as a separate process that must be completed before sale/distribution; these repository tests are not qualification evidence by themselves. See the [official qualification overview](https://www.bluetooth.com/develop-with-bluetooth/qualify/). A digital implementation flow also has distinct physical stages; see the [OpenROAD flow documentation](https://openroad-flow-scripts.readthedocs.io/en/latest/). Neither reference establishes that this chip has completed those stages.
