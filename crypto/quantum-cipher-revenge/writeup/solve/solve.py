from Crypto.Util.number import bytes_to_long, long_to_bytes
from pwn import *
import sys

url = sys.argv[1].split(":")

io = remote(url[0], int(url[1]))
context.log_level = "error"

io.recvuntil(b"Flag = ")
encrypted_flag = io.recvline().strip().decode()

encrypted_flag = bin(bytes_to_long(bytes.fromhex(encrypted_flag)))[2:]
while len(encrypted_flag) % 24 != 0:
    encrypted_flag = '0' + encrypted_flag

io.recvuntil(b"Permutation = ")
Permutation = io.recvline().strip().decode()[1:-1]
Permutation = [int(x) for x in Permutation.split() if x]

blocks = [encrypted_flag[i:i+24][::-1] for i in range(0, len(encrypted_flag), 24)]

for _ in range(31):
    decrypted_blocks = []
    for block in blocks:
        decrypted_block = ['0']*24
        for i in range(24):
            decrypted_block[Permutation[i]] = block[i]
        decrypted_blocks.append(''.join(decrypted_block))

    blocks = decrypted_blocks.copy()

flag = ''.join(x[::-1] for x in blocks)
print(long_to_bytes(int(flag, 2)).decode())

