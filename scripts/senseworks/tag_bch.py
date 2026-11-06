"""The senseworks tag packet and its BCH code: the reference of the ble-tx-tag-* and ble-tx-poc transmitters.

Author: Miguel Simões
(ble-tx-poc, 2026-11-06: S bytes of sensor, 1 or 2; TxAdd a choice. ble-tx-tag-8 and ble-tx-tag-1byte are
S = 2 and S = 1 of this file)

The tag sends one Legacy Advertising PDU, ADV_NONCONN_IND, with a fixed format, S bytes of sensor:

  byte  0      header byte 0: PDU type ADV_NONCONN_IND, TxAdd: 0x42 with TxAdd = 1 (AdvA is random
               static), 0x02 with TxAdd = 0 (AdvA is public, as the EUI-48 of the proof of concept)
  byte  1      header byte 1: the payload length L = 6 + 4 + S + P
  bytes 2..7   AdvA, least significant byte first (the chip's: ROM, OTP or the EEPROM's EUI-48)
  byte  8      AD length: 3 + S + P (one AD structure, Manufacturer Specific Data)
  byte  9      AD type 0xFF
  bytes 10..11 Company ID, least significant byte first
  bytes 12..   the sensor's S bytes, d0 (d1)
  then         P bytes of BCH parity

The BCH code is a shortened binary BCH code of length 255 over GF(2^8) (primitive polynomial
x^8 + x^4 + x^3 + x^2 + 1), designed distance 2t + 1, its generator g(x) the least common multiple of
the minimal polynomials of alpha^1 .. alpha^2t. The message is the 48 + 8S bits that the receiver does
not know: AdvA (bytes 2..7) and the sensor, in the order they are sent (bytes in order, each least
significant bit first). The encoding is systematic, as a serial LFSR does it: the message bits enter
the division by g(x) in that order, the first one the highest power; the parity bits follow the
message, the remainder's highest coefficient first, and are packed into the bytes after the sensor,
least significant bit first, as every PDU byte. When 8P is more than deg g (t = 12: 92 of 96 bits;
t = 18: 124 of 128), the last 8P - deg g bits are 0.

  t   deg g  P  S = 1: L  PDU  on air            S = 2: L  PDU  on air
  8    64    8     19     21   29 bytes, 232 us     20     22   30 bytes, 240 us
  12   92   12     23     25   33 bytes, 264 us     24     26   34 bytes, 272 us
  18  124   16     27     29   37 bytes, 296 us     28     30   38 bytes, 304 us

  python3 scripts/senseworks/tag_bch.py --self-test     the code's properties, encoder and decoder
  python3 scripts/senseworks/tag_bch.py --verilog       the generators as the RTL holds them
"""

from __future__ import annotations

import argparse
import random

PRIMITIVE = 0x11D          # x^8 + x^4 + x^3 + x^2 + 1
N_FULL = 255
TS = (8, 12, 18)
SENSOR_SIZES = (1, 2)      # S, the bytes of sensor
AD_TYPE = 0xFF
DEFAULT_COMPANY_ID = 0xFFFF  # the value for tests: a product needs its own, assigned by the SIG
SENSOR_OFFSET = 12

# GF(2^8): exponent and logarithm tables
EXP = [0] * 510
LOG = [0] * 256
_x = 1
for _i in range(255):
    EXP[_i] = _x
    LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= PRIMITIVE
for _i in range(255, 510):
    EXP[_i] = EXP[_i - 255]


def gf_mul(a: int, b: int) -> int:
    return 0 if a == 0 or b == 0 else EXP[LOG[a] + LOG[b]]


def gf_inv(a: int) -> int:
    return EXP[255 - LOG[a]]


def poly2_mul(a: int, b: int) -> int:
    """Product of two polynomials over GF(2), bit k = coefficient of x^k."""
    r = 0
    while b:
        if b & 1:
            r ^= a
        a <<= 1
        b >>= 1
    return r


