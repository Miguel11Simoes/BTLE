// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0
//
// Controller-level lockstep through the AXI-lite REGISTER interface
// (baremetal_phy_intf_mode = 0, the path the boards use):
//   u_ref : upstream btle_controller (every module renamed *_ref by the runner)
//   u_dut : btle_controller of branch ble-tx-table with GAUSS_TABLE = 1
//
// Adapted from the ble-opt harness (same stimulus, same software sequence).
// On this branch nothing is removed: the IQ capture, the full Link Layer and
// the UART are still there, so EVERY output is compared on every clock,
// including bram_rddata_a, ll_itrpt2 and uart_tx, and EVERY register read must
// return the same value in both designs.
//
// The software sequence is the one firmware/btle_ll.c uses, plus TX, which no
// upstream software drives:
//   setup  : COS/SIN tables (regs 2, 3), Gaussian taps (reg 1), RX config
//            (regs 10-12), counter reset (reg 0 bit 15)
//   per packet, from the Python model's vectors, between random noise:
//     RX   : wait for interrupt 0 (decode end); read 49, the PDU words from 40,
//            write 40, read 56, 57, 10, 50, 53, 55, 41, 51
//     TX   : write 4-7, the PDU octets through 8, pulse 9; wait for the end
//   end    : read all 64 registers

