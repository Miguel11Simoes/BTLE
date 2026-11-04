# usage: vivado -mode batch -source post.tcl -tclargs <root> [configurations] (default: those of TX_FINAL_DECISIONS.md)
set root [lindex $argv 0]
set names [lrange $argv 1 end]
if {[llength $names] == 0} { set names {up2024 upstream master rom min minflops} }
foreach n $names {
  set d $root/$n
  open_checkpoint $d/routed.dcp
  report_power -format xml -file $d/power.xml
  report_power -hierarchical_depth 6 -file $d/power_hier.rpt
  if {$n eq "up2024"} {
    report_timing -max_paths 1 -nworst 1 -group [get_clocks clk] -file $d/worst_bb.rpt
    report_timing -max_paths 1 -nworst 1 -from [get_cells -hier -filter {NAME =~ *btle_rx_i*} -quiet] -to [get_cells -hier -filter {NAME =~ *btle_rx_i*} -quiet] -file $d/worst_rx.rpt
  } else {
    report_timing -max_paths 1 -nworst 1 -group [get_clocks bb_clk] -file $d/worst_bb.rpt
    report_timing -max_paths 1 -nworst 1 -group [get_clocks axi_clk] -file $d/worst_axi.rpt
    report_timing -max_paths 1 -nworst 1 -from [get_cells -hier -filter {NAME =~ *btle_tx_i*} -quiet] -to [get_cells -hier -filter {NAME =~ *btle_tx_i*} -quiet] -file $d/worst_tx.rpt
    # the senseworks tag (ble-tx-tag-*) has no receiver: no btle_rx cells, no worst_rx.rpt
    if {[llength [get_cells -hier -filter {NAME =~ *btle_rx_i*} -quiet]] > 0} {
      report_timing -max_paths 1 -nworst 1 -from [get_cells -hier -filter {NAME =~ *btle_rx_i*} -quiet] -to [get_cells -hier -filter {NAME =~ *btle_rx_i*} -quiet] -file $d/worst_rx.rpt
    }
  }
  close_design
}
puts POST_DONE
