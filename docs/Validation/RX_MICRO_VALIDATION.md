# Validation of one stored phase and an 8-bit demodulator (`ble-rx-micro`)

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `ble-rx-micro`, cut from `ble-rx-best` (`d9080f36`)  
**Base:** tag `upstream-baseline` (`8540186`); reference: `ble-rx-best` and the models of [RX_PER.md](RX_PER.md)  
**Date:** 2026-10-21  
**Author:** Miguel Simões  
**Status:** executed. RTL commit `745e4bba` (no RTL changed after it); harness `3b26eb43`; campaigns
[`micro-campaign.txt`](../../results/validation/micro-campaign.txt) to [`micro4-campaign.txt`](../../results/validation/micro4-campaign.txt).

---

## Purpose

`ble-rx-micro` applies to `ble-rx-best` the two levers of [RX_PER.md](RX_PER.md) § 3 that cost least
sensitivity per µm²:

1. **a demodulator of 8 bits**: the samples shifted right by `RX_IQ_SHIFT` and saturated to
   `RX_IQ_BITS` bits before it;
2. **one stored phase**, chosen when the Access Address is found (the model `centre1`), instead of 8
   decoders and the choice by the CRC at the end.

Neither is equivalent to `ble-rx-best`: their evidence is the packet-error-rate harness, packet by packet
against their model, and the cost is measured against `ble-rx-best` on the same samples. This report
records the change, that evidence, the area and the cost.

## 1. The change

- **`verilog/rx_one_phase.v`** (new):
  - **the choice**: the first phase p0 to find the Access Address opens a window of one symbol; the
    phases that find it in that window (p0 … p0+7, in the order of their samples) are recorded in a mask;
    the window closes with the hit of p0+7, the clock after its bit, and the phase chosen is the middle
    of those found, the (n/2)-th in sample order (the later of two middles): `centre1`'s rule;
  - **the decoding**: one `rx_decoder_shared` with `NUM_PHASE = 1`, fed the chosen phase **one bit
    late** (`last_bit` keeps the latest bit of every phase, 8 flip-flops): its first bit is the last bit
    of the phase's Access Address, with `hit_flag` the clock after, which restarts its scrambler and CRC
    as the Access Address search does. The window closes before the chosen phase's next bit whichever
    phase it is, so the choice needs no buffer. The packet ends one symbol later than with 8 decoders;
    the bits decoded are the same;
  - **the packet**: 42 octets in registers (header, payload, CRC), written at `octet_valid`, one past 42
    dropped, read on `clkb` with one clock of latency, as `sdpram_two_clk`. **No SRAM macro.**
- **`verilog/btle_rx.v`**: `RX_ONE_PHASE` (default 1; 0 keeps the 8 decoders, the CRC selection and the
  packet RAM of `ble-rx-best`, textually, in `gen_eight`), `RX_IQ_BITS` (default 8) and `RX_IQ_SHIFT`
  (default 0); the demodulator, `gfsk_demodulation_shared`, is unchanged and instantiated at
  `RX_IQ_BITS`. The input port stays 16 bits.
- `btle_phy.v`, `btle_controller.v`: `RX_ONE_PHASE` passed down. `run_lint.py` knows it.

**The scale.** 8 bits with no shift fit the scale of `btlelib.py` and the matrix (a peak of 127). A front
end that gives 12-bit samples needs `RX_IQ_SHIFT = 4` at the same 8 bits, and the level its AGC holds
decides how much headroom is left; that is a choice per front end, not made here.

## 2. Evidence

