import numpy as np
from pwn import *
from string import printable
import sys

FLAG_LEN = 38
flag = ['?']*FLAG_LEN

url = sys.argv[1].split(":")

for c in printable:
    r = remote(url[0], int(url[1]))
    r.recvuntil(b'> ')
    r.sendline(b'1')
    r.recvuntil(b'byte) ')
    r.sendline(c.encode().hex().encode())
    output = r.recvline().decode().strip()
    byte_state = eval(output)
    r.recvuntil(b'> ')
    r.sendline(b'2')
    output = r.recvline().decode().strip()
    flag_state = eval(output)
    blocks = [flag_state[i:i+256] for i in range(0, len(flag_state), 256)]
    for i, block in enumerate(blocks):
        coeff = np.vdot(byte_state, block)
        if np.real(coeff) > 0.98:
            flag[i] = c
    r.close()
print("".join(flag))
