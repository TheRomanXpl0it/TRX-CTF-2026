import sys


opcodes = {
    "NOP":       0x01,
    "PUSH":      0x02,
    "POP":       0x03,
    "PEEK":      0x1C,  
    "ADD":       0x05,
    "SUB":       0x06,
    "MUL":       0x07,
    "DIV":       0x08,
    "PRINT":     0x09,
    "LOAD_MEM":  0x1D,
    "STORE_MEM": 0x0B,
    "JUMP":      0x0C,
    "JZ":        0x0D,
    "JNZ":       0x1E,
    "CALL":      0x0F,
    "RET":       0x22,
    "EQ":        0x11,
    "LT":        0x26,
    "GT":        0x13,
    "NEG":       0x27,
    "XOR":       0x28,
    "ROL":       0x16,
    "ROR":       0x17,
    "HALT":      0x18,
    "READ_INT":  0x19,
    "LOAD_IND":  0x1A,
    "STORE_IND": 0x1B,
    "PRINT_OK":  0x29,
    "RAND":      0x2A,
    "PRINT_ERR": 0x21,
    "EXIT":      0xFF
}

opcode_encode_table = [
    0x00000000, 0x51CDAC75, 0x1B021086, 0x5EFB2A93,
    0x00000000, 0x290AF19A, 0x00000001, 0x7D44CDE7,
    0x51BDAB5B, 0x970547BF, 0x00000000, 0x22404922,
    0x00000002, 0xDAC30B37, 0x00000000, 0x86132F14,
    0x00000000, 0xBB676DB7, 0x00000000, 0x0B44322F,
    0x00000000, 0x00000000, 0x00000005, 0x79000DBC,
    0x00000004, 0xB0EADEB3, 0x5AA618E6, 0xC47F392A,
    0x9B9F1876, 0x6C9FABB5, 0x0A4D8AF2, 0x00000000,
    0x00000000, 0xAB0166B1, 0x058CEDAD, 0x00000000,
    0x00000000, 0x00000000, 0x136731A2, 0xC7A2F52D,
    0x79B04CCE, 0xB133C9E4, 0x0D2112B8, 0xDF2111FD,
    0x0000000A, 0x00000000, 0x00000000, 0xAC6AECBD,
    0x00000008, 0x80800078, 0xC721EC57, 0x0AA7C094,
    0x730A2E3B, 0x7A8C2DEA, 0x00000007, 0x00000000,
    0x9752A7DB, 0x00000000, 0x00000000, 0x42F8D3CB,
    0x97845C9D, 0x46CDDFD6, 0xA4494A4C, 0x00000000,
    0x4286ADB7, 0x636109A7, 0xBE339B57, 0x8D4886A2,
    0x449CBD10, 0x42AAAFDD, 0x00000000, 0x63FA0439,
    0x6DCB4782, 0xB7AF19A2, 0x00000000, 0x34A3B835,
    0x241E638A, 0xDBDAE616, 0x29EC6314, 0x0B23A7DE,
    0x3E1B028E, 0x3E9C8FB3, 0xB5A26448, 0x00000000,
    0x97F410B0, 0x00000000, 0x00000015, 0x5B6CFF9E,
    0x00000014, 0x00000000, 0x8C7EB51A, 0x3EAE4EC5,
    0x68C77549, 0x6AEAE563, 0x00000000, 0x63AFC509,
    0x00000010, 0x00000000, 0xB95FC859, 0x0F40765A,
    0x02867888, 0x00000000, 0x0000000D, 0xD483588A,
    0x00000000, 0x00000000, 0x9E58666B, 0x00000000,
    0x0000000E, 0x382678CD, 0x00000000, 0x80BE4E2A,
    0xCB7E4D9B, 0xE8256602, 0x40F9C770, 0x62591360,
    0x8A20AC47, 0x262CA366, 0x00000000, 0x05C14550,
    0x362BF411, 0x00000000, 0xA9DBDBA2, 0x01460CB3,
    0x00000000, 0x19D8A3EB, 0x61C53874, 0xDFA12FC3,
    0x00000000, 0x00000000, 0x0B05DC5E, 0x00000000,
    0x8C1D20F5, 0x0E773796, 0x00000000, 0x00000000,
    0x7F0080FD, 0x18809124, 0x64560BE4, 0x5838021A,
    0x038A37A3, 0x00000000, 0x00000000, 0x2445B462,
    0x8A25700E, 0x3189F588, 0x00000000, 0x214E8F5B,
    0xA7B0D1FA, 0xAAADF3F6, 0x6069849E, 0xC2623313,
    0x59D92FA4, 0xB622A915, 0x00000000, 0x76407CAA,
    0x8743A42E, 0xB4ED0846, 0x00000000, 0x00000000,
    0x77774059, 0x00000000, 0xE073A2FB, 0x00000000,
    0x5D3E86AD, 0x36E05117, 0x4E0A40C7, 0x43BABB2D,
    0xE3D15A69, 0x00000000, 0x00000000, 0xDD6BF5D0,
    0x0000002A, 0xA7592CED, 0x217DC195, 0x00000000,
    0x00000028, 0x717EBD27, 0x8141298E, 0x81C6212A,
    0x7CBE1799, 0x4E1AA7C1, 0x00000027, 0x00000000,
    0x00000000, 0x00000000, 0xA8E02CB0, 0x830080F5,
    0x099DE87F, 0x00000000, 0x27415136, 0x00000000,
    0x00000020, 0x633CFD0E, 0x0EC0EB67, 0x00000000,
    0x00000000, 0xBBD8D729, 0x0000001D, 0xCE1D98A4,
    0x0695E63E, 0x5D77B1D2, 0x63E0D391, 0x03E1F935,
    0x0000001A, 0x00000000, 0x00000000, 0x21EBE89B,
    0xBCE72F44, 0x66D17EF6, 0x00000000, 0x00000000,
    0x00000000, 0x85A39B6E, 0x0000001B, 0x6838E195,
    0x0000001C, 0x04B4DD28, 0x305C4D7D, 0x9E8A67B9,
    0xDE0AC03C, 0x00000000, 0x00000000, 0x00000000,
    0x00000000, 0x00000000, 0x0772BC42, 0xA2C4A16A,
    0x59076879, 0x00000000, 0x00000000, 0x00000000,
    0x4C86405C, 0x00000000, 0x00000000, 0x00000000,
    0x2EB0CDA1, 0xB42E4B34, 0xC019AA25, 0x00000000,
    0xF924D0E8, 0x00000000, 0xD61E9255, 0x20924244,
    0xE0E92639, 0x00000000, 0x00000000, 0x00000000,
    0x7A2EDBF9, 0x03D38A9D, 0x00000000, 0x00000000,
    0x3CD34F9B, 0x52C61A37, 0x3522D812, 0x3AE8298D
]

