#!/usr/bin/env python3
"""The sensors of ble-tx-poc-gen: each one's profile as what the bus does, slot by slot, compiled into verilog/tag_profiles.v.

Author: Miguel Simões

A slot is one bit on the bus, four ticks (verilog/tag_fsm.v). A profile is the list of slots of an event, ending just
before the packet. A profile says the sensor's address or chip select, the SPI mode, the commands, the times and the
bytes to read; the two bytes kept go in the packet as read, and the gateway converts them. Each sensor's sequence, from
its datasheet (docs/Senseworks/TX_POC_GEN.md section 3):

  TMP100   I2C 0x48. START 0x90 0x01 0x81 STOP: 9 bits, shutdown, one conversion. 75 ms, the maximum. START 0x90 0x00 STOP,
           START 0x91 two bytes STOP. Two's complement, 1/256 degC per unit, low 7 bits 0.
  TMP114   I2C 0x48 (TMP114A). START 0x90 0x03 0x00 0x1C STOP: shutdown, one conversion (no averaging). 7.5 ms, the maximum.
           START 0x90 0x00, repeated START 0x91 two bytes STOP. Two's complement, 1/128 degC per unit.
  MAX31875 I2C 0x48 (R0). START 0x90 0x01 0x01 0x21 STOP: 9 bits, shutdown, one conversion. 25 ms, half of the 50 ms maximum
           at 10 bits. START 0x90 0x00, repeated START 0x91 two bytes STOP. Two's complement, 1/256 degC per unit, low 7 bits 0.
  TMP126   SPI, three wires, SCLK idle high. CS_n low, 0x0003 0x001E, CS_n high: shutdown, one conversion. 7.5 ms, the maximum.
           CS_n low, 0x0100, two bytes in, CS_n high. Two's complement, 1/32 degC per 8 units, low 2 bits 0.

  python3 scripts/senseworks/tag_profile.py --output verilog/tag_profiles.v [--sensors a,b,c,d]
  python3 scripts/senseworks/tag_profile.py --check verilog/tag_profiles.v
  python3 scripts/senseworks/tag_profile.py --show
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

# The codes of a slot (verilog/tag_fsm.v): [2] a bit on the bus; then [1] the bit goes into the packet's register, [0] SDA
# low; [2] = 0: [0] START (with SPI: CS_n falls), [1] STOP, 0: nothing.
IDLE, START, STOP, W1, W0, KEEP = 0, 1, 2, 4, 5, 6
TICKS_PER_SLOT = 4
TICK_HZ = 32768
SLOT_BITS = 10            # the last 2^12 ticks of a period: every period, 125 ms the shortest, has room for them
ADV_DELAY_SLOTS = 64      # advDelay takes up to 255 ticks from the start of those


def byte_slots(value: int) -> list[int]:
    return [W0 if not (value >> (7 - k)) & 1 else W1 for k in range(8)]


def i2c_write(address: int, data: list[int]) -> list[int]:
    """START, the address, the bytes, each with the sensor's ACK, STOP, and a slot of bus free."""
    slots = [START] + byte_slots(address << 1) + [W1]
    for d in data:
        slots += byte_slots(d) + [W1]
    return slots + [STOP, IDLE]


def i2c_pointer(address: int, pointer: int) -> list[int]:
    """The pointer of a read, closed by the repeated START that follows, not by a STOP."""
    return [START] + byte_slots(address << 1) + [W1] + byte_slots(pointer) + [W1]


def i2c_read(address: int, count: int = 2, keep: tuple[int, ...] = (0, 1)) -> list[int]:
    """START, the address, the bytes read, acknowledged but for the last, those in keep into the packet, STOP."""
    slots = [START] + byte_slots((address << 1) | 1) + [W1]
    for k in range(count):
        slots += [KEEP if k in keep else W1] * 8
        slots += [W0] if k < count - 1 else [W1]
    return slots + [STOP]


def spi_frame(words: list[int], read_bits: int = 0, keep_from: int = 0) -> list[int]:
    """CS_n low, 16-bit words out, bits in (the 16 from keep_from into the packet), CS_n high, and a slot with it high."""
    slots = [START]
    for w in words:
        slots += byte_slots(w >> 8) + byte_slots(w & 0xFF)
    slots += [KEEP if keep_from <= k < keep_from + 16 else W1 for k in range(read_bits)]
    return slots + [STOP, IDLE]


def wait_ms(ms: float) -> list[int]:
    return [IDLE] * math.ceil(ms / 1000 * TICK_HZ / TICKS_PER_SLOT)


