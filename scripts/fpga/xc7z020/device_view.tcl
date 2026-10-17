# usage (GUI, run by device_view.ps1): vivado -mode gui -source device_view.tcl -tclargs <dir>
# Opens <dir>/routed.dcp, highlights btle_tx's primitives in orange in the Device view, and writes what it
# highlighted to <dir>/device.txt, which also tells device_view.ps1 that the view can be captured.
set d [lindex $argv 0]
open_checkpoint $d/routed.dcp
set all [get_cells -hier -filter IS_PRIMITIVE]
set tx [filter $all {NAME =~ *btle_tx_i/*}]
highlight_objects -color orange $tx
set f [open $d/device.txt.tmp w]
puts $f "tool=Vivado [version -short], GUI, Device view (default layout, Device panel maximized, zoom to fit)"
puts $f "checkpoint=[file tail $d]/routed.dcp"
puts $f "orange=btle_tx_i: [llength $tx] of the design's [llength $all] primitives (highlight_objects -color orange)"
close $f
file rename -force $d/device.txt.tmp $d/device.txt
