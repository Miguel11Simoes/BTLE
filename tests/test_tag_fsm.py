"""tag_fsm of ble-tx-poc-tmp100, from the sensor's model to upstream's Python receiver.

Author: Miguel Simões

tests/tag_fsm_tb.v runs tag_fsm with the model of the TMP100 (tests/tmp100_model.v) and a monitor of the I2C bus against
the datasheet's limits (tests/i2c_timing_monitor.v). Each scenario below is one simulation; for every packet it sends,
against what the scenario implies:
- the sensor's two bytes: what the sensor's model really answered (its log), and, where the scenario knows them, from the
  temperature itself and back to it, T = int16 / 256, as the gateway converts;
- the PHY bits: those of python/btlelib.py's btle_tx for the PDU of scripts/senseworks/tag_bch.py;
- upstream's Python receiver (btle_rx) decodes the I/Q, the CRC right, that PDU;
- the BCH code: the PDU is a codeword, and t errors at random are corrected back to it;
- T_advEvent, start to start: exactly the period less advDelay, in ticks and in time, advDelay from a model of the LFSR
  XOR AdvA's first byte;
- the TMP100: in shutdown at every packet; no read during a conversion; OS written outside shutdown only once, the first
  event's, which puts it in shutdown.
The packets of the scenarios on the default code go to --output (JSON) for scripts/senseworks/check_tag_scapy.py.

Then: the coverage of the frames (every (window, slot), over all the scenarios), and with --mutants the deliberate faults,
each of which must fail a scenario with a concrete mismatch.

  python3 tests/test_tag_fsm.py [--only NAME[,NAME]] [--jobs N] [--mutants] [--output FILE] [--resume FILE]

With --resume, each result is appended to FILE, and a later run with the same RTL, models and test takes it from there: a
campaign survives the loss of its machine (WSL restarted while this was written). The log prints every result either way.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile
import threading

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from btlelib import btle_tx, btle_rx, hex_string_to_bit, bit_to_hex_string, crc24_core  # noqa: E402
sys.path.insert(0, str(ROOT / "scripts/senseworks"))
import tag_bch  # noqa: E402

RTL = ["tag_fsm.v", "btle_tx.v", "crc24.v", "crc24_core.v", "scramble.v", "scramble_core.v", "gfsk_modulation.v",
       "bit_repeat_upsample.v", "gauss_filter.v", "vco.v"]
MODELS = ["tag_fsm_tb.v", "i2c_slave_model.v", "tmp100_model.v", "i2c_timing_monitor.v", "efuse_async_mem_1x8_model.v"]
ROM_ADV = 0xC10203040506                 # tag_fsm's ADV_ADDRESS
CID = 0xFFFF
WINDOW_CONFIG, WINDOW_POINTER, WINDOW_READ = 8, 30, 31
REAL_TICK_NS = 1.0e9 / 32768


class Mismatch(Exception):
    """The design did not do what the scenario implies: a concrete failure."""


@dataclass(frozen=True)
class Build:
    tick_div: int = 25
    rate_en: int = 0
    bch: int = 8
    otp: int = 0
    adv: int = ROM_ADV
    channel: int = 37
    clk_half_ns: float = 31.25

    def tick_ns(self) -> float:
        return self.tick_div * 2 * self.clk_half_ns

    def time_scale(self) -> float:
        """How much faster than the real tick the scenario runs; the model's times divide by it."""
        return REAL_TICK_NS / self.tick_ns()


@dataclass
class Scenario:
    name: str
    build: Build = Build()
    temps: list[float] = field(default_factory=lambda: [25.0])
    adv: int | None = None               # the AdvA expected: the build's unless programmed
    rate: int = 4                        # with rate_en
    events: int = 3
    max_ms: int = 3000
    plus: dict = field(default_factory=dict)
    expected: list[int] | None = None    # each packet's two bytes, when known a priori
    period: bool = True                  # T_advEvent checked
    rows: bool = True
    sensor_checks: bool = True           # the TMP100's log
    from_reads: bool = True              # each packet what the log says was read
    os_ignored_max: int = 1
    scl_period_ns: float | None = None
    frames: tuple[int, int] | None = None  # the STARTs and STOPs the bus must see
    gap_ticks: tuple[int, int] | None = None  # between these packets, at least so many ticks more: the tag was off