def minimal_polynomial(i: int) -> int:
    """The minimal polynomial over GF(2) of alpha^i: the product of (x - alpha^j) over its conjugates."""
    conj, j = [], i % 255
    while j not in conj:
        conj.append(j)
        j = (2 * j) % 255
    poly = [1]                               # coefficients in GF(2^8), poly[k] of x^k
    for c in conj:
        root = EXP[c]
        nxt = [0] * (len(poly) + 1)
        for k, coef in enumerate(poly):
            nxt[k + 1] ^= coef
            nxt[k] ^= gf_mul(coef, root)
        poly = nxt
    assert all(c in (0, 1) for c in poly), "a minimal polynomial has binary coefficients"
    return sum(c << k for k, c in enumerate(poly))


def generator(t: int) -> int:
    g, used = 1, set()
    for i in range(1, 2 * t + 1):
        m = minimal_polynomial(i)
        if m not in used:
            used.add(m)
            g = poly2_mul(g, m)
    return g


GENERATORS = {t: generator(t) for t in TS}


def degree(t: int) -> int:
    return GENERATORS[t].bit_length() - 1


def parity_bytes(t: int) -> int:
    return (degree(t) + 7) // 8


def message_length(sensor_bytes: int) -> int:
    """AdvA and the sensor, in bits."""
    return 48 + 8 * sensor_bytes


def payload_length(t: int, sensor_bytes: int) -> int:
    return 10 + sensor_bytes + parity_bytes(t)


def sensor_size(pdu: bytes, t: int) -> int:
    """The bytes of sensor of a PDU of this code, from its header (the length, which the tag fixes)."""
    return pdu[1] - 10 - parity_bytes(t)


def encode_bits(message: list[int], t: int) -> list[int]:
    """The parity bits of a message (bits in the order sent), in the order sent."""
    g, deg = GENERATORS[t], degree(t)
    low, mask, r = g ^ (1 << deg), (1 << deg) - 1, 0
    for b in message:
        feedback = b ^ ((r >> (deg - 1)) & 1)
        r = (r << 1) & mask
        if feedback:
            r ^= low
    return [(r >> (deg - 1 - k)) & 1 for k in range(deg)]


def bits_of(data: bytes) -> list[int]:
    """Bytes in order, each least significant bit first (the order a BLE PDU is sent)."""
    return [(byte >> k) & 1 for byte in data for k in range(8)]


