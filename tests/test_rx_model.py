"""Packet rejection tests for the reference used to validate the ASIC."""
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
import btlelib as bl


class ReceiverModelTests(unittest.TestCase):
    def packet(self, channel=37, length=8):
        pdu = bl.hex_string_to_bit('42' + format(length, '02x') + ''.join(format((j*73+17)&255, '02x') for j in range(length)))
        init = bl.hex_string_to_bit('555555')
        aa = bl.hex_string_to_bit('D6BE898E')
        frame = bl.scramble(np.concatenate((np.zeros(8,dtype=np.int8), aa, pdu, bl.crc24_core(pdu,init))), channel)[8:]
        return pdu, init, frame

    def test_valid_frames_all_channels(self):
        for channel in range(40):
            for length in (0,1,8,31):
                pdu,init,frame=self.packet(channel,length)
                actual,good,n=bl.decode_phy_bits(frame,channel,init)
                self.assertTrue(good,(channel,length))
                np.testing.assert_array_equal(actual,pdu)
                self.assertEqual(n,length)

    def test_every_truncation_is_rejected(self):
        for channel in (0,10,37,39):
            for length in (0,1,8,31):
                pdu,init,frame=self.packet(channel,length)
                for cut in range(len(frame)):
                    _,good,_=bl.decode_phy_bits(frame[:cut],channel,init)
                    self.assertFalse(good,(channel,length,cut))

    def test_each_single_bit_error_in_pdu_or_crc_is_rejected(self):
        _,init,frame=self.packet()
        for k in range(32,len(frame)):
            bad=frame.copy();bad[k]^=1
            self.assertFalse(bl.decode_phy_bits(bad,37,init)[1],k)

    def test_noise_still_exports_real_unit_stimuli(self):
        old=(bl.SAVE_FOR_VERILOG,bl.SAVE_DIR)
        with tempfile.TemporaryDirectory() as temp:
            try:
                bl.SAVE_FOR_VERILOG=1;bl.SAVE_DIR=temp
                result=bl.btle_rx(np.zeros(101),np.zeros(101))
                self.assertFalse(result[1]);self.assertEqual(len(result[0]),0)
                p=Path(temp)
                self.assertEqual(len((p/'btle_rx_btle_rx_core_test_input_i.txt').read_text().split()),13)
                self.assertEqual(len((p/'btle_rx_gfsk_demodulation_test_output_bit_ref.txt').read_text().split()),12)
                self.assertEqual((p/'btle_rx_btle_rx_core_test_output_crc_ok_ref.txt').read_text().strip(),'0')
            finally:bl.SAVE_FOR_VERILOG,bl.SAVE_DIR=old

    def test_short_captures_and_input_contract(self):
        for n in range(17):
            self.assertFalse(bl.btle_rx(np.zeros(n),np.zeros(n))[1])
        with self.assertRaises(ValueError):bl.btle_rx([0],[0,1])
        with self.assertRaises(ValueError):bl.btle_rx([0],[0],40)
        with self.assertRaises(ValueError):bl.btle_rx([0],[0],37,[0])

if __name__=='__main__':unittest.main()