def raw9(t: float) -> int:
    """What the TMP100 answers at 9 bits for a temperature: its register, the low 7 bits 0."""
    return ((int(round(t * 16)) << 4) & 0xFFFF) & 0xFF80


def celsius(raw: int) -> float:
    return (raw - 0x10000 if raw & 0x8000 else raw) / 256


def build_sim(build: Build, work: Path, tag: str, texts: dict[str, str] | None) -> Path:
    """Compile once per build (and per mutation); the simulation binary is shared by the scenarios."""
    key = hashlib.sha256(repr((build, tag)).encode()).hexdigest()[:16]
    out = work / f"sim_{key}"
    if out.exists():
        return out
    d = work / f"src_{key}"
    d.mkdir()
    files = []
    for f in RTL:
        path = d / f
        path.write_text(texts[f] if texts and f in texts else (ROOT / "verilog" / f).read_text())
        files.append(str(path))
    files += [str(ROOT / "tests" / f) for f in MODELS]
    defs = [f"-DTICK_DIV={build.tick_div}", f"-DRATE_EN={build.rate_en}", f"-DBCH={build.bch}", f"-DOTP={build.otp}",
            f"-DCHANNEL={build.channel}", f"-DCLK_HALF_NS={build.clk_half_ns}", f"-DROM_ADV=48'h{build.adv:012x}",
            f"-DCID=16'h{CID:04x}"]
    result = subprocess.run([os.environ.get("IVERILOG", "iverilog"), "-g2012", "-s", "tag_fsm_tb", "-o", str(out),
                             *defs, *files], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"does not compile:\n{result.stdout}{result.stderr}")
    return out


def simulate(s: Scenario, sim: Path, work: Path) -> Path:
    run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=work))
    (run_dir / "temps.hex").write_text("".join(f"{round(t * 16) & 0xFFFF:04x}\n" for t in s.temps))
    plus = {"events": s.events, "max_ms": s.max_ms, "time_scale": s.build.time_scale(), "rate": s.rate, **s.plus}
    args = [f"+{k}={v}" for k, v in plus.items()]
    result = subprocess.run([os.environ.get("VVP", "vvp"), "-n", str(sim), *args], cwd=run_dir, capture_output=True,
                            text=True, timeout=3000)
    log = result.stdout + result.stderr
    lines = [l for l in log.splitlines() if l.startswith(("PASS", "MISMATCH", "ERROR"))]
    if result.returncode != 0 or not any(l.startswith("PASS") for l in lines):
        mismatch = [l for l in lines if l.startswith("MISMATCH")]
        if mismatch:
            raise Mismatch(mismatch[0])
        raise RuntimeError(f"exit {result.returncode}: {log[-800:]}")
    (run_dir / "verdict.txt").write_text(lines[-1] + "\n")
    return run_dir


def lfsr_sequence(n: int) -> list[int]:
    values, l = [], 0
    for _ in range(n):
        values.append(l)
        l = ((l << 1) & 0xFF) | (((l >> 7) ^ (l >> 5) ^ (l >> 4) ^ (l >> 3) ^ int((l & 0x7F) == 0)) & 1)
    return values


def period_ticks(s: Scenario) -> int:
    return 1 << (11 + s.rate) if s.build.rate_en else 1 << 15


