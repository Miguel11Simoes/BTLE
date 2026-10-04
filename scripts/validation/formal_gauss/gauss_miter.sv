// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0
//
// Formal miter for optimisation B2: the upstream runtime-tap Gaussian FIR
// (gauss_filter_ref, taken from the reference revision and renamed) against
// gauss_filter with GAUSS_TABLE = 1 (the constant taps).
//
// Supported configuration: the FIR is loaded, through its own tap interface,
// with the taps the table was built from (GAUSS_TABLE_TAPS, default = BLE
// BT = 0.5), before any sample is sent. The miter does exactly that: after
// reset it writes taps 0..8 on 9 consecutive clocks, then parks the index
// (15 = no write). During loading no sample is valid (assumption); after it,
// bit_upsample, bit_upsample_valid and bit_upsample_valid_last are free on
// every clock. rst is free too: every reset restarts the loading.
// Property: from the end of loading, the three outputs are equal on every clock.

module gauss_miter (
  input wire clk,
  input wire rst,
  input wire bit_upsample,
  input wire bit_upsample_valid,
  input wire bit_upsample_valid_last
);

localparam integer W = 16;
localparam [9*16-1:0] TAPS = {16'd24, 16'd22, 16'd15, 16'd9, 16'd4, 16'd1, 16'd0, 16'd0, 16'd0};

// ---------------- tap loading sequence (both designs) ----------------
reg [3:0] load_count;   // 0..8 = writing tap load_count, 9 = loaded
reg init = 1;
always @ (posedge clk) begin
  init <= 0;
  if (rst) load_count <= 0;
  else if (load_count != 9) load_count <= load_count + 1;
end
wire loaded = (load_count == 9);
wire [3:0] tap_index = loaded ? 4'd15 : load_count;
wire signed [W-1:0] tap_value = loaded ? 0 : (TAPS >> (load_count*16));

// ---------------- designs ----------------
wire signed [W-1:0] r_out, d_out;
wire r_valid, r_last, d_valid, d_last;

gauss_filter_ref #(.GAUSS_FILTER_BIT_WIDTH(W), .NUM_TAP_GAUSS_FILTER(17)) u_ref (
  .clk(clk), .rst(rst), .tap_index(tap_index), .tap_value(tap_value),
  .bit_upsample(bit_upsample), .bit_upsample_valid(bit_upsample_valid),
  .bit_upsample_valid_last(bit_upsample_valid_last),
  .bit_upsample_gauss_filter(r_out), .bit_upsample_gauss_filter_valid(r_valid),
  .bit_upsample_gauss_filter_valid_last(r_last));

gauss_filter #(.GAUSS_FILTER_BIT_WIDTH(W), .NUM_TAP_GAUSS_FILTER(17),
               .GAUSS_TABLE(1), .GAUSS_TABLE_TAPS(TAPS)) u_dut (
  .clk(clk), .rst(rst), .tap_index(tap_index), .tap_value(tap_value),
  .bit_upsample(bit_upsample), .bit_upsample_valid(bit_upsample_valid),
  .bit_upsample_valid_last(bit_upsample_valid_last),
  .bit_upsample_gauss_filter(d_out), .bit_upsample_gauss_filter_valid(d_valid),
  .bit_upsample_gauss_filter_valid_last(d_last));

// ---------------- environment and property ----------------
reg was_loaded = 0;
always @ (posedge clk) was_loaded <= loaded & ~rst;

always @ (*) begin
  if (init) assume (rst);
  if (!init && !rst && !loaded) assume (!bit_upsample_valid); // configure before transmitting
  if (was_loaded) begin
    assert (r_out == d_out);
    assert (r_valid == d_valid);
    assert (r_last == d_last);
  end
end

// ---------------- inductive invariants ----------------
genvar k;
generate
  for (k=0; k<9; k=k+1) begin : taps_loaded
    wire signed [W-1:0] t_ref = (k==0) ? u_ref.gauss_filter_tap0 : (k==1) ? u_ref.gauss_filter_tap1 :
                                (k==2) ? u_ref.gauss_filter_tap2 : (k==3) ? u_ref.gauss_filter_tap3 :
                                (k==4) ? u_ref.gauss_filter_tap4 : (k==5) ? u_ref.gauss_filter_tap5 :
                                (k==6) ? u_ref.gauss_filter_tap6 : (k==7) ? u_ref.gauss_filter_tap7 :
                                                                             u_ref.gauss_filter_tap8;
    always @ (*) if (!init && (loaded || load_count > k)) assert (t_ref == W'(TAPS >> (k*16)));
  end
endgenerate
always @ (*) begin
  if (!init) begin
    assert (u_ref.bit_upsample_store == u_dut.bit_upsample_store);
    assert (r_valid == d_valid && r_last == d_last);
    if (!loaded) assert (!r_valid && !d_valid && r_out == 0 && d_out == 0 &&
                         u_ref.bit_upsample_store == 0);
  end
end

endmodule
