#!/usr/bin/env python3
from pwn import args, remote, context
import random

context.log_level = "critical"


HOST = 127.0.0.1
PORT = 1337
N = 256


def solve_nq(n, fixed):
    fixed = dict(fixed)
    free_rows = [r for r in range(n) if r not in fixed]
    free_cols = [c for c in range(n) if c not in fixed.values()]
    random.shuffle(free_cols)

    col = [0] * n
    for r, c in fixed.items():
        col[r] = c
    for r, c in zip(free_rows, free_cols):
        col[r] = c

    size = 2 * n - 1
    d1 = [0] * size
    d2 = [0] * size
    for r in range(n):
        c = col[r]
        d1[r - c + (n - 1)] += 1
        d2[r + c] += 1

    def conflicts(r):
        c = col[r]
        return (d1[r - c + (n - 1)] - 1) + (d2[r + c] - 1)

    for _ in range(200000):
        bad = [r for r in free_rows if conflicts(r) > 0]
        if not bad:
            return col

        r1 = random.choice(bad)
        c1 = col[r1]
        d1[r1 - c1 + (n - 1)] -= 1
        d2[r1 + c1] -= 1

        best = None
        best_r2 = None
        for r2 in free_rows:
            if r2 == r1:
                continue
            c2 = col[r2]
            d1[r2 - c2 + (n - 1)] -= 1
            d2[r2 + c2] -= 1

            conf = d1[r1 - c2 + (n - 1)] + d2[r1 + c2]
            conf += d1[r2 - c1 + (n - 1)] + d2[r2 + c1]

            d1[r2 - c2 + (n - 1)] += 1
            d2[r2 + c2] += 1

            if best is None or conf < best:
                best = conf
                best_r2 = r2

        d1[r1 - c1 + (n - 1)] += 1
        d2[r1 + c1] += 1

        if best_r2 is None:
            continue

        r2 = best_r2
        c2 = col[r2]

        d1[r1 - c1 + (n - 1)] -= 1
        d2[r1 + c1] -= 1
        d1[r2 - c2 + (n - 1)] -= 1
        d2[r2 + c2] -= 1

        col[r1], col[r2] = c2, c1

        d1[r1 - col[r1] + (n - 1)] += 1
        d2[r1 + col[r1]] += 1
        d1[r2 - col[r2] + (n - 1)] += 1
        d2[r2 + col[r2]] += 1

    raise RuntimeError("solver failed")


cache = {}


def build_payload():
    fixed = [(127, 129), (23, 45)]
    key = tuple(fixed)
    if key in cache:
        return cache[key]
    while True:
        try:
            sol = solve_nq(N, fixed)
            break
        except RuntimeError:
            continue
    fixed_rows = {r for r, _ in fixed}
    payload = [f"{sol[r]},{r}".encode() for r in range(N) if r not in fixed_rows]
    cache[key] = payload
    return payload


def one_attempt(payload):
    io = remote(HOST, PORT)
    for line in payload:
        io.sendline(line)
    data = io.recvrepeat(1.2)
    io.close()
    return data


def main():
    payload = build_payload()
    while True:
        out = one_attempt(payload)
        response = out.decode(errors="ignore")
        if "TRX" in response:
            print(response)
            return


if __name__ == "__main__":
    main()
