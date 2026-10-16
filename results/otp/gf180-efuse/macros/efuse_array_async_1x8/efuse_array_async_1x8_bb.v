
(* blackbox *)
module efuse_array_async_1x8 #(
    parameter NWORDS = 1,
    parameter WORD_WIDTH = 8
) (
    input  [NWORDS-1:0]     BIT_SEL,
    input  [WORD_WIDTH-1:0] COL_PROG_N,
    input                   PRESET_N,
    input                   SENSE,
    output [WORD_WIDTH-1:0] OUT
);
endmodule
            