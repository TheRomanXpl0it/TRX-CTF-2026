; Convention
; mem[0] = N Board
; mem[1]  = column
; mem[2]  = row
; mem[3]  = utility
; mem[4]  = utility
; mem[42] = return output
; mem[69] = i
; mem[70] = j
; mem[4096 + colm*256 + row] = chessboard matrix

PUSH 256
STORE_MEM 0

CALL fill_input
LOAD_MEM 42
JZ invalid
CALL valid
LOAD_MEM 42
JZ invalid
PRINT_OK
HALT

invalid:
PRINT_ERR
HALT

fill_input:
RAND 8
PUSH 4
SUB
STORE_MEM 6

RAND 8
PUSH 4
SUB
STORE_MEM 7

LOAD_MEM 6
PUSH 127
ADD
PUSH 256
MUL
LOAD_MEM 7
PUSH 129
ADD
ADD
PUSH 4096
ADD
STORE_MEM 3
PUSH 1
LOAD_MEM 3
PUSH 0
XOR
STORE_IND

LOAD_MEM 6
PUSH 23
ADD
PUSH 256
MUL
LOAD_MEM 7
PUSH 45
ADD
ADD
PUSH 4096
ADD
STORE_MEM 3
PUSH 1
LOAD_MEM 3
PUSH 0
XOR
STORE_IND
PUSH 2
STORE_MEM 69
loop_input:
LOAD_MEM 69
LOAD_MEM 0
LT
JZ input_done

READ_INT
STORE_MEM 1
STORE_MEM 2

LOAD_MEM 1
PUSH 0
LT
JNZ input_invalid

LOAD_MEM 1
LOAD_MEM 0
LT
JZ input_invalid

LOAD_MEM 2
PUSH 0
LT
JNZ input_invalid

LOAD_MEM 2
LOAD_MEM 0
LT
JZ input_invalid

LOAD_MEM 2
PUSH 256
MUL
LOAD_MEM 1
ADD
PUSH 4096
ADD
STORE_MEM 3
LOAD_MEM 3
LOAD_IND
JNZ input_invalid

PUSH 1
LOAD_MEM 3
PUSH 0
XOR
STORE_IND

LOAD_MEM 69
PUSH 1
ADD
STORE_MEM 69
JUMP loop_input

input_invalid:
PUSH 0
STORE_MEM 42
RET

input_done:
PUSH 1
STORE_MEM 42
RET

valid:
PUSH 3
PUSH 2
SUB
STORE_MEM 42
CALL validate_rows
CALL validate_cols
CALL validate_diag
RET

validate_rows:
PUSH 0
STORE_MEM 69
one_cycle:
LOAD_MEM 69
LOAD_MEM 0
LT
JZ rows_done

PUSH 0
STORE_MEM 1
PUSH 0
STORE_MEM 70

row_col_loop:
LOAD_MEM 70
LOAD_MEM 0
LT
JZ row_done

LOAD_MEM 69
PUSH 256
MUL
LOAD_MEM 70
ADD
PUSH 4096
ADD
LOAD_IND
LOAD_MEM 1
ADD
STORE_MEM 1

LOAD_MEM 70
PUSH 1
ADD
STORE_MEM 70
JUMP row_col_loop

row_done:
LOAD_MEM 1
PUSH 1
GT
JZ rows_continue
PUSH 0
STORE_MEM 42
rows_continue:

LOAD_MEM 69
PUSH 1
ADD
STORE_MEM 69
JUMP one_cycle

rows_done:
RET

validate_cols:
PUSH 0
STORE_MEM 69
col_cycle:
LOAD_MEM 69
LOAD_MEM 0
LT
JZ cols_done

PUSH 0
STORE_MEM 1
PUSH 0
STORE_MEM 70

col_row_loop:
LOAD_MEM 70
LOAD_MEM 0
LT
JZ col_done

LOAD_MEM 70
PUSH 256
MUL
LOAD_MEM 69
ADD
PUSH 4096
ADD
LOAD_IND
LOAD_MEM 1
ADD
STORE_MEM 1

LOAD_MEM 70
PUSH 1
ADD
STORE_MEM 70
JUMP col_row_loop

col_done:
LOAD_MEM 1
PUSH 1
GT
JZ cols_continue
PUSH 0
STORE_MEM 42
cols_continue:

LOAD_MEM 69
PUSH 1
ADD
STORE_MEM 69
JUMP col_cycle

cols_done:
RET

validate_diag:
LOAD_MEM 0
PUSH 1
SUB
STORE_MEM 3

PUSH 0
LOAD_MEM 3
SUB
STORE_MEM 1

diag1_loop:
LOAD_MEM 1
LOAD_MEM 3
GT
JNZ diag2_setup

PUSH 0
STORE_MEM 2
PUSH 0
STORE_MEM 69

diag1_row_loop:
LOAD_MEM 69
LOAD_MEM 0
LT
JZ diag1_done

LOAD_MEM 69
LOAD_MEM 1
ADD
STORE_MEM 4

LOAD_MEM 4
PUSH 0
LT
JNZ diag1_next_row

LOAD_MEM 4
LOAD_MEM 0
LT
JZ diag1_next_row

LOAD_MEM 69
PUSH 256
MUL
LOAD_MEM 4
ADD
PUSH 4096
ADD
LOAD_IND
LOAD_MEM 2
ADD
STORE_MEM 2

diag1_next_row:
LOAD_MEM 69
PUSH 1
ADD
STORE_MEM 69
JUMP diag1_row_loop

diag1_done:
LOAD_MEM 2
PUSH 1
GT
JZ diag1_continue
PUSH 0
STORE_MEM 42
diag1_continue:

LOAD_MEM 1
PUSH 1
ADD
STORE_MEM 1
JUMP diag1_loop

diag2_setup:
PUSH 0
STORE_MEM 1

diag2_loop:
LOAD_MEM 1
LOAD_MEM 3
PUSH 2
MUL
GT
JNZ diag_done

PUSH 0
STORE_MEM 2
PUSH 0
STORE_MEM 69

diag2_row_loop:
LOAD_MEM 69
LOAD_MEM 0
LT
JZ diag2_done

LOAD_MEM 1
LOAD_MEM 69
SUB
STORE_MEM 4

LOAD_MEM 4
PUSH 0
LT
JNZ diag2_next_row

LOAD_MEM 4
LOAD_MEM 0
LT
JZ diag2_next_row

LOAD_MEM 69
PUSH 256
MUL
LOAD_MEM 4
ADD
PUSH 4096
ADD
LOAD_IND
LOAD_MEM 2
ADD
STORE_MEM 2

diag2_next_row:
LOAD_MEM 69
PUSH 1
ADD
STORE_MEM 69
JUMP diag2_row_loop

diag2_done:
LOAD_MEM 2
PUSH 1
GT
JZ diag2_continue
PUSH 0
STORE_MEM 42
diag2_continue:

LOAD_MEM 1
PUSH 1
ADD
STORE_MEM 1
JUMP diag2_loop

diag_done:
RET