`timescale 1ns / 1ps
module tb_ctl_lockstep;

localparam integer RF_IQ_BIT_WIDTH = 64;
localparam integer W16 = 16;

// ---------------- clocks and resets ----------------
reg bb_clk = 1, rf_clk = 0;
always #((1000.0/16.0)/2.0) bb_clk = !bb_clk;
always #((1000.0/8.0)/2.0)  rf_clk = !rf_clk;
reg bb_rst = 1, rf_rst = 1, aresetn = 0;

// ---------------- shared stimulus ----------------
reg  [RF_IQ_BIT_WIDTH-1:0] rx_iq_signal_ext = 0;
reg  rx_iq_valid_ext = 1;
reg  [7:0] awaddr = 0, araddr = 0;
reg  awvalid = 0, wvalid = 0, bready = 0, arvalid = 0, rready = 0;
reg  [31:0] wdata = 0;

// ---------------- designs ----------------
`define CTL_PORTS(P) \
  .rf_clk(rf_clk), .rf_rst(rf_rst), .bb_clk(bb_clk), .bb_rst(bb_rst), .gpio(8'd0), \
  .ll_gpio(P``_ll_gpio), .ll_itrpt0(P``_it0), .ll_itrpt1(P``_it1), .ll_itrpt2(P``_it2), .ll_itrpt3(P``_it3), \
  .ll_itrpt4(P``_it4), .ll_itrpt5(P``_it5), .ll_itrpt6(P``_it6), .ll_itrpt7(P``_it7), \
  .bram_addr_a(17'd0), .bram_clk_a(bb_clk), .bram_wrdata_a(32'd0), .bram_rddata_a(P``_bram_rd), \
  .bram_en_a(1'b0), .bram_rst_a(1'b0), .bram_we_a(1'b0), \
  .uart_rx(1'b1), .uart_tx(P``_uart_tx), .rf_gpio(8'd0), \
  .tx_iq_signal_ext(P``_tx_iq), .tx_iq_valid_ext(P``_tx_v), .tx_iq_valid_last_ext(P``_tx_vl), \
  .rx_iq_signal_ext(rx_iq_signal_ext), .rx_iq_valid_ext(rx_iq_valid_ext), \
  .s00_axi_aclk(bb_clk), .s00_axi_aresetn(aresetn), \
  .s00_axi_awaddr(awaddr), .s00_axi_awprot(3'd0), .s00_axi_awvalid(awvalid), .s00_axi_awready(P``_awready), \
  .s00_axi_wdata(wdata), .s00_axi_wstrb(4'hF), .s00_axi_wvalid(wvalid), .s00_axi_wready(P``_wready), \
  .s00_axi_bresp(P``_bresp), .s00_axi_bvalid(P``_bvalid), .s00_axi_bready(bready), \
  .s00_axi_araddr(araddr), .s00_axi_arprot(3'd0), .s00_axi_arvalid(arvalid), .s00_axi_arready(P``_arready), \
  .s00_axi_rdata(P``_rdata), .s00_axi_rresp(P``_rresp), .s00_axi_rvalid(P``_rvalid), .s00_axi_rready(rready), \
  .baremetal_phy_intf_mode(1'b0), \
  .ext_tx_gauss_filter_tap_index(4'd15), .ext_tx_gauss_filter_tap_value(16'd0), \
  .ext_tx_cos_table_write_address(11'd0), .ext_tx_cos_table_write_data(8'd0), \
  .ext_tx_sin_table_write_address(11'd0), .ext_tx_sin_table_write_data(8'd0), \
  .ext_tx_preamble(8'd0), .ext_tx_access_address(32'd0), .ext_tx_crc_state_init_bit(24'd0), \
  .ext_tx_crc_state_init_bit_load(1'b0), .ext_tx_channel_number(6'd0), .ext_tx_channel_number_load(1'b0), \
  .ext_tx_pdu_octet_mem_data(8'd0), .ext_tx_pdu_octet_mem_addr(9'd0), .ext_tx_start(1'b0), \
  .ext_tx_phy_bit(P``_x0), .ext_tx_phy_bit_valid(P``_x1), .ext_tx_phy_bit_valid_last(P``_x2), \
  .ext_tx_bit_upsample(P``_x3), .ext_tx_bit_upsample_valid(P``_x4), .ext_tx_bit_upsample_valid_last(P``_x5), \
  .ext_tx_bit_upsample_gauss_filter(P``_gauss), .ext_tx_bit_upsample_gauss_filter_valid(P``_x6), \
  .ext_tx_bit_upsample_gauss_filter_valid_last(P``_x7), \
  .ext_rx_unique_bit_sequence(32'd0), .ext_rx_channel_number(6'd0), .ext_rx_crc_state_init_bit(24'd0), \
  .ext_rx_hit_flag(P``_r0), .ext_rx_decode_run(P``_r1), .ext_rx_decode_end(P``_r2), .ext_rx_crc_ok(P``_r3), \
  .ext_rx_best_phase(P``_bp), .ext_rx_payload_length(P``_len), .ext_rx_pdu_octet_mem_addr(9'd0), \
  .ext_rx_pdu_octet_mem_data(P``_pdu)

`define CTL_WIRES(P) \
  wire [15:0] P``_ll_gpio; wire P``_it0, P``_it1, P``_it2, P``_it3, P``_it4, P``_it5, P``_it6, P``_it7; \
  wire [31:0] P``_bram_rd; wire P``_uart_tx; wire [RF_IQ_BIT_WIDTH-1:0] P``_tx_iq; wire P``_tx_v, P``_tx_vl; \
  wire P``_awready, P``_wready, P``_bvalid, P``_arready, P``_rvalid; wire [1:0] P``_bresp, P``_rresp; \
  wire [31:0] P``_rdata; wire P``_x0, P``_x1, P``_x2, P``_x3, P``_x4, P``_x5, P``_x6, P``_x7; \
  wire signed [15:0] P``_gauss; wire P``_r0, P``_r1, P``_r2, P``_r3; wire [2:0] P``_bp; wire [7:0] P``_len, P``_pdu;

`CTL_WIRES(r)
`CTL_WIRES(d)

btle_controller_ref u_ref ( `CTL_PORTS(r) );
btle_controller #(.GAUSS_TABLE(1)) u_dut ( `CTL_PORTS(d) );

// ---------------- clock-by-clock comparison ----------------
wire [159:0] r_vec = {r_ll_gpio, r_it0, r_it1, r_it3, r_it4, r_it5, r_it6, r_it7, r_tx_iq, r_tx_v, r_tx_vl,
                      r_awready, r_wready, r_bvalid, r_arready, r_rvalid, r_bresp, r_rresp,
                      r_x0, r_x1, r_x2, r_x3, r_x4, r_x5, r_x6, r_x7, r_gauss, r_r0, r_r1, r_r2, r_r3, r_bp, r_len, r_pdu};
wire [159:0] d_vec = {d_ll_gpio, d_it0, d_it1, d_it3, d_it4, d_it5, d_it6, d_it7, d_tx_iq, d_tx_v, d_tx_vl,
                      d_awready, d_wready, d_bvalid, d_arready, d_rvalid, d_bresp, d_rresp,
                      d_x0, d_x1, d_x2, d_x3, d_x4, d_x5, d_x6, d_x7, d_gauss, d_r0, d_r1, d_r2, d_r3, d_bp, d_len, d_pdu};