labels = {}

def invert_kinda_random_stuff1(y):
    return opcode_encode_table[y]

def kinda_random_stuff2(value):
    x = value
    x ^= x << 7
    x ^= x >> 3
    x ^= x << 5
    x ^= x >> 2
    x ^= 0xA5C3F1E9
    return x

def ignore_comments(line):
    if ';' in line:
        line = line.split(';', 1)[0]
    return line.strip()

def check_label(line):
    if line.endswith(':'):
        label = line[:-1].strip()
        return label
    return None

def calculate_labels():
    address = 0
    for line in lines:
        line = ignore_comments(line).strip()
        if not line:
            continue
        label = check_label(line)
        if label:
            labels[label] = address
            continue
        address += 1


if len(sys.argv) != 2:
    print(f"Usage: assembler.py <assembly_file>")
    exit(1)

with open(sys.argv[1], "r") as f:
    lines = f.readlines()

final_instructions = []
calculate_labels()

for line in lines:
    line = ignore_comments(line).strip()
    if not line:
        continue
    label = check_label(line)
    if label:
        continue
    
    parts = line.split()
    instr = parts[0].upper()
    
    if instr not in opcodes:
        print(f"Unknown instruction: {instr}")
        exit(1)
    
    opcode = opcodes[instr]
    encoded_opcode = invert_kinda_random_stuff1(opcode)


    operand = parts[1] if len(parts) > 1 else None
    try:
        operand = kinda_random_stuff2(int(operand)) if operand else 0
    except Exception:
        if operand in labels:
            operand = kinda_random_stuff2(labels[operand])
        else:
            print(f"Unknown operand or label: {operand}")
            exit(1)

    full_instruction = (encoded_opcode << 32) | (operand & 0xFFFFFFFF)

    final_instructions.append(full_instruction)

with open("output.bin", "wb") as f:
    for instr in final_instructions:
        op = (instr >> 32) & 0xFFFFFFFF
        arg = instr & 0xFFFFFFFF
        f.write(op.to_bytes(4, byteorder='little'))
        f.write(arg.to_bytes(4, byteorder='little'))
    print("Assembled successfully into output.bin")


    


    