def check(s: Scenario, run: Path, rng: random.Random) -> tuple[list[dict], str]:
    b = s.build
    t = b.bch
    adv_expected = s.adv if s.adv is not None else b.adv
    events, aborted, reset_index = [], set(), None
    for line in (run / "events.txt").read_text().splitlines():
        f = line.split()
        if f[0] == "tx":
            events.append(dict(packet=int(f[1]), ns=float(f[2]), ticks=int(f[3]), sensor=int(f[4], 16), adv=int(f[5], 16),
                               shutdown=int(f[6]), channel=int(f[7])))
        elif f[0] == "reset":
            reset_index = int(f[1])
            if int(f[4]):
                aborted.add(int(f[1]))
    done = [e for e in events if e["packet"] not in aborted]
    if len(done) < s.events - len(aborted):
        raise Mismatch(f"{len(done)} packets completed, {s.events} expected")
    # what the sensor answered
    log = (run / "tmp100.log").read_text().splitlines()
    reads = [(float(l.split()[1]), int(l.split()[2], 16), int(l.split()[3])) for l in log if l.startswith("read")]
    tables = {n: np.loadtxt(run / f"{n}.txt", dtype=int, ndmin=2) for n in ("iq", "bits")}
    crc_init = hex_string_to_bit("555555")
    rows = []
    previous = -1.0
    for k, e in enumerate(events):
        window = [r for r in reads if previous < r[0] < e["ns"]]
        previous = e["ns"]
        settled = reset_index is None or e["packet"] < reset_index or e["packet"] > reset_index + 1  # the first after it may be wrong
        if s.expected is not None and settled:
            if e["sensor"] != s.expected[k]:
                raise Mismatch(f"packet {e['packet']}: sensor {e['sensor']:04x}, expected {s.expected[k]:04x}")
        elif s.from_reads and settled:
            want = window[-1][1] if window else 0xFFFF
            if e["sensor"] != want:
                raise Mismatch(f"packet {e['packet']}: sensor {e['sensor']:04x}, the sensor answered {want:04x}")
            if e["sensor"] != 0xFFFF and e["sensor"] & 0x7F:
                raise Mismatch(f"packet {e['packet']}: sensor {e['sensor']:04x}, the low 7 bits of a 9-bit reading are 0")
        if s.sensor_checks and window and settled and not e["shutdown"]:
            raise Mismatch(f"packet {e['packet']}: the TMP100 is not in shutdown")
        if e["adv"] != adv_expected or e["channel"] != b.channel:
            raise Mismatch(f"packet {e['packet']}: AdvA {e['adv']:012x} channel {e['channel']}; expected {adv_expected:012x} {b.channel}")
        if e["packet"] in aborted:
            continue
        sensor = e["sensor"].to_bytes(2, "big")
        pdu = tag_bch.tag_pdu(adv_expected, sensor, t, CID, 1)
        pdu_bits = hex_string_to_bit(pdu.hex())
        i, q, bits, _ = btle_tx(pdu_bits, b.channel, crc_init, "D6BE898E")
        got_bits = tables["bits"][tables["bits"][:, 0] == e["packet"]][:, 1]
        if not np.array_equal(got_bits, bits):
            raise Mismatch(f"packet {e['packet']}: the PHY bits are not those of the PDU {pdu.hex()}")
        got_iq = tables["iq"][tables["iq"][:, 0] == e["packet"]][:, 1:]
        if got_iq.shape[0] != len(i):
            raise Mismatch(f"packet {e['packet']}: {got_iq.shape[0]} samples, {len(i)} expected")
        decoded = btle_rx(got_iq[:, 0], got_iq[:, 1], b.channel, crc_init, "D6BE898E")
        if not decoded[1] or bit_to_hex_string(decoded[0]) != pdu.hex():
            raise Mismatch(f"packet {e['packet']}: upstream's receiver does not decode the PDU sent")
        received = bytes.fromhex(bit_to_hex_string(decoded[0]))
        word = tag_bch.codeword_bits(received, t)
        if tag_bch.decode_bits(word, t) != word:
            raise Mismatch(f"packet {e['packet']}: the PDU is not a codeword")
        bad = list(word)
        for j in rng.sample(range(len(word)), t):
            bad[j] ^= 1
        if tag_bch.decode_bits(bad, t) != word:
            raise Mismatch(f"packet {e['packet']}: {t} errors not corrected")
        if s.rows and t == 8:
            rows.append(dict(scenario=s.name, t=t, sensor_bytes=2, tx_add=1, channel=b.channel, sensor=sensor.hex(),
                             access_address="8e89bed6", pdu=pdu.hex(),
                             crc_bits="".join(str(int(v)) for v in crc24_core(pdu_bits, crc_init))))
    # T_advEvent, exact in ticks and in time
    if s.period:
        delays = lfsr_sequence(len(events) + 1)
        for k in range(1, len(events)):
            ticks = events[k]["ticks"] - events[k - 1]["ticks"]
            want = period_ticks(s) - (delays[k - 1] ^ (adv_expected & 0xFF))
            if s.gap_ticks and k == s.gap_ticks[0]:
                if ticks < s.gap_ticks[1]:
                    raise Mismatch(f"{ticks} ticks across the time off, at least {s.gap_ticks[1]} expected")
                continue
            if ticks != want:
                raise Mismatch(f"T_advEvent between packets {k - 1} and {k}: {ticks} ticks, expected {want}")
            ns = events[k]["ns"] - events[k - 1]["ns"]
            if abs(ns - want * b.tick_ns()) > 1:
                raise Mismatch(f"T_advEvent between packets {k - 1} and {k}: {ns} ns, {want * b.tick_ns()} expected")
    # the model's log
    if s.sensor_checks:
        written = [l for l in log if l.startswith("write_readonly")]
        if written and reset_index is None:
            raise Mismatch(f"a byte written with the pointer on the temperature: {written[0]}")
        ignored = [l for l in log if l.startswith("os_ignored")]
        if len(ignored) > s.os_ignored_max:
            raise Mismatch(f"{len(ignored)} one-shots written outside shutdown: {ignored[-1]}")
        stale = [r for r in reads if r[2] and r[0] > (events[0]["ns"] if events else 0)]
        if stale:
            raise Mismatch(f"the temperature read during a conversion at {stale[0][0]} ns")
    verdict = (run / "verdict.txt").read_text().strip()
    if s.sensor_checks and s.temps and "config 81" not in verdict and reads:
        raise Mismatch(f"the configuration at the end is not 0x81: {verdict}")
    if s.scl_period_ns is not None:
        low, high = map(float, re.search(r"SCL period, between ([\d.]+) and ([\d.]+) ns", verdict).groups())
        if abs(low - s.scl_period_ns) > 1 or abs(high - s.scl_period_ns) > 1:
            raise Mismatch(f"SCL period between {low} and {high} ns, expected {s.scl_period_ns}")
    if s.frames is not None:
        got = tuple(map(int, re.search(r"(\d+) STARTs, (\d+) STOPs", verdict).groups()))
        if got != s.frames:
            raise Mismatch(f"{got[0]} STARTs and {got[1]} STOPs on the bus, expected {s.frames[0]} and {s.frames[1]}")
    return rows, verdict


