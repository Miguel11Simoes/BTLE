
# PnR only (run.sh appends this to btle_tx.sdc as btle_tx_pnr.sdc; signoff keeps btle_tx.sdc and the
# library's limits): tighter targets, so that the resizer leaves margin at the ss corner.
set_max_transition 2.0 [current_design]
set_max_fanout 8 [current_design]
