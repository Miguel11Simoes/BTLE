// Simulation-only variant of scripts/layout/tx_min_gf180/pdu_buffer_ram_gf180.v: the macro inputs
// delayed by 1 ns, the hold that the layout must give them (the GF180MCU SRAM model samples its inputs
// Tdly = 100 ps after the clock; zero-delay RTL would change them at the clock).
module pdu_buffer_ram #
(
  parameter integer DATA_WIDTH = 8,
  parameter integer ADDRESS_WIDTH = 5
) (
  input wire clk,
  input wire rst,
  input wire [ADDRESS_WIDTH-1:0] write_address,
  input wire [DATA_WIDTH-1:0] write_data,
  input wire write_enable,
  input wire [ADDRESS_WIDTH-1:0] read_address,
  input wire read_enable,
  output wire [DATA_WIDTH-1:0] read_data
);
wire [ADDRESS_WIDTH-1:0] address = write_enable ? write_address : read_address;
wire #1 cen_n = !(write_enable || read_enable);
wire #1 gwen_n = !write_enable;
wire [DATA_WIDTH-1:0] #1 wen_n = {DATA_WIDTH{!write_enable}};
wire [5:0] #1 a_d = {{(6-ADDRESS_WIDTH){1'b0}}, address};
wire [DATA_WIDTH-1:0] #1 d_d = write_data;
gf180mcu_fd_ip_sram__sram64x8m8wm1 sram_i (.CLK(clk), .CEN(cen_n), .GWEN(gwen_n), .WEN(wen_n), .A(a_d), .D(d_d), .Q(read_data));
wire unused_rst = rst;
endmodule