# ------------------------------------------------------------------------------------------------- the scenarios
def after_first(temps: list[float]) -> list[int]:
    """The first packet carries the last continuous conversion, of the first temperature; then one conversion per event."""
    return [raw9(temps[0])] + [raw9(t) for t in temps]


def scenarios() -> list[Scenario]:
    out: list[Scenario] = []
    # the temperature's range, the sign, the truncation to 9 bits; the bus's timing and its frames
    sweep = [25.0, -40.0, -40.5, -55.0, 0.0, 87.0, 87.5, 125.0, -0.5, 0.25, 20.75, 30.0]
    out.append(Scenario("nominal", temps=sweep, events=len(sweep) + 1, expected=after_first(sweep), scl_period_ns=6250.0,
                        frames=(3 * (len(sweep) + 1), 3 * (len(sweep) + 1))))
    # a second in real time: 16 MHz, 488 clocks per tick
    out.append(Scenario("real_time", Build(tick_div=488), temps=[21.5, 22.0], events=3, max_ms=5000,
                        expected=after_first([21.5, 22.0]), scl_period_ns=4 * 488 * 62.5))
    # the typical conversion time: the same bytes (the wait is for the maximum)
    out.append(Scenario("conversion_typical", temps=[10.0, 11.0], events=3, plus={"conv_mode": 1}, expected=after_first([10.0, 11.0])))
    # no sensor at all, and a sensor that stops answering and comes back: 0xFFFF, the packets go on
    out.append(Scenario("sensor_absent", temps=[20.0], events=3, plus={"tmp100": 0}, expected=[0xFFFF] * 3))
    out.append(Scenario("sensor_nack", temps=[20.0, 21.0, 22.0, 23.0], events=6, plus={"nack_from": 2, "nack_to": 4}, os_ignored_max=1))
    out.append(Scenario("sensor_nack_at_boot", temps=[20.0, 21.0], events=5, plus={"nack_from": 0, "nack_to": 2}, os_ignored_max=1))
    # the channel, the codes: parameters
    for channel in (38, 39):
        out.append(Scenario(f"channel_{channel}", Build(channel=channel), temps=[15.0, 16.0], events=2))
    for bch in (12, 18):
        out.append(Scenario(f"bch_{bch}", Build(bch=bch), temps=[25.0, 26.0], events=2, rows=False))
    # AdvA in the eFuse blocks; AdvA's first byte is advDelay's XOR: the two ends
    otp_adv = 0xD1E2A3B4C5F6
    out.append(Scenario("adv_efuse", Build(otp=1), temps=[12.0, 13.0], events=3, adv=otp_adv, plus={"otp_prog": f"{otp_adv:012x}"}))
    out.append(Scenario("adv_first_byte_00", Build(adv=0xC10203040500), temps=[12.0], events=3))
    out.append(Scenario("adv_first_byte_ff", Build(adv=0xC102030405FF), temps=[12.0], events=3))
    # every rate; the conversion fits in the shortest; start to start exact in each
    for rate in range(1, 8):
        out.append(Scenario(f"rate_{rate}", Build(rate_en=1), rate=rate, temps=[-5.0, 1.0, 2.0], events=3, max_ms=4000,
                            expected=after_first([-5.0, 1.0])))
    # off: nothing on the bus or on the air; back on, the same
    out.append(Scenario("rate_off_and_on", Build(rate_en=1), rate=4, temps=[1.0, 2.0, 3.0], events=4, max_ms=4000,
                        plus={"off_after": 2, "off_ticks": 100000, "on_rate": 4}, gap_ticks=(2, 100000)))
    # the test mode: a counter, no bus; all the delays and the wrap of the LFSR
    out.append(Scenario("test_mode", Build(rate_en=1), rate=1, temps=[20.0], events=8, plus={"test_mode": 1, "i2c_monitor": 0},
                        expected=list(range(1, 9)), frames=None, sensor_checks=False, from_reads=False))
    out.append(Scenario("test_mode_wraps_all_delays", Build(rate_en=1), rate=1, temps=[20.0], events=260,
                        plus={"test_mode": 1, "i2c_monitor": 0}, expected=list(range(1, 261)), rows=False, sensor_checks=False,
                        from_reads=False, max_ms=6000))
    # a reset anywhere in a frame, and in the packet: at most one packet wrong, then right, the sensor as configured
    places = [(WINDOW_CONFIG, s) for s in (0, 1, 5, 9, 10, 14, 18, 19, 23, 27, 28)] + \
             [(WINDOW_POINTER, s) for s in (0, 3, 9, 12, 18, 19)] + \
             [(WINDOW_READ, s) for s in (0, 4, 9, 10, 13, 17, 18, 19, 22, 26, 27, 28)]
    temps = [8.0, 6.0, 7.0, 5.0, 4.0, 3.0, 2.0]
    for window, slot in places:
        for phase in (0, 2):
            out.append(Scenario(f"reset_w{window}_s{slot}_p{phase}", temps=temps, events=5, rows=False, period=False,
                                os_ignored_max=2,
                                plus={"reset_packet": 1, "reset_t": window * 128 + slot * 4 + phase, "i2c_monitor": 0}))
    out.append(Scenario("reset_in_packet", temps=temps, events=5, rows=False, period=False,
                        plus={"reset_packet": 1, "reset_t": -1, "i2c_monitor": 0}))
    # a line stuck low: nothing hangs, the packets go on; SCL: no frame seen, 0xFFFF; SDA: 0x0000, the limit of no ACK check
    out.append(Scenario("scl_stuck", temps=[40.0, 41.0, 42.0], events=6, os_ignored_max=1,
                        plus={"stuck_scl_from": 1, "stuck_scl_to": 3, "i2c_monitor": 0}))
    out.append(Scenario("sda_stuck", temps=[40.0, 41.0, 42.0], events=6, period=True, from_reads=False, os_ignored_max=1,
                        expected=[raw9(40.0), 0x0000, 0x0000, raw9(40.0), raw9(41.0), raw9(42.0)],
                        plus={"stuck_sda_from": 1, "stuck_sda_to": 3, "i2c_monitor": 0}))
    # the ASIC's clock: 32.768 kHz, a tick per clock
    # (with no switch to 16 MHz here, the packet takes 3840 of those clocks, within the second)
    out.append(Scenario("asic_clock", Build(tick_div=1, clk_half_ns=15258.789), temps=[25.0, -20.0, 60.0], events=4, max_ms=8000,
                        expected=after_first([25.0, -20.0, 60.0]), plus={"t_out_ns": 900}, scl_period_ns=122070.3))
    return out


