#!/usr/bin/env python3
"""The sensor profile of the tag of ble-tx-poc: the image of its configuration memory, and what it means.

Author: Miguel Simões

The profile describes the sensor to tag_core (verilog/tag_core.v); the same RTL serves another sensor
with another profile. The image, S the bytes of sensor (tag_core's SENSOR_BYTES), 32 bytes with S = 1:

  byte  0        version: 0x01
  byte  1        size: the bytes of the image, CRC included (6 + 4S + 21 + 1)
  bytes 2..3     the advertising interval, in units of 32 ticks (1 ms at 32 kHz), least significant first
  byte  4        [5:0] the channel; [6] TxAdd of an AdvA read from the EEPROM; [7] test mode (a counter
                 instead of the sensor)
  byte  5        [4:0] where the measure program starts in the programs; [5] SPI (0: I2C); [6] SPI's clock
                 idle high (mode 3; 0: mode 0); [7] the ADC (tag_core's ADC_EN = 1)
  then, S times  the capture of a byte of sensor, from the bits read during a measure program, in order:
                 [7] signed, [5:0] the bits to skip; [4:0] the bits to take, 1..16; the offset, 16 bits,
                 two's complement, least significant byte first. The byte sent is the saturation to
                 0..254 of (the bits taken + the offset); 0xFF means the sensor did not answer
  21 bytes       the programs: the boot program, then the measure program, each ended by END; unused
                 bytes 0. A step is:
                   0x00            END
                   0kkkkkkk        WAIT at least k units (of 32 ticks), k = 1..127
                   1wwwrrrh + www bytes   XFER: START (I2C) or CS low (SPI); www bytes written (I2C: the
                                   first is the address byte); rrr bytes read; STOP or CS high, unless h = 1
                 A failed acknowledge ends the program: the event sends 0xFF.
  last byte      CRC-8 of all the bytes before it: x^8 + x^2 + x + 1 (0x07), initial value 0xFF, most
                 significant bit first, no final XOR; so the CRC run over the whole image gives 0

  python3 scripts/senseworks/tag_profile.py --sensor tmp100-9 --output profile.bin    # for the EEPROM
  python3 scripts/senseworks/tag_profile.py --show profile.bin                        # read an image back
  python3 scripts/senseworks/tag_profile.py --verilog                                 # the RTL's default
  python3 scripts/senseworks/tag_profile.py --check verilog/tag_core.v                # it must match this

The image goes at address 0x00 of the 24AA02E48 (its free half is 0x00-0x7F, DS22124D section 6.3).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import math
from pathlib import Path
import re
import sys

VERSION = 1
PROG_BYTES = 21
HEADER_BYTES = 6
CAPTURE_BYTES = 4
UNIT_S_32K = 32 / 32000            # the unit of the interval and of WAIT at the FPGA's 32 kHz tick
UNIT_S_ASIC = 32 / 32768           # at the ASIC's 32.768 kHz clock: the shortest, so the one WAIT is sized for
TMP100_MAX_CONVERSION_MS = {9: 75, 10: 150, 11: 300, 12: 600}   # SBOS231I, section 6.5


def image_bytes(sensor_bytes: int) -> int:
    return HEADER_BYTES + CAPTURE_BYTES * sensor_bytes + PROG_BYTES + 1


def crc8(data: bytes) -> int:
    crc = 0xFF
    for byte in data:
        for k in range(7, -1, -1):
            feedback = ((crc >> 7) ^ (byte >> k)) & 1
            crc = (crc << 1) & 0xFF
            if feedback:
                crc ^= 0x07
    return crc


def xfer(write: list[int] | bytes = (), read: int = 0, hold: bool = False) -> list[int]:
    """An XFER step: START, the bytes written, read bytes read, STOP (unless hold)."""
    assert 0 <= len(write) <= 7 and 0 <= read <= 7, "XFER: at most 7 bytes each way"
    return [0x80 | (len(write) << 4) | (read << 1) | int(hold)] + list(write)


def wait_ms(ms: float) -> list[int]:
    """WAIT steps that last at least ms, at the FPGA's tick and at the ASIC's (the shorter unit)."""
    units = math.ceil(ms / 1000 / UNIT_S_ASIC)
    steps = []
    while units > 0:
        steps.append(min(units, 127))
        units -= steps[-1]
    return steps


END = [0x00]


@dataclass
class Capture:
    take: int
    skip: int = 0
    signed: bool = False
    offset: int = 0

    def encode(self) -> bytes:
        assert 1 <= self.take <= 16 and 0 <= self.skip <= 63 and -32768 <= self.offset <= 32767
        return bytes([(0x80 if self.signed else 0) | self.skip, self.take]) + (self.offset & 0xFFFF).to_bytes(2, "little")

    def code(self, raw_bits: list[int]) -> int:
        """The byte sent, from the bits read in order (tag_capture.v)."""
        taken = raw_bits[self.skip:self.skip + self.take]
        value = int("".join(map(str, taken)), 2) if taken else 0
        if self.signed and taken and taken[0]:
            value -= 1 << len(taken)
        return max(0, min(254, value + self.offset))


@dataclass
class Profile:
    boot: list[int]
    measure: list[int]
    captures: list[Capture]
    interval: int = 1000           # units of 32 ticks: 1 s at 32 kHz
    channel: int = 37
    tx_add: int = 0
    test_mode: bool = False
    spi: bool = False
    spi_cpol: bool = False
    adc: bool = False
    note: str = ""
    version: int = VERSION
    extra: dict = field(default_factory=dict)

    def image(self) -> bytes:
        s = len(self.captures)
        programs = bytes(self.boot + self.measure)
        assert s in (1, 2) and 0 <= self.interval <= 0xFFFF and 0 <= self.channel <= 39
        assert len(programs) <= PROG_BYTES, f"the programs take {len(programs)} bytes, at most {PROG_BYTES}"
        body = bytes([self.version, image_bytes(s)]) + self.interval.to_bytes(2, "little")
        body += bytes([self.channel | (self.tx_add << 6) | (int(self.test_mode) << 7),
                       len(self.boot) | (int(self.spi) << 5) | (int(self.spi_cpol) << 6) | (int(self.adc) << 7)])
        body += b"".join(c.encode() for c in self.captures)
        body += programs + bytes(PROG_BYTES - len(programs))
        return body + bytes([crc8(body)])


def tmp100(bits: int = 9, t_min: float = -40.0, interval: int = 1000, channel: int = 37, address: int = 0x48,
           test_mode: bool = False, tx_add: int = 0) -> Profile:
    """The TI TMP100 (SBOS231I): shutdown at boot, a one-shot per event, the wait of the slowest conversion.

    Reading OS gives the comparator, not the end of the conversion (section 7.5.3.6), so the program waits
    the maximum conversion time. The boot program waits too: the device starts in continuous conversion, and
    OS only starts a conversion once it has shut down (section 7.5.3.1). step = 2^(9-bits) ... 0.5 degC at 9.
    """
    assert bits in TMP100_MAX_CONVERSION_MS
    resolution = (bits - 9) << 5
    step = 0.5 / (1 << (bits - 9))
    write, read = address << 1, (address << 1) | 1
    boot = xfer([write, 0x01, 0x01 | resolution]) + wait_ms(TMP100_MAX_CONVERSION_MS[9]) + END
    measure = (xfer([write, 0x01, 0x81 | resolution]) + wait_ms(TMP100_MAX_CONVERSION_MS[bits]) +
               xfer([write, 0x00], hold=True) + xfer([read], read=2) + END)
    capture = Capture(take=bits, signed=True, offset=round(-t_min / step))
    return Profile(boot, measure, [capture], interval=interval, channel=channel, tx_add=tx_add, test_mode=test_mode,
                   note=f"TMP100, {bits} bits: step {step} degC, N = 0 at {t_min} degC")


def temperature(code: int, bits: int = 9, t_min: float = -40.0) -> float | None:
    """What the gateway computes from the byte sent (None: the sensor did not answer)."""
    return None if code == 0xFF else t_min + code * 0.5 / (1 << (bits - 9))


SENSORS = {
    "tmp100-9": lambda **kw: tmp100(9, -40.0, **kw),     # the default: 0.5 degC from -40 to +87 degC
    "tmp100-10": lambda **kw: tmp100(10, -10.0, **kw),   # 0.25 degC from -10 to +53.5 degC
    "tmp100-12": lambda **kw: tmp100(12, 10.0, **kw),    # 0.0625 degC from +10 to +25.875 degC
}


def default_image() -> bytes:
    return tmp100().image()


def verilog_constant(image: bytes) -> str:
    return f"{8 * len(image)}'h{image.hex()}"


def show(image: bytes) -> str:
    s = (len(image) - HEADER_BYTES - PROG_BYTES - 1) // CAPTURE_BYTES
    lines = [f"{len(image)} bytes, {s} byte(s) of sensor, version {image[0]}, size {image[1]}, "
             f"CRC {'right' if crc8(image) == 0 else 'WRONG'}",
             f"interval {int.from_bytes(image[2:4], 'little')} units, channel {image[4] & 63}, TxAdd {(image[4] >> 6) & 1}, "
             f"test mode {image[4] >> 7}",
             f"measure program at {image[5] & 31}, {'SPI mode ' + ('3' if image[5] & 64 else '0') if image[5] & 32 else 'I2C'}"
             f"{', ADC' if image[5] & 128 else ''}"]
    for c in range(s):
        b = image[HEADER_BYTES + CAPTURE_BYTES * c:HEADER_BYTES + CAPTURE_BYTES * (c + 1)]
        lines.append(f"capture {c}: skip {b[0] & 63}, take {b[1] & 31}, {'signed' if b[0] & 128 else 'unsigned'}, "
                     f"offset {int.from_bytes(b[2:4], 'little', signed=True)}")
    programs, pc = image[HEADER_BYTES + CAPTURE_BYTES * s:-1], 0
    while pc < len(programs):
        op = programs[pc]
        if op & 0x80:
            w, r = (op >> 4) & 7, (op >> 1) & 7
            lines.append(f"  {pc:2}: XFER write {programs[pc + 1:pc + 1 + w].hex(' ')} read {r}{' hold' if op & 1 else ''}")
            pc += 1 + w
        elif op:
            lines.append(f"  {pc:2}: WAIT {op}")
            pc += 1
        else:
            lines.append(f"  {pc:2}: END")
            pc += 1
            if pc > (image[5] & 31):
                break
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--sensor", choices=sorted(SENSORS), default="tmp100-9")
    parser.add_argument("--interval", type=int, default=1000, help="units of 32 ticks (1 ms at 32 kHz)")
    parser.add_argument("--channel", type=int, default=37)
    parser.add_argument("--test-mode", action="store_true", help="a counter instead of the sensor")
    parser.add_argument("--output", type=Path, help="write the image (.bin), and .hex next to it")
    parser.add_argument("--show", type=Path, help="read an image back")
    parser.add_argument("--verilog", action="store_true", help="the default profile, as tag_core.v holds it")
    parser.add_argument("--check", type=Path, help="tag_core.v's DEFAULT_PROFILE must be the default profile")
    args = parser.parse_args()
    if args.verilog:
        print(verilog_constant(default_image()))
    if args.check:
        m = re.search(r"parameter \[255:0\] DEFAULT_PROFILE = 256'h([0-9a-fA-F_]+)", args.check.read_text())
        if not m or bytes.fromhex(m.group(1).replace("_", "")) != default_image():
            sys.exit(f"FAIL: DEFAULT_PROFILE in {args.check} is not tag_profile.py's default ({default_image().hex()})")
        print(f"PASS: DEFAULT_PROFILE in {args.check} is tag_profile.py's default")
    if args.show:
        print(show(args.show.read_bytes()))
    if args.output:
        profile = SENSORS[args.sensor](interval=args.interval, channel=args.channel, test_mode=args.test_mode)
        image = profile.image()
        args.output.write_bytes(image)
        args.output.with_suffix(".hex").write_text("".join(f"{b:02x}\n" for b in image))
        print(f"{args.output}: {profile.note}\n{show(image)}")


if __name__ == "__main__":
    main()
