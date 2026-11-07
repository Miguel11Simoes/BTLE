# Packet error rate of the receiver under noise and frequency offset (`ble-rx-best`)

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `ble-rx-best`  
**Base:** tag `upstream-baseline` (`8540186`); the receiver model: `python/btlelib.py`  
**Date:** 2026-10-21  
**Author:** Miguel Simões  
**Status:** executed. Run `rx-per`: RTL of `7b2ebdc5` (no RTL changed), harness `scripts/validation/rx_per/`
at the hashes in [`provenance.txt`](../../results/validation/rx-per/rx_per_best8/provenance.txt).

---

## Purpose

Every receiver branch so far was proved equivalent to the one before it: formally, in lockstep, and
by the product audit's matrix. Three levers remain that are **not equivalent by design**, because they
change what the receiver decodes:

- **one stored phase**: the phase chosen when the Access Address is found, not by the CRC at the end;
- **fewer phase hypotheses** than the 8 sampling phases;
- **a narrower demodulator** than its 16-bit samples.

No proof or lockstep can be their evidence. The matrix cannot either: it holds 9 decoded advertising
packets (example 0 at SNR 20 and 12 dB with 0 and 20 ppm, and at 8 dB with 0 ppm), one noise realization
each; its other 9 advertising cases are rejections that the model also rejects
([`best-matrix-product`](../../results/validation/best-matrix-product/rx_regression/summary.tsv), column
`coverage`). A loss of 1 to 2 dB of sensitivity does not show in it.

This harness measures what such a lever costs: **the packets the RTL loses**, at points of SNR and
frequency offset, on thousands of packets, **packet by packet against a receiver model** on the very
samples the RTL is fed. This report records the harness and its first run, on `ble-rx-best` itself, which
gives the reference that the levers are measured against.

## 1. The harness

`scripts/validation/rx_per/`:

| File | Role |
|---|---|
| `gen_rx_per.py` | Stimuli of one point (SNR, ppm): N segments, each noise (64–127 samples and a random fraction of a sample), one Legacy Advertising packet, 400 samples of noise. The packets alternate between example 0 of the matrix (32 octets of payload) and the longest PDU (37 octets of payload, random each time), on channels 37, 38, 39 in turn. Transmitter, carrier and sampling offset of the ppm (`add_freq_sampling_error`) and AWGN (`add_noise`) are `btlelib.py`'s; the samples are cast with `np.int16`, as the matrix's vectors. Writes the samples, the segments, and per segment whether each receiver model gets the packet. |
| `tb_rx_per.v` | `btle_rx` with its defaults, `clkb` = `clk`, the advertising Access Address and CRC init, the channel of each segment. Reset before every segment (segments are independent, and the phase of a sample is its index in the segment modulo 8, as in the model); one sample every second clock, as `clock_domain_conversion_iq` gives it; after every `decode_end` with `crc_ok`, the header and payload read from the packet RAM, each word held 4 clocks. |
| `rx_per_report.py` | Per point: the packets the RTL loses (received = a `decode_end` of its segment with `crc_ok` and the octets of the PDU sent), with a Wilson 95 % interval; the same for every model; the disagreements with the reference model. |
| `run_rx_per.sh` | The points in parallel, the report, the mutation check; provenance (DUT revision, model and harness hashes, tool versions). |

**The receiver models** (`gen_rx_per.py`, `MODELS`), each built from the 8 phases decoded by `btlelib`'s
functions (`gfsk_demodulation_fixed_point`, `search_unique_bit_sequence`, `decode_phy_bits`):

| Model | Receives the packet when | The receiver it models |
|---|---|---|
| `best8` | any phase decodes it with the right CRC; checked against `btlelib.btle_rx` on every segment | `ble-rx-best`, `master`, upstream |
| `centre1` | the phase in the middle of those that find the Access Address within one symbol of the first (the later of two middles) decodes it | one stored phase, chosen at the Access Address |
| `first1` | the first phase to find the Access Address decodes it | one stored phase, the first that finds it |
| `phases4` | phase 0, 2, 4 or 6 decodes it with the right CRC | 4 phase hypotheses |
| `phases2` | phase 0 or 4 decodes it with the right CRC | 2 phase hypotheses |

With `QBITS` < 16 the models decode the samples shifted right by `QSHIFT` (arithmetic) and saturated to
`QBITS`: the model of a narrower demodulator. The testbench still feeds the 16-bit samples, as the RF
interface gives them; the narrowing is the RTL's own.

**Verdict.** `RX_PER PASS` when every point is complete, the RTL receives **exactly** the packets that the
reference model receives, and never accepts a PDU other than the one sent. Otherwise `MISMATCH` lines and
`RESULT: FAIL`.

**Mutation check** (reference `best8`): three copies of the DUT, each with one deliberate degradation, on
100 packets at 0 ppm and 10 dB; each must lose packets the model receives.

