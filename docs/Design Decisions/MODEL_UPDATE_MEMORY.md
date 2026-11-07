# Model update: model memory separate from the BLE receive buffers

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `ble-opt`  
**Date:** 2026-09-19  
**Author:** Miguel Simões  
**Status:** implemented in software (`firmware/model_update/`) and tested on the
host with a flash model and injected power cuts. Not yet run on a processor,
and not yet connected to a BLE link layer (which does not exist yet: see § 6).

---

## Purpose

The tag must receive a new model of about 48 KiB over BLE. This document fixes
where each byte lives, so that no 48 KiB buffer appears in the receiver, and it
describes the transfer that moves the model safely from the radio into
non-volatile memory.

## 1. Where the memory is

```
 BLE RX (hardware)          software (model_update)              NVM (system budget)
 ┌───────────────────┐      ┌───────────────────────────┐        ┌──────────────────────┐
 │ 8 x PDU buffers   │ ───► │ 1 block buffer (128 B)    │ ─────► │ slot A (48 KiB)      │
 │ (512 B each,      │      │ + state: 472 B in total   │        │ slot B (48 KiB)      │
 │  unchanged)       │      │                           │        │ 2 metadata pages     │
 └───────────────────┘      └───────────────────────────┘        │ progress log (4 KiB) │
                                                                 └──────────────────────┘
```

| Memory | Size | Belongs to | Notes |
|---|---:|---|---|
| RX PDU buffers | 8 × 512 × 8 bit | BLE receiver (hardware) | unchanged, as agreed (§ 2 of the area plan) |
| Receiver state (`mu_ctx_t`) | **472 bytes** of RAM | processor | one 128-byte block buffer, the block bitmap (64 B), manifest, metadata mirror |
| Model slots A and B | 2 × 48 KiB | NVM, system budget | the new model is written into the slot that is **not** active |
| Metadata | 2 pages (2 × 256 B in the tests) | NVM | used alternately; each record carries a sequence number and a CRC-32 |
| Progress log | 4 KiB in the tests | NVM | 4 bytes per completed block, append-only, so the transfer can resume |
| **NVM total for a 48 KiB model** | **≈ 100.5 KiB** | system | 96 KiB of slots + 4.5 KiB of metadata and log |

The receiver needs **no buffer of the model's size**: a model of any size up to
one slot flows through the same 128-byte block buffer.

## 2. Transfer protocol

A 48 KiB model is **384 blocks of 128 bytes**. Each BLE packet payload carries
one message (little-endian):

| Message | Fields | Size |
|---|---|---|
| `MANIFEST_FRAG` | type, offset, length, up to 16 bytes of the manifest | ≤ 19 B |
| `MANIFEST_END` | type, CRC-32 of the 44-byte manifest | 5 B |
| `BLOCK_FRAG` | type, block (16 bit), offset, length, up to 16 data bytes | ≤ 21 B |
| `BLOCK_END` | type, block, CRC-32 of the block | 7 B |

The manifest holds the version, the image size, the block size and the
**SHA-256** of the whole image. With 16 data bytes per packet (a 23-byte ATT MTU
minus headers), one block is 8 fragments plus its end: 9 packets, 3456 packets
for the whole model plus 4 for the manifest. A larger MTU (BLE 4.2 data length
extension) would carry a block in one or two packets. `MU_FRAG_DATA_MAX` is a
single constant.

The receiver:
1. assembles one block at a time in RAM;
2. checks its CRC-32 at `BLOCK_END`;
3. programs it into the target slot, reads it back, and appends a log entry;
4. after the last block, computes the SHA-256 of the whole slot;
5. only if the hash matches, activates the new model with **one metadata write**.

A block that fails its CRC, or arrives incomplete, is simply not recorded, and
the sender sends it again. The sender learns which blocks are missing from the
receiver status. In the final system that status travels over the connected
BLE link. Out-of-order blocks and duplicates are accepted.

## 3. Why a power cut cannot leave a bad model active

| Mechanism | Guarantee |
|---|---|
| The new model goes to the **inactive** slot | the running model is never touched during an update |
| Metadata written to the **other** page, with sequence number + CRC | a cut during the write leaves the previous record valid: the state is either the old one or the new one |
| Before erasing the target slot, a metadata record marks it invalid | a half-erased slot is never trusted |
| Progress log with an entry and its complement per block | a torn entry is skipped; at worst that block is received again |
| Activation = one metadata write, **after** the SHA-256 check | a model becomes active only complete and verified |
| At boot, the active slot's SHA-256 is checked again | if the content does not match, the other valid slot is used |
| All blocks received but the cut hit before activation | at boot the receiver finds the complete log, verifies, and activates |

## 4. Evidence

`firmware/model_update/run_tests.sh`. The results are in
[`results/validation/sticker/model_update/`](../../results/validation/sticker/model_update/result.txt).

The flash model erases by page (to 0xFF) and programs by AND (bits only go
from 1 to 0). A power cut interrupts the operation in progress (a torn write
or erase of a random prefix), and the device then reboots and resumes.

| Test | Result |
|---|---|
| T1 clean 48 KiB install | pass |
| T2 48 KiB update with 20 % packet loss, 5 % duplicates, 5 % bit flips, blocks in random order | pass; about 10× the loss-free packet count, because a block is re-sent whole |
| T3 60 updates of 48 KiB with up to 5 random power cuts each | 60/60 completed, **100 power cuts** |
| T4 exhaustive sweep: a power cut at **every** NVM operation of an update (230 operations) | 233/233 completed |
| T5 image whose content does not match the manifest hash | rejected; the previous model stays active, also after reboot |
| T6 transfer abandoned half-way, then a different model | the new model completes; the partial one never becomes active |
| T7 plain reboot in the middle of a transfer | the 200 completed blocks are kept; the transfer resumes |
| Invariant after **every** one of the 333 boots | once a model is installed there is always one active; it is the previous or the new version; its content matches that image byte for byte |

**Non-vacuity:** four mutants of `model_update.c`, each a plausible mistake,
must each make the suite fail. All four are caught:
- activating without the hash check (caught by T5);
- writing the metadata over the current page (a cut leaves no valid record; caught by the invariant);
- not logging progress (caught by T7);
- writing the new model over the active slot (caught by the invariant).

## 5. Assumptions and limits

- **Flash behaviour.** A torn program is modelled as a prefix of the bytes
  being programmed correctly. Real flash can leave a byte half-programmed.
  Re-programming the same data is still safe here (it is an AND), but a
  production version should verify each block and, on a mismatch, erase and
  rewrite its page.
- **No authentication.** The SHA-256 protects integrity, not origin. Accepting
  a model only from an authorised sender needs a signature over the manifest
  (for example Ed25519), which is not implemented.
- **Wear.** The log is erased once per transfer and the metadata page once per
  record. Wear-levelling is not handled.
- **Retransmission granularity is the block.** With 20 % packet loss this costs
  about 10× the packets. On a connected BLE link, the link layer's own
  acknowledgements make packet loss rare at this level.

## 6. What this does not include

The upstream Link Layer is a placeholder, so there is no connected BLE link yet
to carry these messages, acknowledge them, or return the status. That link
layer — connection control, acknowledgements, retransmission — is still to be
written (area plan § 2). This code is the part that sits above it and decides
what reaches the model memory. The final validation must repeat T1–T7 over the
real link, on the processor, with the full 48 KiB transfer.