// the outputs that ble-opt removes on purpose; on this branch they are compared too
wire [33:0] r_dbg = {r_bram_rd, r_it2, r_uart_tx};
wire [33:0] d_dbg = {d_bram_rd, d_it2, d_uart_tx};
integer cycles = 0, compared = 0, mismatches = 0;
reg checking = 0;
always @ (negedge bb_clk) begin
  cycles = cycles + 1;
  if (checking) begin
    compared = compared + 1;
    if ((^{r_tx_v, d_tx_v, r_tx_vl, d_tx_vl, r_awready, d_awready,
           r_wready, d_wready, r_bvalid, d_bvalid, r_arready, d_arready,
           r_rvalid, d_rvalid}) === 1'bx)
      $fatal(1, "UNKNOWN controller handshake");
    if ((r_tx_v && (^r_tx_iq === 1'bx)) || (d_tx_v && (^d_tx_iq === 1'bx)))
      $fatal(1, "UNKNOWN valid TX sample");
    if (r_vec !== d_vec || r_dbg !== d_dbg) begin
      mismatches = mismatches + 1;
      $display("MISMATCH outputs at cycle %0d: ref %h dut %h diff %h; capture/itrpt2/uart ref %h dut %h",
               cycles, r_vec, d_vec, r_vec ^ d_vec, r_dbg, d_dbg);
      $fatal(1, "ctl lockstep FAIL");
    end
  end
end

// ---------------- AXI-lite master ----------------
initial begin #1000000000; $fatal(1, "controller watchdog timeout"); end
integer seed;
function integer rnd(input integer n); rnd = ($random(seed) & 32'h7fffffff) % n; endfunction
task idle(input integer n); integer t; begin for (t=0; t<n; t=t+1) @(posedge bb_clk); end endtask

task axi_write(input [5:0] reg_idx, input [31:0] value);
  begin
    idle(rnd(3));
    #1 awaddr = {reg_idx, 2'b00}; wdata = value; awvalid = 1; wvalid = 1;
    @(posedge bb_clk); while (!(r_awready && r_wready)) @(posedge bb_clk);
    #1 awvalid = 0; wvalid = 0; idle(rnd(3)); #1 bready = 1;
    @(posedge bb_clk); while (!r_bvalid) @(posedge bb_clk);
    #1 bready = 0;
  end
endtask

integer w, num_word, len_bytes;
integer n_reads = 0;
task axi_read(input [5:0] reg_idx, output [31:0] value);
  reg [31:0] meaningful_mask;
  begin
    idle(rnd(3));
    #1 araddr = {reg_idx, 2'b00}; arvalid = 1;
    @(posedge bb_clk); while (!r_arready) @(posedge bb_clk);
    #1 arvalid = 0; idle(rnd(3)); #1 rready = 1;
    @(posedge bb_clk); while (!r_rvalid) @(posedge bb_clk);
    value = r_rdata; n_reads = n_reads + 1;
    // The final RX RAM word may contain padding bytes never written by RX.
    // Check every delivered byte, excluding only that non-payload padding.
    meaningful_mask = 32'hffffffff;
    // Status[7:0] mirrors the unqualified live RAM port, even after its read
    // pointer has passed the packet. Packet bytes are checked through reg 40.
    if (reg_idx == 49) meaningful_mask = 32'hffffff00;
    if (reg_idx == 40 && w == num_word-1 && (len_bytes & 3) != 0)
      meaningful_mask = (32'h1 << (8*(len_bytes & 3)))-1;
    if ((^(r_rdata & meaningful_mask)) === 1'bx ||
        (^(d_rdata & meaningful_mask)) === 1'bx)
      $fatal(1, "UNKNOWN data in completed AXI read reg %0d", reg_idx);
    if (r_rdata !== d_rdata) begin    // every register: nothing is removed on this branch
      $display("MISMATCH read reg %0d at cycle %0d: ref %h dut %h", reg_idx, cycles, r_rdata, d_rdata);
      $fatal(1, "ctl lockstep FAIL");
    end
    #1 rready = 0;
  end
endtask

// ---------------- vectors (Python model) ----------------
reg [31:0] cfg_mem [0:31];
integer cos_t [0:2047], sin_t [0:2047], taps [0:16];
integer pkt_i [0:65535], pkt_q [0:65535], bad_i [0:65535], bad_q [0:65535], n_pkt;
integer tx_oct [0:511], n_oct;
integer fd, rc, a, k;
reg [31:0] aa_reg; reg [5:0] ch; reg [23:0] crcinit;

task load_int_file(input [8*64-1:0] name, output integer n, input integer which);
  begin
    fd = $fopen(name, "r"); n = 0;
    if (fd == 0) $fatal(1, "cannot open %0s", name);
    while (!$feof(fd)) begin
      rc = $fscanf(fd, "%d\n", a);
      if (rc == 1) begin
        case (which) 0: cos_t[n] = a; 1: sin_t[n] = a; 2: taps[n] = a; 3: pkt_i[n] = a; 4: pkt_q[n] = a; 5: bad_i[n] = a; 6: bad_q[n] = a; endcase
        n = n + 1;
      end
    end
    $fclose(fd);
  end
endtask

// ---------------- RX sample source (rf clock) ----------------
reg send_packet = 0; reg packet_busy = 0; reg corrupt = 0; integer amp = 0, n_tmp, n_corrupt = 0;
integer rx_k = 0;
function [15:0] noise(input integer amplitude);   // 16-bit sample
  integer x;
  begin
    x = (rnd(16) == 0) ? ((rnd(2) == 0) ? -32768 : 32767) : ($random(seed) % (amplitude+1));
    noise = x[15:0];
  end
endfunction
function [15:0] pkt_i_16(input integer idx); integer x; begin x = corrupt ? bad_i[idx] : pkt_i[idx]; pkt_i_16 = x[15:0]; end endfunction
function [15:0] pkt_q_16(input integer idx); integer x; begin x = corrupt ? bad_q[idx] : pkt_q[idx]; pkt_q_16 = x[15:0]; end endfunction
always @ (posedge rf_clk) begin
  if (!rf_rst) begin
    if (send_packet && !packet_busy) begin packet_busy <= 1; rx_k <= 0; end
    if (packet_busy) begin
      rx_iq_signal_ext <= {32'd0, pkt_q_16(rx_k), pkt_i_16(rx_k)};
      if (rx_k == n_pkt-1) packet_busy <= 0;
      rx_k <= rx_k + 1;
    end else begin
      rx_iq_signal_ext <= {32'd0, noise(amp), noise(amp)};
    end
  end
end

// ---------------- scenario ----------------
integer n_packets, p, got_irq, n_irq = 0, n_crc_ok = 0, n_tx = 0;
reg [31:0] v, status;

initial begin
  if (!$value$plusargs("seed=%d", seed)) seed = 1;
  if (!$value$plusargs("packets=%d", n_packets)) n_packets = 6;
  if (n_packets <= 0) $fatal(1, "empty controller campaign");
  $readmemh("btle_config.txt", cfg_mem, 0, 3);
  ch = cfg_mem[1]; crcinit = cfg_mem[2];
  aa_reg = {cfg_mem[3][7:0], cfg_mem[3][15:8], cfg_mem[3][23:16], cfg_mem[3][31:24]};
  load_int_file("cos_table.txt", n_tmp, 0);
  if (n_tmp != 2048) $fatal(1, "incomplete COS table");
  load_int_file("sin_table.txt", n_tmp, 1);
  if (n_tmp != 2048) $fatal(1, "incomplete SIN table");
  load_int_file("gauss_filter_tap.txt", n_tmp, 2);
  if (n_tmp != 17) $fatal(1, "incomplete Gaussian taps");
  load_int_file("btle_rx_test_input_i.txt", n_pkt, 3);
  load_int_file("btle_rx_test_input_q.txt", n_tmp, 4);
  if (n_pkt <= 0 || n_tmp != n_pkt) $fatal(1, "incomplete RX vectors");
  load_int_file("btle_rx_invalid_input_i.txt", n_tmp, 5);
  if (n_tmp != n_pkt) $fatal(1, "invalid-packet I length differs");
  load_int_file("btle_rx_invalid_input_q.txt", n_tmp, 6);
  if (n_tmp != n_pkt) $fatal(1, "invalid-packet Q length differs");
  fd = $fopen("btle_tx_test_input.txt", "r"); n_oct = 0;
  if (fd == 0) $fatal(1, "missing TX input");
  while (!$feof(fd)) begin rc = $fscanf(fd, "%h\n", a); if (rc == 1) begin tx_oct[n_oct] = a; n_oct = n_oct + 1; end end
  $fclose(fd);
  $display("ctl lockstep: seed %0d packets %0d rx samples %0d tx octets %0d AA %08h ch %0d",
           seed, n_packets, n_pkt, n_oct, aa_reg, ch);

  repeat (8) @(posedge bb_clk);
  #1 bb_rst = 0; rf_rst = 0; aresetn = 1;
  repeat (4) @(posedge bb_clk);
  #1 checking = 1;

  // setup, as software would do it
  axi_write(0, 32'h8000); axi_write(0, 32'h0);                         // counter reset (bit 15)
  for (k=0; k<2048; k=k+1) axi_write(2, (k << 16) | (cos_t[k] & 8'hFF));  // COS table
  for (k=0; k<2048; k=k+1) axi_write(3, (k << 16) | (sin_t[k] & 8'hFF));  // SIN table
  for (k=0; k<9; k=k+1)    axi_write(1, (k << 16) | (taps[k] & 16'hFFFF)); // Gaussian taps
  axi_write(1, 32'h000F0000);                                           // park the tap index
  axi_write(11, ch); axi_write(12, crcinit); axi_write(10, aa_reg);     // RX config

  for (p=0; p<n_packets; p=p+1) begin
    // ---- RX: packet from the model, between random noise ----
    case (rnd(4)) 0: amp = 0; 1: amp = 64; 2: amp = 2047; default: amp = 32767; endcase
    idle(rnd(400));
    corrupt = (rnd(3) == 0);
    if (p == 0) corrupt = 0;
    if (p == 1) corrupt = 1;
    if (corrupt) n_corrupt = n_corrupt + 1;
    #1 send_packet = 1; @(posedge rf_clk); #1 send_packet = 0;
    got_irq = 0;
    for (k=0; k<(n_pkt*2+4000) && !got_irq; k=k+1) begin @(posedge bb_clk); if (r_it0) got_irq = 1; end
    if (got_irq) begin
      n_irq = n_irq + 1;
      axi_write(39, 1);                                       // as btle_ll.c
      axi_read(49, status);
      if (status[16] !== !corrupt) $fatal(1, "unexpected controller CRC acceptance");
      if (status[16]) n_crc_ok = n_crc_ok + 1;
      len_bytes = 2 + status[15:8] + 3;
      num_word = (len_bytes >> 2) + ((len_bytes & 3) ? 1 : 0);
      for (w=0; w<num_word; w=w+1) axi_read(40, v);
      axi_write(40, 0);
      axi_read(56, v); axi_read(57, v); axi_read(10, v);
      axi_read(50, v); axi_read(53, v); axi_read(55, v); axi_read(41, v); axi_read(51, v);
      axi_write(39, 0);
    end
    // ---- TX through the registers ----
    axi_write(4, (aa_reg[0] ? 8'h55 : 8'hAA));               // preamble by AA LSB
    axi_write(5, aa_reg); axi_write(6, crcinit); axi_write(7, ch);
    for (k=0; k<n_oct; k=k+1) axi_write(8, (k << 16) | (tx_oct[k] & 8'hFF));
    axi_write(9, 1); axi_write(9, 0);
    for (k=0; k<200000 && !r_tx_vl; k=k+1) @(posedge bb_clk);
    if (r_tx_vl) n_tx = n_tx + 1;
    else $fatal(1, "TX did not complete packet %0d: state=%0d length=%0d bit_count=%0d start=%b reg9=%h", p,
       u_ref.btle_phy_i.btle_tx_i.phy_tx_state, u_ref.btle_phy_i.btle_tx_i.payload_length,
       u_ref.btle_phy_i.btle_tx_i.bit_count, u_ref.btle_phy_i.btle_tx_i.tx_start,
       u_ref.btle_ll_i.slv_reg9);
    idle(20);
    axi_read(48, v); axi_read(62, v);
  end

  // ---- every register ----
  for (k=0; k<64; k=k+1) begin
    if (k != 40) axi_read(k, v);   // 40 pops the RX buffer; read above in the firmware order
  end
  idle(50);
  $display("ctl lockstep: cycles %0d compared %0d rx_irqs %0d rx_crc_ok %0d tx_packets %0d axi_reads %0d (all compared) corrupted_packets %0d",
           cycles, compared, n_irq, n_crc_ok, n_tx, n_reads, n_corrupt);
  $display("ctl lockstep: mismatches %0d", mismatches);
  if (compared <= 0 || n_reads <= 0 || n_oct <= 0 ||
      n_tx != n_packets || n_irq != n_packets)
    $fatal(1, "INCOMPLETE controller coverage: tx=%0d rx=%0d requested=%0d", n_tx, n_irq, n_packets);
  if (mismatches == 0) $display("CTL LOCKSTEP PASS");
  $finish;
end

endmodule
