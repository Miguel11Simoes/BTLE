# usage: vivado -mode batch -source impl.tcl -tclargs <dir> <ooc|wrapper2024>
set d [lindex $argv 0]
set mode [lindex $argv 1]
set part xc7z020clg484-1
if {$mode eq "wrapper2024"} {
  # upstream's 2024 project (verilog/btle_controller.tcl at fc5bc42): its design files, top btle_controller_wrapper, its xdc
  foreach m {bit_repeat_upsample btle_controller btle_ll btle_phy btle_rx btle_rx_core btle_tx crc24 crc24_core dpram gauss_filter gfsk_demodulation gfsk_modulation rx_clk_gen scramble scramble_core search_unique_bit_sequence serial_in_ram_out tx_clk_gen uart_frame_rx uart_frame_tx vco btle_controller_wrapper} {
    read_verilog $d/verilog/$m.v
  }
  read_xdc $d/verilog/btle_controller_wrapper.xdc
  synth_design -top btle_controller_wrapper -part $part
} else {
  foreach f [glob $d/verilog/*.v] {
    set n [file tail $f]
    if {[string match *_tb.v $n] || $n eq "btle_controller_wrapper.v"} continue
    read_verilog $f
  }
  read_xdc -mode out_of_context [file dirname $d]/clocks.xdc
  synth_design -top btle_controller -part $part -mode out_of_context
}
report_utilization -file $d/synth_util.rpt
opt_design
place_design
route_design
report_utilization -file $d/impl_util.rpt
report_utilization -hierarchical -hierarchical_depth 3 -file $d/impl_util_hier.rpt
report_timing_summary -max_paths 3 -file $d/timing.rpt
report_clock_utilization -file $d/clock_util.rpt
report_power -file $d/power.rpt
report_drc -file $d/drc.rpt
write_checkpoint -force $d/routed.dcp
puts "IMPL_DONE"