def bytes_of(bits: list[int]) -> bytes:
    bits = bits + [0] * (-len(bits) % 8)
    return bytes(sum(bits[8 * n + k] << k for k in range(8)) for n in range(len(bits) // 8))


def message_bits(adv_address: int, sensor: bytes) -> list[int]:
    """AdvA (an integer, its least significant byte sent first) and the sensor's bytes."""
    assert len(sensor) in SENSOR_SIZES and 0 <= adv_address < 1 << 48
    return bits_of(adv_address.to_bytes(6, "little") + bytes(sensor))


def tag_pdu(adv_address: int, sensor: bytes, t: int, company_id: int = DEFAULT_COMPANY_ID, tx_add: int = 1) -> bytes:
    """The whole PDU (header, AdvA, the AD structure with the sensor and the parity), without the CRC."""
    p, s = parity_bytes(t), len(sensor)
    parity = bytes_of(encode_bits(message_bits(adv_address, sensor), t))
    assert len(parity) == p
    pdu = (bytes([0x02 | (tx_add << 6), payload_length(t, s)]) + adv_address.to_bytes(6, "little") +
           bytes([3 + s + p, AD_TYPE]) + company_id.to_bytes(2, "little") + bytes(sensor) + parity)
    assert len(pdu) == 2 + payload_length(t, s)
    return pdu


def codeword_bits(pdu: bytes, t: int) -> list[int]:
    """The received codeword in a PDU: the message bits and the deg g parity bits, in the order sent."""
    parity_offset = SENSOR_OFFSET + sensor_size(pdu, t)
    bits = bits_of(pdu[2:8] + pdu[SENSOR_OFFSET:parity_offset])
    return bits + bits_of(pdu[parity_offset:parity_offset + parity_bytes(t)])[:degree(t)]


def decode_bits(word: list[int], t: int) -> list[int] | None:
    """Bounded-distance decoding (syndromes, Berlekamp-Massey, Chien search) of a word of the shortened
    code, bits in the order sent; the corrected word, or None if it is not within t of a codeword."""
    n = len(word)
    assert n - degree(t) in map(message_length, SENSOR_SIZES)
    # bit k of the word is the coefficient of x^(n-1-k)
    syndromes = []
    for j in range(1, 2 * t + 1):
        s = 0
        for k, b in enumerate(word):
            if b:
                s ^= EXP[(j * (n - 1 - k)) % 255]
        syndromes.append(s)
    if not any(syndromes):
        return list(word)
    # Berlekamp-Massey: the error locator Lambda(x), Lambda[k] of x^k
    lam, prev, l, m, b = [1], [1], 0, 1, 1
    for r in range(2 * t):
        d = syndromes[r]
        for i in range(1, l + 1):
            if i < len(lam):
                d ^= gf_mul(lam[i], syndromes[r - i])
        if d == 0:
            m += 1
            continue
        coef = gf_mul(d, gf_inv(b))
        nxt = lam + [0] * max(0, len(prev) + m - len(lam))
        for i, c in enumerate(prev):
            nxt[i + m] ^= gf_mul(coef, c)
        if 2 * l <= r:
            prev, l, b, m = lam, r + 1 - l, d, 1
        else:
            m += 1
        lam = nxt
    while len(lam) > 1 and lam[-1] == 0:
        lam.pop()
    if len(lam) - 1 != l or l > t:
        return None
    # Chien search over the positions of the shortened code: an error at degree e is a root alpha^-e
    positions = []
    for e in range(n):
        x = EXP[(255 - e) % 255]
        v, xp = 0, 1
        for c in lam:
            v ^= gf_mul(c, xp)
            xp = gf_mul(xp, x)
        if v == 0:
            positions.append(e)
    if len(positions) != l:
        return None
    fixed = list(word)
    for e in positions:
        fixed[n - 1 - e] ^= 1
    return fixed


def verilog_constants() -> str:
    lines = []
    for t in TS:
        deg = degree(t)
        low = GENERATORS[t] ^ (1 << deg)
        lines.append(f"t = {t:2}: deg {deg:3}, g(x) without x^{deg} = {deg}'h{low:0{(deg + 3) // 4}x}")
    return "\n".join(lines)


def self_test(trials: int) -> None:
    rng = random.Random(20261104)
    x255 = (1 << 255) | 1
    for t in TS:
        g, deg = GENERATORS[t], degree(t)
        # g divides x^255 + 1, and alpha^1 .. alpha^2t are its roots (the BCH bound: distance >= 2t + 1)
        rem = x255
        while rem.bit_length() - 1 >= deg:
            rem ^= g << (rem.bit_length() - 1 - deg)
        assert rem == 0, f"t={t}: g does not divide x^255 + 1"
        for j in range(1, 2 * t + 1):
            v = 0
            for k in range(deg + 1):
                if (g >> k) & 1:
                    v ^= EXP[(j * k) % 255]
            assert v == 0, f"t={t}: alpha^{j} is not a root of g"
        for s in SENSOR_SIZES:
            k_bits = message_length(s)
            assert N_FULL - deg >= k_bits
            n = k_bits + deg
            corrected = failures = miscorrected = 0
            for trial in range(trials):
                msg = [rng.getrandbits(1) for _ in range(k_bits)]
                word = msg + encode_bits(msg, t)
                # the codeword is a multiple of g: its syndromes are 0
                assert decode_bits(word, t) == word
                w = rng.randint(1, t) if trial % 2 == 0 else rng.randint(t + 1, 3 * t)
                bad = list(word)
                for k in rng.sample(range(n), w):
                    bad[k] ^= 1
                out = decode_bits(bad, t)
                if w <= t:
                    assert out == word, f"t={t}: {w} errors not corrected"
                    corrected += 1
                elif out is None:
                    failures += 1
                elif out != word:
                    miscorrected += 1
            print(f"t = {t:2}, S = {s}: deg g {deg}, n = {n}, P = {parity_bytes(t)} bytes, L = {payload_length(t, s)}: "
                  f"{corrected} words with 1..t errors all corrected; of {trials - corrected} with t+1..3t, "
                  f"{failures} detected, {miscorrected} decoded to another codeword")
    print("PASS")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--trials", type=int, default=2000)
    parser.add_argument("--verilog", action="store_true")
    args = parser.parse_args()
    if args.verilog:
        print(verilog_constants())
    if args.self_test:
        self_test(args.trials)


if __name__ == "__main__":
    main()