| Check | Result |
|---|---|
| **Both levers** (defaults) against the model `centre1` at 8 bits ([`rx_per_centre1_q8s0`](../../results/validation/micro/rx_per_centre1_q8s0/result.txt)) | **9 600/9 600 packets the same**, 0 wrong PDUs; mutants **4/4**: `centre_first` (the first of the window), `centre_earlier` (the earlier middle), `decoder_current_bit`, `wrap_not_saturate` |
| **The width alone** (`RX_ONE_PHASE=0`) against `best8` at 8 bits ([`rx_per_best8_q8s0`](../../results/validation/micro/rx_per_best8_q8s0/result.txt)) | **9 600/9 600 the same**, 0 wrong PDUs |
| **`RX_ONE_PHASE=0`, 16 bits** against `best8` ([`rx_per_best8`](../../results/validation/micro/rx_per_best8/result.txt)) | **9 600/9 600 the same**, the 2 604 losses of `ble-rx-best`'s run `rx-per`; mutants **3/3** |
| Lint gate (Verilator 5.020, `--Wall`) ([`micro-lint`](../../results/validation/micro-lint/result.json)) | **64/64 configurations** (with `RX_ONE_PHASE`), 12 reviewed exceptions, none new |
| The product audit's matrix, defaults ([`micro-matrix-product`](../../results/validation/micro-matrix-product/rx_regression/summary.tsv)) | 214 PASS, 56 ERROR: the 50 data-channel cases, as on `ble-rx-best`, and **3 advertising packets** (`ex0_snr12_ppm20_d0`, `_d5`, `ex0_snr8_ppm0_d0`; `btle_rx_tb` and `btle_controller_tb` each) that the reference receives and one stored phase loses: the cost of § 4, at the threshold, not a fault |

A window closed one phase early (the hit of p0+7 not counted) shows in no packet: a window reaches p0+7
only when the signal is strong, where every phase decodes the packet. The packet harness leaves that
mutant out (`a6009798`); the lockstep and the proof of § 2.2 and § 2.3 catch it.

### 2.1 Lockstep against the 8 decoders (`rx_micro_lockstep`)