class Sensor:
    def __init__(self, name: str, slots: list[int], spi: bool = False, cpol0: bool = False):
        self.name, self.slots, self.spi, self.cpol0 = name, slots, spi, cpol0


def sensors() -> dict[str, Sensor]:
    tmp100 = i2c_write(0x48, [0x01, 0x81]) + wait_ms(75) + i2c_write(0x48, [0x00]) + i2c_read(0x48)
    tmp114 = i2c_write(0x48, [0x03, 0x00, 0x1C]) + wait_ms(7.5) + i2c_pointer(0x48, 0x00) + i2c_read(0x48)
    max31875 = i2c_write(0x48, [0x01, 0x01, 0x21]) + wait_ms(25) + i2c_pointer(0x48, 0x00) + i2c_read(0x48)
    tmp126 = spi_frame([0x0003, 0x001E]) + wait_ms(7.5) + spi_frame([0x0100], read_bits=16)[:-1]
    # shapes of other parts, for the tests of the generality: SPI mode 0, 16 bits read with no command (MAX6675)
    max6675 = spi_frame([], read_bits=16)[:-1]
    return {"tmp100": Sensor("tmp100", tmp100), "tmp114": Sensor("tmp114", tmp114), "max31875": Sensor("max31875", max31875),
            "tmp126": Sensor("tmp126", tmp126, spi=True), "max6675": Sensor("max6675", max6675, spi=True, cpol0=True)}


DEFAULT = ["tmp100", "tmp114", "max31875", "tmp126"]


def table(sensor: Sensor) -> list[int]:
    length = 1 << SLOT_BITS
    if len(sensor.slots) > length - ADV_DELAY_SLOTS:
        raise ValueError(f"{sensor.name}: {len(sensor.slots)} slots, at most {length - ADV_DELAY_SLOTS}")
    return [IDLE] * (length - len(sensor.slots)) + sensor.slots


def verilog(names: list[str]) -> str:
    all_sensors = sensors()
    if len(names) != 4:
        raise ValueError("four profiles, chosen by two pins")
    out = ["// Author: Miguel Simões", "// SPDX-FileCopyrightText: 2026 Miguel Simões", "// SPDX-License-Identifier: Apache-2.0", "",
           f"// Generated by scripts/senseworks/tag_profile.py, do not edit: {', '.join(names)}.",
           "// What the bus does in each slot of an event, by sensor: one bit of the slot's code per table (verilog/tag_fsm.v).",
           "// All constants, so that synthesis leaves only the logic these sequences use.", "",
           "`timescale 1ns / 1ps", "module tag_profiles (", "  input  wire [1:0] sel,", f"  input  wire [{SLOT_BITS - 1}:0] slot,",
           "  output wire [2:0] code,", "  output wire spi,", "  output wire cpol0", ");", ""]
    length = 1 << SLOT_BITS
    for k, name in enumerate(names):
        codes = table(all_sensors[name])
        out.append(f"// {name}: {len(all_sensors[name].slots)} slots")
        for bit in range(3):
            value = sum(((c >> bit) & 1) << i for i, c in enumerate(codes))
            out.append(f"localparam [{length - 1}:0] T{k}_{bit} = {length}'h{value:0{length // 4}x};")
        out.append(f"wire [2:0] code{k} = {{T{k}_2[slot], T{k}_1[slot], T{k}_0[slot]}};")
    spi = "".join("1" if all_sensors[n].spi else "0" for n in reversed(names))
    cpol = "".join("1" if all_sensors[n].cpol0 else "0" for n in reversed(names))
    out += ["", "assign code = (sel == 2'd0) ? code0 : (sel == 2'd1) ? code1 : (sel == 2'd2) ? code2 : code3;",
            f"wire [3:0] spi_of = 4'b{spi};", f"wire [3:0] cpol0_of = 4'b{cpol};", "assign spi = spi_of[sel];", "assign cpol0 = cpol0_of[sel];",
            "", "endmodule", ""]
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", type=Path)
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--sensors", default=",".join(DEFAULT))
    a = parser.parse_args()
    names = a.sensors.split(",")
    text = verilog(names)
    if a.output:
        a.output.write_text(text)
    if a.check:
        if a.check.read_text() != text:
            sys.exit(f"FAIL: {a.check} is not what this script generates")
        print(f"PASS: {a.check} is what this script generates")
    if a.show:
        for n, s in sensors().items():
            busy = sum(c != IDLE for c in s.slots)
            print(f"{n}: {len(s.slots)} slots, {busy} on the bus, {len(s.slots) * TICKS_PER_SLOT / TICK_HZ * 1000:.1f} ms, {'SPI' if s.spi else 'I2C'}")


if __name__ == "__main__":
    main()
