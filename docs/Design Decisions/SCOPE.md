# Scope: a reconfigurable RISC-V in the BLE baseband

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `risc-v-ble`  
**Base:** tag `upstream-baseline` (`8540186`)  
**Date:** 2026-09-18  
**Author:** Miguel Simões  
**Status:** draft. Four decisions are open (section 3).  

---

## Purpose

This document records the starting point and the questions that must be
answered **before** any RTL changes. Anything still undecided is marked as
open, and it must be decided here, in writing, not in code.

## Revision history

| Date | Change |
|---|---|
| 2026-09-18 | First version (Portuguese, `docs/SCOPE.md`). |
| 2026-09-18 | Moved to `Design Decisions/`, rewritten in English, and corrected after reading the code: the hardware LL is a placeholder, the FPGA system is receive-only, and the OpenLane flow did not close. See section 2. |

## 1. What upstream provides

Verified in the sources; details in
[../Architecture/UPSTREAM_ARCHITECTURE.md](../Architecture/UPSTREAM_ARCHITECTURE.md).

| Block | Files | Role |
|---|---|---|
| PHY | `btle_phy.v`, `btle_rx.v`, `btle_rx_core.v`, `btle_tx.v` | Receive and transmit chains, 16 MHz, 8× oversampling |
| Modulation | `gfsk_modulation.v`, `gfsk_demodulation.v`, `gauss_filter.v`, `vco.v` | GFSK; taps and COS/SIN table writable at runtime |
| Bit processing | `crc24*.v`, `scramble*.v`, `search_unique_bit_sequence.v`, `bit_repeat_upsample.v` | CRC-24, whitening, access-address detection |
| LL wrapper | `btle_ll.v` | AXI-lite registers, RX PDU RAM, counters, timestamps; placeholder state machine |
| Top | `btle_controller.v`, `btle_controller_wrapper.v` | PHY + LL + clock crossing + AGC/IQ capture |
| Firmware | `firmware/btle_ll.c` | Linux process on the Zynq ARM: RX configuration and packet forwarding |
| Flows | `fpga/` (AntSDR, AntSDR E200, SDRPi), `open_btle_baseband_chip/` | Vivado; OpenLane2 on SKY130 (partial) |
| Model | `python/btlelib.py` | Bit-true reference model and test-vector generator |

## 2. What the code changed in the first version of this scope

The first version said the natural place for the RISC-V was "replacing or
sitting beside the LL state machine", and that OpenLane gave an area reference
"up to GDSII". Reading the code changed three things:

1. **There is no Link Layer to migrate.** The state machine in `btle_ll.v`
   steps through its states on every transmitted packet and makes no
   protocol decision. The firmware on the ARM configures RX and forwards
   packets, and never transmits. The system is a sniffer. A RISC-V Link Layer
   has to be **written**, and the hardware/software split is a design choice,
   not a relocation.
2. **The PHY boundary is cleaner than it looked.** `btle_controller` already
   has a complete cycle-level PHY interface (the `ext_*` ports, selected by
   `baremetal_phy_intf_mode`). A new controller can attach there directly, or
   through the existing AXI-lite register file.
3. **There is no closed area reference yet.** Upstream reports that post-PnR
   STA fails for `btle_rx_core` and global routing fails for the whole design.
   The "before" number the thesis needs has to be produced, either by closing
   the flow or by using FPGA utilisation as the reference.

## 3. The central question and the open decisions

**Which parts of an active BLE Link Layer run as software on a RISC-V core, and
which stay in fixed hardware?**

The PHY (GFSK, CRC, whitening, access-address search) must deliver a result
every sample at 16 MHz, which a scalar core cannot do, so it stays in hardware.
Everything above it is open:

- [ ] **D1. The hardware/software split.** Candidates for software:
      advertising schedule, scan and connection state machines, channel
      selection and hopping, PDU building and parsing, control procedures.
      Candidates for hardware assistance: the T_IFS turnaround, event timers,
      automatic ACK/NESN/SN handling.
- [ ] **D2. The core.** One option is Snitch, which is familiar from the other
      thesis line. The other is a small core such as PicoRV32 or Ibex, which
      `py2hwsw` already ships as a submodule. The choice drives area,
      interrupt latency and tooling.
- [ ] **D3. What "reconfigurable" means.** Runtime parameters (upstream
      already has these: taps, COS/SIN table, AA, CRC init), replaceable
      firmware, or reconfigurable logic. These are three different claims and
      each needs its own proof.
- [ ] **D4. The metric the thesis defends.** Area, energy per packet, LL
      response latency, or flexibility shown through a use case.

## 4. Requirements that will be hard

- **BLE timing.** T_IFS is 150 µs ± 2 µs between packets. A core running
  software must meet it deterministically, from the RX CRC result to the first
  TX sample. This is a requirement, not an implementation detail, and upstream
  has nothing that meets it.
- **PHY↔core interface.** It needs a written specification: registers or
  ports, interrupts, PDU buffers, and which side owns each memory. The two
  existing candidates are the `ext_*` port set and the AXI-lite map in
  [../Architecture/LL_REGISTER_MAP.md](../Architecture/LL_REGISTER_MAP.md).
- **Proof of equivalence.** The PHY must behave exactly as before. The
  reference is the Python model and the upstream testbenches, run with the
  same stimuli before and after
  ([../Validation/UPSTREAM_TEST_INVENTORY.md](../Validation/UPSTREAM_TEST_INVENTORY.md)).

## 5. Relation to the other thesis line

This line is **separate** from `snitch_cluster_tese`, and the two repositories
stay apart. If BLE later becomes the transport for alerts from the predictive
maintenance SoC, that integration is a milestone of its own, and it only
starts once each side works on its own.

## 6. Proposed order of work

1. Close decisions D1–D4 here, in writing.
2. Reproduce upstream as it is: the Python model, the unit testbenches, the
   top-level testbench, and one synthesis flow (Vivado or OpenLane). This
   gives a behaviour reference **and** an area reference
   ([../Guides/REPRODUCE_UPSTREAM.md](../Guides/REPRODUCE_UPSTREAM.md)).
3. Specify the PHY↔core interface before writing RTL.
4. Integrate the core with a minimal firmware that does what `btle_ll.c` does
   today (receive and report), and prove that the PHY did not regress.
5. Add active LL functions one at a time, advertising first, with the step-2
   reference as the oracle and T_IFS measured at every step.

Every step keeps its evidence, in the same spirit as the other line: what
passed, what was not tested, and what is not claimed.