[`micro2/rx_micro_lockstep`](../../results/validation/micro2/rx_micro_lockstep/result.txt):
`btle_rx` with its defaults, and as reference `rx_decoder_shared` with 8 phases (proved equal to the 8
`btle_rx_core` chains, `formal_shared`) fed the dut's own bits, `bit_valid` and Access Address hits and
restarted with it: what `ble-rx-best`'s decoders decode from the same bits. Checked on every clock: the
phase chosen against an independent model of the rule (a list in time order, not the RTL's mask) and the
clock it is chosen in; every octet against the reference's octet of the same index for that phase; at
the end the CRC verdict, the length and the number of octets; btle_rx's outputs and every packet word
read. Stimulus: the `rx_per` segments at 0 and 20 ppm, 8 to 20 dB.

| | |
|---|---|
| Points | **10/10 PASS**: 2 000 packets, 1 981 choices, 78 233 octets, 1 967 ends (1 321 with the CRC right), 48 184 packet words; no restart of the chosen phase by a later hit |
| Mutants | **6/6**: `centre_first`, `centre_earlier`, **`window_short`**, `decoder_current_bit`, `hit_every_bit`, `words_38` |

The first campaign ([`micro/rx_micro_lockstep_first`](../../results/validation/micro/rx_micro_lockstep_first/result.txt))
had a mutant `hit_with_bit` (`dec_hit <= first`) that no check caught: it is equivalent (a hit acts in
the decoder only with a bit), and was replaced by `hit_every_bit` (`6b4df762`).

### 2.2 Formal (`formal_micro`)

[`micro2/formal_micro`](../../results/validation/micro2/formal_micro/result.txt) and
[`micro2-n2/formal_micro`](../../results/validation/micro2-n2/formal_micro/result.txt) (SBY, bitwuzla;
yosys `equiv`):

| Task | What | Result |
|---|---|---|
| `best_equiv` | `btle_rx` with `RX_ONE_PHASE = 0`, 16 bits ≡ `ble-rx-best`'s `btle_rx` (`7b2ebdc5`), flattened with the same submodules | **PASS, unbounded**: 4 549 `$equiv` cells proven |
| `sat8`, `sat8s4` | the demodulator's input is the sample (shifted by 0 or 4) saturated to 8 bits, every 16-bit sample | **PASS** |
| `w4w8` | the demodulator at 4 bits ≡ at 8 bits on samples that fit, real multipliers | **PASS, unbounded** (k-induction with invariants) |
| `w8w16` | the same at 8 against 16 bits, the real widths | **PASS, bounded** (BMC, 12 clocks from reset); unbounded (`w8w16p`) did not close: its base case stalled at 11 clocks; depth 24 did not finish in 2 h |
| `phase_n4` | `rx_one_phase` against `rx_decoder_shared` with every phase, scaled to 4 phases: the choice, every octet, length, the end | **PASS, bounded** (BMC 120: the choice and the first octets) |
| `phase_n2` | the same with 2 phases | **PASS, bounded** (BMC 200: a whole packet, through its CRC and `decode_end`) |
| Mutants | `early_or`, `sat_wrap`, `sat_max_off`, `product_narrow`, `centre_first`, **`window_short`**, `decoder_current_bit`, `crc_init_wrong` | **9/9 detected** (8 in `micro2`, 1 in `micro2-n2`) |

`phase_n2` first failed (`micro2`): the miter counted the octets in a register and missed the last one,
which comes in the clock of `decode_end`; the miter was corrected (`3b26eb43`), not the RTL, and the
lockstep had checked that count with the octet included. The first campaign
([`micro/formal_micro_first`](../../results/validation/micro/formal_micro_first/result.txt)) did not elaborate
`one_phase_miter.sv` (`expect` is a keyword).

### 2.3 Gate level

[`micro-gate/rx_per_centre1_q8s0_gate`](../../results/validation/micro-gate/rx_per_centre1_q8s0_gate/result.txt):
`btle_rx` mapped to Nangate45 (the flow of the area and activity runs, `synth_gate_netlist.sh TOP=btle_rx`),
its cells simulated by models from the liberty, the 9 600 packets of § 2: **the same packets as the
model, 0 disagreements** (6 993.7 µm², the area run's netlist).

### 2.4 The front end's scale

[`micro-scale/`](../../results/validation/micro-scale/): the 24 points again, the whole input scaled
(`LEVEL_DB`), each run against its own model (all **9 600/9 600 the same**). +24 dB is a 12-bit ADC's
scale (a peak of 2 032); `RX_IQ_SHIFT = 4` takes it to 8 bits.

| Input level | Demodulator | Packets lost of 9 600 |
|---|---|---:|
| +24 dB | 16 bits | 3 353 |
| +24 dB | **8 bits, `RX_IQ_SHIFT = 4`** | 3 380 |
| +12 dB (the AGC 12 dB low) | 8 bits, shift 4 | 3 329 |
| +18 dB (6 dB low) | 8 bits, shift 4 | 3 403 |
| +30 dB (6 dB high) | 8 bits, shift 4 | **4 057**: saturated (18.5 % lost at 0 ppm, 14 dB, against 0) |

The 8 bits cost 27 packets at the ADC's scale and hold down to 12 dB below it; above it the 8 bits
saturate. **The AGC must keep the peak within the ADC's full scale** (which it must anyway), with
`RX_IQ_SHIFT` = ADC bits − 8.

### 2.5 Timing and switching activity

Timing ([`results/timing/micro/ble-rx-micro/`](../../results/timing/micro/ble-rx-micro/summary.txt),
`run_sta.sh`, against corrected `master`): `btle_rx` **1.459 ns** (`master` 1.991 ns, `ble-rx-best` 1.997 ns),
the controller 3.340 ns, its worst path the transmitter's Gaussian tail as on every branch; 62.5 ns at
16 MHz. The register file of the packet and its `clkb` read are in it; there is no macro left untimed.

Activity ([`results/power/micro/ble-rx-micro/`](../../results/power/micro/ble-rx-micro/summary.md),
`run_activity.sh RX_DIFFERS=1`, the vectors of run `all-branches`, against corrected `master`): every
scenario ran; the receiver's outputs differ from `master`'s by design (one symbol later, other packets),
so they are counted, not compared (`RX_DIFFERS`). Data + clock switched capacitance, a proxy, not power:

| Scenario | `rx` | `tx` | `mixed` | `idle` | `idle0` |
|---|---:|---:|---:|---:|---:|
| `ble-rx-micro` vs `master` | −31.8 % | −21.2 % | **−31.8 %** | −32.8 % | −22.7 % |
| `ble-rx-best` vs `master` (§ 16 of the comparison) | +10.0 % | +11.7 % | +9.6 % | +10.4 % | +12.3 % |

The clock load falls 26.9 % (584 flip-flops fewer than `ble-rx-best`, 1 281 fewer than `master` in the
receiver) and the receiver's data switching with it.

## 3. Area

[`results/area/micro/ble-rx-micro/`](../../results/area/micro/ble-rx-micro/summary.md), the flow of every
earlier run; `ble-rx-best` from run `rx-best`.

| | `ble-rx-best` | `ble-rx-micro` |
|---|---:|---:|
| Std cells, `btle_rx` | 7 281 | **3 668** |
| Flip-flops, `btle_rx` | 1 371 | 787 |
| Cell area, `btle_rx` (µm²) | 12 780.0 | **6 993.7** |
| RX packet RAM macro (µm²) | 8 116.5 (336 × 8) | **none** (42 octets in registers, inside `btle_rx`) |
| **Receiver: cells + macros (µm²)** | 20 896.5 | **6 993.7 (−66.5 %)** |
| Std cells / cell area, `btle_controller` | 22 983 / 38 700.1 µm² | 19 671 / 33 226.1 µm² |
| SRAM macros, controller | 8 | 7 |

Against corrected `master` (238 283.0 µm², § 16 of the comparison) the receiver is **−97.1 %**. The
per-module rows of `gfsk_demodulation_shared` and `rx_decoder_shared` in the summary are those modules
synthesised alone at their own defaults (16 bits, 8 phases), not as `btle_rx` uses them.

## 4. The cost

Packets lost, %, on the same samples (seed 1, 400 per point): `ble-rx-best` (run `rx-per`), the width alone,
and `ble-rx-micro`.

| ppm | SNR (dB) | `ble-rx-best` | 8 bits, 8 phases | **`ble-rx-micro`** |
|---:|---:|---:|---:|---:|
| 0 | 10 | 3.0 | 3.8 | 27.8 |
| 0 | 12 | 0.0 | 0.0 | 2.8 |
| 0 | 14 | 0.0 | 0.0 | 0.0 |
| 10 | 12 | 0.2 | 0.5 | 10.2 |
| 10 | 14 | 0.0 | 0.0 | 0.5 |
| 20 | 12 | 11.8 | 14.0 | 45.2 |
| 20 | 14 | 0.0 | 0.0 | 7.8 |
| 20 | 16 | 0.0 | 0.0 | 0.5 |
| 30 | 16 | 1.8 | 2.2 | 11.2 |
| 30 | 20 | 0.0 | 0.0 | 0.0 |

(every point: [`summary.tsv`](../../results/validation/micro/rx_per_centre1_q8s0/summary.tsv)). The width
costs little at this scale (2 640 against 2 604 packets lost over the 24 points); the one stored phase
costs about 2 dB: `ble-rx-micro` loses at 12 dB what `ble-rx-best` loses at 10, at 14 dB what it loses at
12 with 20 ppm, and needs 20 dB at 30 ppm where `ble-rx-best` needs 16. With a strong signal (14 dB and
more up to 10 ppm, 16 dB up to 20 ppm) both lose no packet or almost none.

## 5. Reproducing

From WSL, at the root of `ble-rx-micro`:

```bash
QBITS=8 QSHIFT=0 scripts/validation/rx_per/run_rx_per.sh micro 400 centre1
QBITS=8 QSHIFT=0 DUT_PARAMS='RX_ONE_PHASE=0' scripts/validation/rx_per/run_rx_per.sh micro 400 best8
DUT_PARAMS='RX_ONE_PHASE=0 RX_IQ_BITS=16' scripts/validation/rx_per/run_rx_per.sh micro 400 best8
scripts/area/run_area.sh micro/ble-rx-micro
python3 scripts/validation/run_lint.py --output results/validation/micro-lint
scripts/validation/run_rx_regression.sh micro-matrix-product fca6ac6
```