| Mutant | Change |
|---|---|
| `only_phase_0` | `btle_rx.v`: only phase 0 may end a packet with its CRC (one fixed sampling phase) |
| `demod_3_bits` | `gfsk_demodulation_shared.v`: the products of the samples `>>> 5` (3 bits at this scale) |
| `decision_bias` | `gfsk_demodulation_shared.v`: the decision threshold at 4 000 instead of 0, as a carrier offset of about 16 ppm would move it |

## 2. Run `rx-per`: `ble-rx-best`

[`results/validation/rx-per/rx_per_best8/`](../../results/validation/rx-per/rx_per_best8/result.txt):
24 points (0, 10, 20, 30 ppm × 8, 10, 12, 14, 16, 20 dB), 400 packets each, seed 1, level 0 dB (`btlelib`'s
scale, a peak of 127, the scale of the matrix).

| Check | Result |
|---|---|
| RTL against the model `best8`, packet by packet | **9 600/9 600 the same**: 2 604 lost by both, 0 disagreements |
| PDUs accepted that were not the one sent | **0** |
| Mutants | **3/3 detected**: `only_phase_0` 66 disagreements in 100 packets, `demod_3_bits` 17, `decision_bias` 85 |
| Segments that end with a decode still running (a phase that took noise or a damaged length for a long packet) | 272; none changes a verdict: the receiver ends a packet at the first phase with the right CRC |

Packets lost, %, from [`summary.tsv`](../../results/validation/rx-per/rx_per_best8/summary.tsv). The RTL
column is `ble-rx-best`; the others are the models on the same samples.

| ppm | SNR (dB) | RTL | RTL 95 % | `best8` | `centre1` | `first1` | `phases4` | `phases2` |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 8 | 73.5 | 69.0–77.6 | 73.5 | 84.2 | 93.8 | 85.8 | 91.2 |
| 0 | 10 | **3.0** | 1.7–5.2 | 3.0 | 26.0 | 78.5 | 17.8 | 47.8 |
| 0 | 12 | **0.0** | 0.0–1.0 | 0.0 | 2.5 | 65.8 | 0.5 | 11.0 |
| 0 | 14 | 0.0 | 0.0–1.0 | 0.0 | 0.0 | 50.8 | 0.0 | 0.2 |
| 0 | 16 | 0.0 | 0.0–1.0 | 0.0 | 0.0 | 44.0 | 0.0 | 0.0 |
| 0 | 20 | 0.0 | 0.0–1.0 | 0.0 | 0.0 | 24.8 | 0.0 | 0.0 |
| 10 | 8 | 82.5 | 78.5–85.9 | 82.5 | 89.8 | 94.0 | 92.2 | 96.0 |
| 10 | 10 | 14.0 | 10.9–17.7 | 14.0 | 46.2 | 80.0 | 41.2 | 64.2 |
| 10 | 12 | **0.2** | 0.0–1.4 | 0.2 | 10.0 | 67.0 | 4.8 | 27.0 |
| 10 | 14 | 0.0 | 0.0–1.0 | 0.0 | 0.5 | 55.2 | 0.0 | 4.0 |
| 10 | 16 | 0.0 | 0.0–1.0 | 0.0 | 0.0 | 47.0 | 0.0 | 0.0 |
| 10 | 20 | 0.0 | 0.0–1.0 | 0.0 | 0.0 | 28.2 | 0.0 | 0.0 |
| 20 | 8 | 98.2 | 96.4–99.1 | 98.2 | 98.5 | 99.2 | 99.0 | 99.5 |
| 20 | 10 | 69.2 | 64.6–73.6 | 69.2 | 80.0 | 91.5 | 81.5 | 91.8 |
| 20 | 12 | 11.8 | 9.0–15.3 | 11.8 | 41.2 | 75.2 | 36.8 | 64.8 |
| 20 | 14 | **0.0** | 0.0–1.0 | 0.0 | 7.0 | 67.8 | 3.2 | 31.2 |
| 20 | 16 | 0.0 | 0.0–1.0 | 0.0 | 0.5 | 46.0 | 0.0 | 7.0 |
| 20 | 20 | 0.0 | 0.0–1.0 | 0.0 | 0.0 | 28.0 | 0.0 | 0.0 |
| 30 | 8 | 100.0 | 99.0–100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| 30 | 10 | 99.0 | 97.5–99.6 | 99.0 | 99.0 | 99.8 | 99.2 | 99.5 |
| 30 | 12 | 75.0 | 70.5–79.0 | 75.0 | 83.5 | 90.2 | 86.2 | 92.5 |
| 30 | 14 | 22.8 | 18.9–27.1 | 22.8 | 50.5 | 68.8 | 47.2 | 74.5 |
| 30 | 16 | **1.8** | 0.9–3.6 | 1.8 | 11.0 | 58.8 | 9.0 | 45.8 |
| 30 | 20 | 0.0 | 0.0–1.0 | 0.0 | 0.0 | 30.5 | 0.0 | 9.2 |

