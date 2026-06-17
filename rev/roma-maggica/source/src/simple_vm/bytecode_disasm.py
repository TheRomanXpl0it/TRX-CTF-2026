#!/usr/bin/env python3
"""
Bytecode disassembler - converts binary bytecode back to human-readable form
Useful for reverse engineering the bytecode
"""

import struct
import sys

# Opcodes
OPCODES = {
    0x00: "NOP",
    0x01: "PUSH_IMM",
    0x02: "POP",
    0x03: "DUP",
    0x04: "LOAD_REG",
    0x05: "STORE_REG",
    0x06: "LOAD_MEM",
    0x07: "STORE_MEM",
    0x08: "ADD",
    0x09: "MUL",
    0x0A: "SUB",
    0x0B: "DIV",
    0x0C: "NEG",
    0x10: "MAT_INIT_IDENTITY",
    0x11: "MAT_SET",
    0x12: "MAT_GET",
    0x13: "MAT_MUL",
    0x14: "MAT_TRANS",
    0x15: "MAT_CMP",
    0x20: "JMP",
    0x21: "JNE",
    0x22: "JEQ",
    0x30: "READ_FLAG",
    0x31: "PUSH_FLAG_CHAR",
    0x32: "FLAG_LEN",
    0x40: "CMP",
    0x41: "EQ",
    0x42: "LT",
    0x43: "GT",
    0xFF: "EXIT",
}

MATRIX_NAMES = {
    0: "L",
    1: "D",
    2: "A_COMPUTED",
    3: "A_EXPECTED",
    4: "TEMP1",
    5: "TEMP2",
}

def disassemble(bytecode):
    """Disassemble bytecode to human-readable form"""
    pc = 0
    instructions = []
    
    while pc < len(bytecode):
        offset = pc
        op = bytecode[pc]
        pc += 1
        
        opname = OPCODES.get(op, f"UNKNOWN_{op:02X}")
        args = []
        
        # Parse arguments based on opcode
        if op == 0x01:  # PUSH_IMM
            if pc + 8 <= len(bytecode):
                val = struct.unpack('<d', bytes(bytecode[pc:pc+8]))[0]
                args = [f"{val}"]
                pc += 8
        
        elif op in [0x04, 0x05, 0x30]:  # LOAD_REG, STORE_REG, READ_FLAG
            if pc < len(bytecode):
                reg = bytecode[pc]
                args = [f"r{reg}"]
                pc += 1
        
        elif op == 0x10:  # MAT_INIT_IDENTITY
            if pc + 2 <= len(bytecode):
                mat_id = bytecode[pc]
                n = bytecode[pc + 1]
                args = [MATRIX_NAMES.get(mat_id, f"mat{mat_id}"), str(n)]
                pc += 2
        
        elif op == 0x11:  # MAT_SET
            if pc + 3 <= len(bytecode):
                mat_id = bytecode[pc]
                i = bytecode[pc + 1]
                j = bytecode[pc + 2]
                args = [MATRIX_NAMES.get(mat_id, f"mat{mat_id}"), f"[{i}][{j}]"]
                pc += 3
        
        elif op == 0x12:  # MAT_GET
            if pc + 3 <= len(bytecode):
                mat_id = bytecode[pc]
                i = bytecode[pc + 1]
                j = bytecode[pc + 2]
                args = [MATRIX_NAMES.get(mat_id, f"mat{mat_id}"), f"[{i}][{j}]"]
                pc += 3
        
        elif op in [0x13, 0x14]:  # MAT_MUL, MAT_TRANS
            if op == 0x13 and pc + 3 <= len(bytecode):
                dest, src1, src2 = bytecode[pc:pc+3]
                args = [MATRIX_NAMES.get(dest, f"mat{dest}"),
                       MATRIX_NAMES.get(src1, f"mat{src1}"),
                       MATRIX_NAMES.get(src2, f"mat{src2}")]
                pc += 3
            elif op == 0x14 and pc + 2 <= len(bytecode):
                dest, src = bytecode[pc:pc+2]
                args = [MATRIX_NAMES.get(dest, f"mat{dest}"),
                       MATRIX_NAMES.get(src, f"mat{src}")]
                pc += 2
        
        elif op == 0x15:  # MAT_CMP
            if pc + 2 <= len(bytecode):
                mat1, mat2 = bytecode[pc:pc+2]
                args = [MATRIX_NAMES.get(mat1, f"mat{mat1}"),
                       MATRIX_NAMES.get(mat2, f"mat{mat2}")]
                pc += 2
        
        elif op in [0x20, 0x21, 0x22]:  # JMP, JNE, JEQ
            if pc + 4 <= len(bytecode):
                target = struct.unpack('<I', bytes(bytecode[pc:pc+4]))[0]
                args = [f"0x{target:04X}"]
                pc += 4
        
        instr = f"{offset:04X}: {opname:20s}"
        if args:
            instr += " " + ", ".join(args)
        
        instructions.append(instr)
    
    return instructions


def main():
    if len(sys.argv) < 2:
        print("Usage: bytecode_disasm.py <bytecode_file>", file=sys.stderr)
        sys.exit(1)
    
    with open(sys.argv[1], 'rb') as f:
        bytecode = f.read()
    
    print(f"Disassembling {sys.argv[1]} ({len(bytecode)} bytes):\n")
    
    instructions = disassemble(bytecode)
    for instr in instructions:
        print(instr)
    
    print(f"\n{len(instructions)} instructions total")


if __name__ == '__main__':
    main()
