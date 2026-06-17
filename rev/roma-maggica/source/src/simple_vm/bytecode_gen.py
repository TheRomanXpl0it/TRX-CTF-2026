#!/usr/bin/env python3
"""
Bytecode generator for the flag verification bytecode
Takes a flag and generates a bytecode binary that verifies it
"""

import struct
import sys

# Bytecode opcodes
OP_PUSH_IMM = 0x01
OP_POP = 0x02
OP_DUP = 0x03
OP_LOAD_REG = 0x04
OP_STORE_REG = 0x05
OP_LOAD_MEM = 0x06
OP_STORE_MEM = 0x07
OP_ADD = 0x08
OP_MUL = 0x09
OP_SUB = 0x0A
OP_DIV = 0x0B
OP_NEG = 0x0C
OP_MAT_INIT_IDENTITY = 0x10
OP_MAT_SET = 0x11
OP_MAT_GET = 0x12
OP_MAT_MUL = 0x13
OP_MAT_TRANS = 0x14
OP_MAT_CMP = 0x15
OP_JMP = 0x20
OP_JNE = 0x21
OP_JEQ = 0x22
OP_READ_FLAG = 0x30
OP_PUSH_FLAG_CHAR = 0x31
OP_FLAG_LEN = 0x32
OP_CMP = 0x40
OP_EQ = 0x41
OP_LT = 0x42
OP_GT = 0x43
OP_NOP = 0x00
OP_EXIT = 0xFF

# Matrix IDs
MAT_L = 0
MAT_D = 1
MAT_A_COMPUTED = 2
MAT_A_EXPECTED = 3

OFFSET = -77
N = 9

class BytecodeGenerator:
    def __init__(self):
        self.bytecode = bytearray()
    
    def emit_byte(self, b):
        """Emit a single byte"""
        self.bytecode.append(b & 0xFF)
    
    def emit_bytes(self, data):
        """Emit multiple bytes"""
        for b in data:
            self.bytecode.append(b & 0xFF)
    
    def emit_double(self, d):
        """Emit a double value (8 bytes, little-endian)"""
        self.emit_bytes(struct.pack('<d', d))
    
    def emit_u32(self, v):
        """Emit a 32-bit unsigned integer (little-endian)"""
        self.emit_bytes(struct.pack('<I', v))
    
    def push_imm(self, value):
        """Push immediate double value"""
        self.emit_byte(OP_PUSH_IMM)
        self.emit_double(value)
    
    def pop(self):
        """Pop from stack"""
        self.emit_byte(OP_POP)
    
    def dup(self):
        """Duplicate top of stack"""
        self.emit_byte(OP_DUP)
    
    def load_reg(self, reg):
        """Load from register"""
        self.emit_byte(OP_LOAD_REG)
        self.emit_byte(reg)
    
    def store_reg(self, reg):
        """Store to register"""
        self.emit_byte(OP_STORE_REG)
        self.emit_byte(reg)
    
    def add(self):
        """Add top two stack values"""
        self.emit_byte(OP_ADD)
    
    def mul(self):
        """Multiply top two stack values"""
        self.emit_byte(OP_MUL)
    
    def sub(self):
        """Subtract (b - a where b is top)"""
        self.emit_byte(OP_SUB)
    
    def div(self):
        """Divide"""
        self.emit_byte(OP_DIV)
    
    def neg(self):
        """Negate"""
        self.emit_byte(OP_NEG)
    
    def mat_init_identity(self, mat_id, n):
        """Initialize NxN identity matrix"""
        self.emit_byte(OP_MAT_INIT_IDENTITY)
        self.emit_byte(mat_id)
        self.emit_byte(n)
    
    def mat_set(self, mat_id, i, j):
        """Set matrix element (pops value from stack)"""
        self.emit_byte(OP_MAT_SET)
        self.emit_byte(mat_id)
        self.emit_byte(i)
        self.emit_byte(j)
    
    def mat_get(self, mat_id, i, j):
        """Get matrix element (pushes to stack)"""
        self.emit_byte(OP_MAT_GET)
        self.emit_byte(mat_id)
        self.emit_byte(i)
        self.emit_byte(j)
    
    def mat_mul(self, dest, src1, src2):
        """Multiply matrices: dest = src1 * src2"""
        self.emit_byte(OP_MAT_MUL)
        self.emit_byte(dest)
        self.emit_byte(src1)
        self.emit_byte(src2)
    
    def mat_trans(self, dest, src):
        """Transpose matrix"""
        self.emit_byte(OP_MAT_TRANS)
        self.emit_byte(dest)
        self.emit_byte(src)
    
    def mat_cmp(self, mat1, mat2):
        """Compare matrices (pushes 1 if equal, 0 if not)"""
        self.emit_byte(OP_MAT_CMP)
        self.emit_byte(mat1)
        self.emit_byte(mat2)
    
    def flag_len(self):
        """Push flag length"""
        self.emit_byte(OP_FLAG_LEN)
    
    def push_flag_char(self):
        """Push flag[index] (index must be on stack)"""
        self.emit_byte(OP_PUSH_FLAG_CHAR)
    
    def eq(self):
        """Check equality"""
        self.emit_byte(OP_EQ)
    
    def exit(self):
        """Exit with code from stack"""
        self.emit_byte(OP_EXIT)
    
    def get_bytecode(self):
        """Get the bytecode as bytes"""
        return bytes(self.bytecode)


