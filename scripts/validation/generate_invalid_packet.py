"""Generate a complete packet with a deliberately wrong CRC initialization."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'python'))
from btlelib import btle_tx,btle_rx,hex_string_to_bit
vec=Path(sys.argv[1]);config=(vec/'btle_config.txt').read_text().split()
ch=int(config[1],16);init=hex_string_to_bit(config[2]);bad=init.copy();bad[0]^=1
packet=''.join((vec/'btle_tx_test_input.txt').read_text().split())
i,q,_,_=btle_tx(hex_string_to_bit(packet),ch,bad,config[3])
if btle_rx(i,q,ch,init,config[3])[1]:raise RuntimeError('bad CRC packet was accepted by the model')
for suffix,data in [('i',i),('q',q)]:np.savetxt(vec/('btle_rx_invalid_input_'+suffix+'.txt'),data,fmt='%d')