**`ble-rx-best` already depends on the frequency offset.** In `btlelib`'s channel, a ppm is both a
carrier offset (2 450 MHz × ppm: 24.5 kHz at 10 ppm, 73.5 kHz at 30 ppm) and a sampling-rate offset. The
demodulator decides on the sign of `i[n−8]·q[n] − i[n]·q[n−8]`, with nothing to remove the carrier offset,
so the SNR it needs rises from about 10 dB at 0 ppm to about 16 dB at 30 ppm. At 50 ppm (122.5 kHz) the
model and the RTL lose example 0 even at 20 dB: the matrix records those cases as rejections. The Core
Specification lets a transmitter's centre frequency deviate by up to ±150 kHz (Vol 6, Part A; not checked
against its text here). The sampling-rate offset is not what costs: over
the longest packet (47 octets with preamble and Access Address, 376 µs), even 100 ppm moves the sampling
instant by 0.3 of a sample.

## 3. What the models say about the levers

These columns are models, not RTL; they are what a lever's RTL must reproduce (§ 4). The first SNR of the
grid (2 dB steps) at which each receiver loses at most 10 % of the packets:

| ppm | `best8` (`ble-rx-best`) | `centre1` | `phases4` | `phases2` | `first1` |
|---:|---:|---:|---:|---:|---:|
| 0 | 10 dB | 12 dB | 12 dB | 14 dB | never (24.8 % at 20 dB) |
| 10 | 12 dB | 12 dB | 12 dB | 14 dB | never (28.2 %) |
| 20 | 14 dB | 14 dB | 14 dB | 16 dB | never (28.0 %) |
| 30 | 16 dB | 20 dB | 16 dB | 20 dB | never (30.5 %) |

- **One stored phase works only if it is the centre.** The first phase to find the Access Address sits on
  the edge of the eye: it loses a quarter of the packets at 20 dB. The middle of the phases that find it
  is known less than one symbol after the first, before its own first bit after the Access Address, so the
  choice needs no buffer; it costs about 1–2 dB against `best8` (26.0 % against 3.0 % at 0 ppm and 10 dB,
  41.2 % against 11.8 % at 20 ppm and 12 dB).
- **4 hypotheses cost about 1 dB**, a little less than one stored phase; **2 hypotheses cost 2–5 dB**,
  more with the offset.
- **The width** is not in this run: its model needs the scale the RF front end gives (`QBITS`, `QSHIFT`,
  `LEVEL_DB`), which a run on the lever's branch fixes.

## 4. Using it for a lever

On the lever's branch, the harness compares its RTL with the lever's model on the same stimuli (the seed,
the point and the level fix them, and `point.txt` records their SHA-256):

```bash
scripts/validation/rx_per/run_rx_per.sh <label> 400 centre1     # one stored phase
scripts/validation/rx_per/run_rx_per.sh <label> 400 phases4     # 4 hypotheses: phases 0, 2, 4, 6
QBITS=8 QSHIFT=0 scripts/validation/rx_per/run_rx_per.sh <label> 400 best8   # an 8-bit demodulator
```

- The RTL must receive exactly the packets of its model. Where the design differs from the model
  (another rule for the middle phase, other phases kept, rounding instead of a shift), the model in
  `gen_rx_per.py` changes with it, in the same commit.
- Its cost is its column against `best8` in this run (the same stimuli), or, packet by packet,
  `packets.tsv` of the two runs.
- The mutants are those of `ble-rx-best` and run only with the reference `best8` at 16 bits; a lever's
  branch adds its own (for example, the middle phase off by one).
- A lever that keeps the 8 phases and the CRC but narrows the demodulator to at least the width of its
  input (12 bits for a 12-bit ADC, sign-extended) is still exact, and its evidence is a proof, as on the
  earlier branches.

## 5. What this does not claim

- **The channel is `btlelib`'s**: AWGN, and a ppm that is both a carrier offset and a sampling offset.
  No phase noise, I/Q imbalance, DC offset, AGC, multipath or interference. The SNR is `btlelib`'s (the
  peak power, 127², over the noise power at 8 MS/s), not E<sub>b</sub>/N<sub>0</sub> nor a sensitivity
  in dBm.
- **One scale** (a peak of 127): the RTL's 16 bits are exact at any scale; a narrower demodulator is not,
  and needs the scale of the front end (`LEVEL_DB`).
- **The receiver alone** (`btle_rx`, its defaults, `clkb` = `clk`, a reset before each packet): not the
  controller, the link layer's reads or the clock crossing, which the lockstep and the matrix cover.
- **Two packets** (example 0, and 37 random octets of payload), on the three advertising channels.
- **The models of the levers are models**: no lever's RTL exists yet, and its column is a prediction
  until a run on its branch agrees with it packet by packet.

## 6. Reproducing

From WSL, at the root of `ble-rx-best`:

```bash
scripts/validation/rx_per/run_rx_per.sh rx-per 400        # 24 points, the mutants; 4 min 45 s on 24 cores
```

The stimuli are not kept (1.34 million samples, about 13 MB, per point); the seed, the point and the
level regenerate them, and `points/*/point.txt` gives their SHA-256.