def generate_flag_verification_bytecode():
    """
    Generate bytecode that:
    1. Reads flag from input at runtime
    2. Constructs L matrix from flag (dynamically)
    3. Constructs D matrix from last N chars of flag (dynamically)
    4. Computes A = L * D * L^T
    5. Compares with hardcoded A
    6. Exits with 0 if match, 1 if not
    """
    gen = BytecodeGenerator()
    
    # Initialize L and D as identity matrices
    gen.mat_init_identity(MAT_L, N)
    gen.mat_init_identity(MAT_D, N)
    
    # Get flag length
    gen.flag_len()
    gen.store_reg(0)  # r0 = flag_len
    
    # Unroll the L matrix fill loop (r, c iteration)
    # We know each iteration: check if r==c, adjust, get flag[index], add offset, set matrix
    r, c = 0, 0
    index = 0
    
    for _ in range(N * N):  # max iterations
        if r == N:
            break
        
        # Check if we should increment r and reset c
        if r == c:
            c = 0
            r += 1
            if r == N:
                break
        
        # Read flag[index] + OFFSET
        gen.push_imm(float(index))
        gen.push_flag_char()
        gen.push_imm(float(OFFSET))
        gen.add()
        
        # Set L[r][c] = value
        gen.mat_set(MAT_L, r, c)
        
        c += 1
        index += 1
    
    # Fill D matrix with last N characters of flag
    # D[i][i] = flag[flag_len - N + i] + OFFSET
    for i in range(N):
        # Read flag[flag_len - N + i]
        gen.load_reg(0)  # flag_len
        gen.push_imm(float(N))
        gen.sub()
        gen.push_imm(float(i))
        gen.add()
        gen.push_flag_char()
        gen.push_imm(float(OFFSET))
        gen.add()
        
        # Set D[i][i]
        gen.mat_set(MAT_D, i, i)
    
    # Create hardcoded A matrix
    # This matches the expected output from the original C code
    expected_A = [
        [-26., -182., -130., -1196., -962., -130., -598., -468., 676.],
        [-182., -1235., -481., -7397., -4979., -2041., -5161., -2574., 5434.],
        [-130., -481., 4075., 4571., 14345., -12899., -13541., 5490., 11132.],
        [-1196., -7397., 4571., -25577., 4297., -40273., -57397., -6660., 47254.],
        [-962., -4979., 14345., 4297., 52989., -68137., -79919., 18920., 47288.],
        [-130., -2041., -12899., -40273., -68137., 57938., 23237., -45137., 12762.],
        [-598., -5161., -13541., -57397., -79919., 23237., 21983., 42538., -58136.],
        [-468., -2574., 5490., -6660., 18920., -45137., 42538., -21769., -1316.],
        [676., 5434., 11132., 47254., 47288., 12762., -58136., -1316., 3116.]
    ]
    
    # Fill expected A matrix
    gen.mat_init_identity(MAT_A_EXPECTED, N)
    for i in range(N):
        for j in range(N):
            gen.push_imm(expected_A[i][j])
            gen.mat_set(MAT_A_EXPECTED, i, j)
    
    # Compute A = L * D * (L^T)
    gen.mat_mul(4, MAT_L, MAT_D)  # temp1 = L * D
    gen.mat_trans(5, MAT_L)        # temp2 = L^T
    gen.mat_mul(MAT_A_COMPUTED, 4, 5)  # result = temp1 * temp2
    
    # Compare computed A with expected A
    gen.mat_cmp(MAT_A_COMPUTED, MAT_A_EXPECTED)
    
    # Result is on stack (1 = match, 0 = no match)
    # Convert to exit code (0 = success, 1 = failure, so invert it)
    gen.push_imm(1.0)
    gen.sub()  # If top is 1, result is 0; if top is 0, result is 1
    gen.exit()
    
    return gen.get_bytecode()


def main():
    output_file = sys.argv[1] if len(sys.argv) > 1 else "bytecode.bin"
    
    print(f"Generating bytecode for flag verification...")
    bytecode = generate_flag_verification_bytecode()
    
    with open(output_file, 'wb') as f:
        f.write(bytecode)
    
    print(f"Bytecode written to {output_file} ({len(bytecode)} bytes)")


if __name__ == '__main__':
    main()