# ------------------------------------------------------------------------------------------------- the coverage
def required_coverage() -> set[tuple[str, int, int]]:
    return {("slot", w, s) for w in (WINDOW_CONFIG, WINDOW_POINTER, WINDOW_READ) for s in range(32)}


# ------------------------------------------------------------------------------------------------- the mutants
# (file, what the fault is, edits, scenarios: one of them must fail with a concrete mismatch)
MUTANTS = [
    ("tag_fsm.v", "no shutdown: SD = 0", [("sent_first_at_lsb(8'h81)", "sent_first_at_lsb(8'h80)")], ["nominal"]),
    ("tag_fsm.v", "no one-shot: OS = 0", [("sent_first_at_lsb(8'h81)", "sent_first_at_lsb(8'h01)")], ["nominal"]),
    ("tag_fsm.v", "10 bits: the wait too short", [("sent_first_at_lsb(8'h81)", "sent_first_at_lsb(8'hA1)")], ["nominal"]),
    ("tag_fsm.v", "the configuration's pointer wrong", [("1'b1, sent_first_at_lsb(8'h01), 1'b1, sent_first_at_lsb(8'h90)", "1'b1, sent_first_at_lsb(8'h03), 1'b1, sent_first_at_lsb(8'h90)")], ["nominal"]),
    ("tag_fsm.v", "the temperature's pointer not written", [("sent_first_at_lsb(8'h00), 1'b1", "sent_first_at_lsb(8'h01), 1'b1")], ["nominal"]),
    ("tag_fsm.v", "the address of the writes wrong", [("{2'b11, sent_first_at_lsb(8'h81), 1'b1, sent_first_at_lsb(8'h01), 1'b1, sent_first_at_lsb(8'h90), 1'b1}", "{2'b11, sent_first_at_lsb(8'h81), 1'b1, sent_first_at_lsb(8'h01), 1'b1, sent_first_at_lsb(8'h92), 1'b1}")], ["nominal"]),
    ("tag_fsm.v", "the address of the read wrong", [("sent_first_at_lsb(8'h91)", "sent_first_at_lsb(8'h93)")], ["nominal"]),
    ("tag_fsm.v", "the first byte read not acknowledged", [("8'hFF, 1'b0, 8'hFF", "8'hFF, 1'b1, 8'hFF")], ["nominal"]),
    ("tag_fsm.v", "the last byte read acknowledged", [("FRAME_READ    = {2'b11,", "FRAME_READ    = {2'b10,")], ["nominal"]),
    ("tag_fsm.v", "the bits sent least significant first", [("sent_first_at_lsb = {b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7]};", "sent_first_at_lsb = b;")], ["nominal"]),
    ("tag_fsm.v", "the wait too short", [("WINDOW_POINTER = 5'd30, WINDOW_READ = 5'd31", "WINDOW_POINTER = 5'd11, WINDOW_READ = 5'd12")], ["nominal"]),
    ("tag_fsm.v", "the read before the pointer", [("WINDOW_READ = 5'd31", "WINDOW_READ = 5'd29")], ["nominal"]),
    ("tag_fsm.v", "the pointer's frame too long", [("in_pointer ? 5'd19 : 5'd28", "5'd28")], ["sensor_absent", "nominal"]),
    ("tag_fsm.v", "sampled with SCL low", [("in_read && (phase == 2'd2)", "in_read && (phase == 2'd0)")], ["nominal"]),
    ("tag_fsm.v", "a bit less sampled", [("(slot >= 5'd19) && (slot <= 5'd26)", "(slot >= 5'd20) && (slot <= 5'd26)")], ["nominal"]),
    ("tag_fsm.v", "the bytes swapped on the air", [(".sensor({sensor_r[7:0], sensor_r[15:8]})", ".sensor(sensor_r)")], ["nominal"]),
    ("tag_fsm.v", "SDA changes with SCL high", [("(is_bit && (phase[1] == phase[0]))", "(is_bit && (phase[1] != phase[0]))")], ["nominal"]),
    ("tag_fsm.v", "no START: SDA does not fall", [("(is_start && (phase != 2'd0))", "1'b0")], ["nominal"]),
    ("tag_fsm.v", "no STOP: SDA not low first", [("(is_stop && !phase[1])", "1'b0")], ["nominal"]),
    ("tag_fsm.v", "SCL does not fall after START", [("(is_start && (phase == 2'd3))", "1'b0")], ["nominal"]),
    ("tag_fsm.v", "no advDelay", [("t <= {t_high, lfsr ^ adv_address_sent[7:0]};", "t <= {t_high, 8'd0};")], ["nominal"]),
    ("tag_fsm.v", "advDelay not XOR AdvA", [("lfsr ^ adv_address_sent[7:0]", "lfsr")], ["nominal"]),
    ("tag_fsm.v", "the LFSR not stepped", [("if (wrap) lfsr <= ", "if (1'b0) lfsr <= ")], ["nominal"]),
    ("tag_fsm.v", "the LFSR stepped every tick", [("if (wrap) lfsr <= ", "lfsr <= ")], ["nominal"]),
    ("tag_fsm.v", "the LFSR can stick at 0", [("^ (lfsr[6:0] == 7'd0)};", "};")], ["nominal"]),
    ("tag_fsm.v", "the LFSR's feedback short of 256 states", [("lfsr[7] ^ lfsr[5] ^ lfsr[4] ^ lfsr[3] ^", "lfsr[7] ^ lfsr[5] ^ lfsr[4] ^")], ["test_mode_wraps_all_delays"]),
    ("tag_fsm.v", "the tick a clock short", [("localparam integer DIV_LAST_INT = TICK_DIV - 1;", "localparam integer DIV_LAST_INT = TICK_DIV - 2;")], ["nominal"]),
    ("tag_fsm.v", "off ignored", [("wire off = (RATE_EN != 0) && (rate == 3'd0);", "wire off = 1'b0;")], ["rate_off_and_on", "test_mode"]),
    ("tag_fsm.v", "off still sends", [("assign tx_start = wrap && tick && !off;", "assign tx_start = tick && (wrap || (off && (t[7:0] == 8'd0)));")], ["rate_off_and_on"]),
    ("tag_fsm.v", "the test mode's bus not silent", [("&t[(T_BITS-1):12] && !test_mode && !off;", "&t[(T_BITS-1):12] && !off;")], ["test_mode"]),
    ("tag_fsm.v", "the test mode's counter stuck", [("else if (test_mode && wrap) sensor_r <= sensor_r + 1'b1;", "")], ["test_mode"]),
    ("tag_fsm.v", "the test mode's counter not cleared", [("if (test_mode && off) begin", "if (1'b0) begin")], ["test_mode"]),
    ("tag_fsm.v", "the channel ignored", [(".channel_number(CHANNEL),", ".channel_number(6'd37),")], ["channel_38"]),
    ("tag_fsm.v", "tx_start held", [("assign tx_start = wrap && tick && !off;", "assign tx_start = wrap && !off;")], ["real_time"]),
] + [
    ("tag_fsm.v", f"rate {rate} wrong", [(f"(rate == 3'd{rate}) ? 6'b{bits}", f"(rate == 3'd{rate}) ? 6'b{other}")], [f"rate_{rate}"])
    for rate, bits, other in ((2, "111110", "111100"), (3, "111100", "111000"), (4, "111000", "110000"), (5, "110000", "100000"),
                              (6, "100000", "000000"), (7, "000000", "100000"))
] + [
    ("tag_fsm.v", "rate 1 wrong", [("6'b111111;    // 125 ms", "6'b111110;    // 125 ms")], ["rate_1"]),
]


