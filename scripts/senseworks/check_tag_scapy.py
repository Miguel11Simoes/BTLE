"""Parse the tag's packets with an independent BLE dissector, scapy's (layers.bluetooth4LE).

Author: Miguel Simões

Reads the JSON that tests/test_tx_tag_packet.py or tests/test_tag_core.py writes (each packet the RTL sent: access
address, PDU, CRC bits in the order sent) and checks, with scapy and nothing of this repository:
- the CRC that scapy computes over the PDU (init 0x555555) is the one the transmitter sent;
- scapy reads the PDU as ADV_NONCONN_IND, the TxAdd of the packet (its "tx_add"; 1 when absent), RxAdd
  0, the length the PDU has, AdvA the chip's;
- AdvData is exactly one AD structure, Manufacturer Specific Data, its length the rest of the PDU,
  the Company ID 0xFFFF, then the sensor's bytes and the parity.
scapy is not one of the repository's dependencies: run this with an interpreter that has it.

  python3 scripts/senseworks/check_tag_scapy.py PACKETS.json
"""

from __future__ import annotations

import json
import sys

from scapy.layers.bluetooth import EIR_Hdr, EIR_Manufacturer_Specific_Data
from scapy.layers.bluetooth4LE import BTLE, BTLE_ADV, BTLE_ADV_NONCONN_IND
from scapy.packet import Raw


def crc_bytes(bits: str) -> bytes:
    """The CRC's 24 bits, in the order sent, as the three bytes on the air (least significant bit first)."""
    return bytes(sum(int(bits[8 * n + k]) << k for k in range(8)) for n in range(3))


def main() -> None:
    rows = json.loads(open(sys.argv[1]).read())
    checked = 0
    for row in rows:
        pdu = bytes.fromhex(row["pdu"])
        sent_crc = crc_bytes(row["crc_bits"])
        crc = BTLE.compute_crc(pdu, init=0x555555)
        assert crc == sent_crc, f"{row}: scapy's CRC {crc.hex()} differs from the CRC sent {sent_crc.hex()}"
        # framed with the advertising access address whatever the channel the test sent it on (the channel
        # changes only the whitening, which the receiver has undone): scapy reads an advertising PDU
        frame = BTLE((0x8E89BED6).to_bytes(4, "little") + pdu + crc)
        adv = frame[BTLE_ADV]
        tx_add = row.get("tx_add", 1)
        assert adv.PDU_type == 2 and adv.TxAdd == tx_add and adv.RxAdd == 0 and adv.Length == len(pdu) - 2, adv.summary()
        nonconn = frame[BTLE_ADV_NONCONN_IND]
        adv_address = pdu[2:8][::-1].hex(":")
        assert nonconn.AdvA == adv_address, (nonconn.AdvA, adv_address)
        structures = nonconn.data
        assert len(structures) == 1, f"{len(structures)} AD structures"
        hdr = structures[0]
        assert isinstance(hdr, EIR_Hdr) and hdr.type == 0xFF and hdr.len == len(pdu) - 9, hdr.summary()
        mfg = hdr[EIR_Manufacturer_Specific_Data]
        assert mfg.company_identifier == 0xFFFF
        rest = bytes(mfg[Raw].load) if Raw in mfg else b""
        sensor = bytes.fromhex(row["sensor"])
        assert rest[:len(sensor)] == sensor and rest == pdu[12:], (rest.hex(), row["sensor"])
        checked += 1
    by_t = sorted({r["t"] for r in rows})
    print(f"PASS: {checked} packets (t = {by_t}): scapy's CRC equal to the one sent; ADV_NONCONN_IND, the TxAdd sent, "
          f"AdvA, one Manufacturer Specific Data structure (Company ID 0xFFFF), the sensor's bytes, the parity")


if __name__ == "__main__":
    main()