class Resume:
    """The results so far, valid only for the same RTL, models and test."""

    def __init__(self, path: Path | None):
        self.path, self.done, self.lock = path, {}, threading.Lock()
        files = [ROOT / "verilog" / f for f in RTL] + [ROOT / "tests" / f for f in MODELS] + [Path(__file__)]
        self.key = hashlib.sha256(b"".join(f.read_bytes() for f in files)).hexdigest()
        if path and path.exists():
            for line in path.read_text().splitlines():
                try:
                    r = json.loads(line)
                except ValueError:      # the last line of a run that was cut
                    continue
                if r["key"] == self.key:
                    self.done[r["name"]] = r["value"]

    def get(self, name: str):
        return self.done.get(name)

    def put(self, name: str, value) -> None:
        if self.path:
            with self.lock, self.path.open("a") as f:
                f.write(json.dumps(dict(key=self.key, name=name, value=value)) + "\n")


def run_scenario(s: Scenario, work: Path, tag: str = "dut", texts: dict[str, str] | None = None):
    rng = random.Random(int(hashlib.sha256(s.name.encode()).hexdigest()[:8], 16))
    sim = build_sim(s.build, work, tag, texts)
    run = simulate(s, sim, work)
    rows, verdict = check(s, run, rng)
    cover = set()
    for line in (run / "cover.txt").read_text().splitlines():
        kind, a, b = line.split()
        cover.add((kind, int(a), int(b)))
    return rows, verdict, cover


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--only", help="comma-separated scenario names (or prefixes)")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    parser.add_argument("--mutants", action="store_true")
    parser.add_argument("--output", type=Path, help="the packets, for check_tag_scapy.py")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--mutant", help="only the mutants whose description holds this text")
    parser.add_argument("--resume", type=Path, help="keep the results here, and take those of an earlier run")
    a = parser.parse_args()
    all_scenarios = scenarios()
    if a.list:
        print("\n".join(s.name for s in all_scenarios))
        return
    chosen = all_scenarios
    if a.only:
        wanted = a.only.split(",")
        chosen = [s for s in all_scenarios if any(s.name == w or s.name.startswith(w) for w in wanted)]
    resume = Resume(a.resume)
    with tempfile.TemporaryDirectory(prefix="tag-fsm-") as temp:
        work = Path(temp)

        def one(s):
            kept = resume.get(s.name)
            if kept:
                return s, (kept["rows"], kept["verdict"], {tuple(c) for c in kept["cover"]}), None
            try:
                r, verdict, cover = run_scenario(s, work)
                resume.put(s.name, dict(rows=r, verdict=verdict, cover=sorted(cover)))
                return s, (r, verdict, cover), None
            except Mismatch as e:
                return s, None, f"MISMATCH {e}"
            except Exception as e:     # noqa: BLE001  a crash is reported, and fails the run
                return s, None, f"ERROR {e}"

        rows, coverage, failures = [], set(), 0
        for s in {sc.build for sc in chosen if not resume.get(sc.name)}:
            build_sim(s, work, "dut", None)     # compiled once, before the pool
        with ThreadPoolExecutor(max_workers=a.jobs) as pool:
            for s, result, error in pool.map(one, chosen):
                if error:
                    failures += 1
                    print(f"{s.name}: FAIL: {error}", flush=True)
                else:
                    r, verdict, cover = result
                    rows += r
                    coverage |= cover
                    print(f"{s.name}: {verdict}", flush=True)
        if failures:
            raise SystemExit(f"FAIL: {failures} of {len(chosen)} scenarios")
        print(f"scenarios: {len(chosen)}, pass {len(chosen)}")
        if not a.only:
            missing = sorted(required_coverage() - coverage)
            print(f"coverage: {len(required_coverage())} (window, slot) required, {len(required_coverage()) - len(missing)} reached")
            if missing:
                raise SystemExit(f"FAIL: not reached: {missing}")
        if a.output:
            a.output.parent.mkdir(parents=True, exist_ok=True)
            a.output.write_text(json.dumps(rows, indent=1) + "\n")
        if a.mutants:
            texts = {f: (ROOT / "verilog" / f).read_text() for f in RTL}
            by_name = {s.name: s for s in all_scenarios}
            caught = 0

            def mutant(index):
                kept = resume.get(f"mutant {index}")
                if kept:
                    return index, kept[0], kept[1]
                result = mutant_run(index)
                if result[1] == "CAUGHT":
                    resume.put(f"mutant {index}", result[1:])
                return result

            def mutant_run(index):
                f, label, edits, names = MUTANTS[index]
                mutated = dict(texts)
                for old, new in edits:
                    if mutated[f].count(old) != 1:
                        return index, "ERROR", f"text not found once in {f}: {old!r}"
                    mutated[f] = mutated[f].replace(old, new)
                for name in names:
                    try:
                        run_scenario(by_name[name], work, f"m{index}", mutated)
                    except Mismatch as e:
                        return index, "CAUGHT", f"{name}: {e}"
                    except RuntimeError as e:
                        if "does not compile" in str(e):
                            return index, "ERROR", str(e)[:300]
                        return index, "ERROR", f"{name}: {e}"
                return index, "NOT CAUGHT", ", ".join(names)

            chosen_mutants = [i for i in range(len(MUTANTS)) if not a.mutant or a.mutant in MUTANTS[i][1]]
            with ThreadPoolExecutor(max_workers=a.jobs) as pool:
                for index, verdict, line in pool.map(mutant, chosen_mutants):
                    f, label, _, _ = MUTANTS[index]
                    print(f"mutant {index + 1} ({f}: {label}): {verdict}: {line[:220]}", flush=True)
                    if verdict == "CAUGHT":
                        caught += 1
            print(f"mutants caught: {caught}/{len(chosen_mutants)}")
            if caught != len(chosen_mutants):
                raise SystemExit("FAIL")
    print("PASS")


if __name__ == "__main__":
    main()
