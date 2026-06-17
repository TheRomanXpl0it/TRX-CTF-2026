#!/usr/bin/env python3
import itertools
import math
import re
import sys
from collections import Counter, defaultdict

from pwn import context, remote


KNOWN_PREFIX = b"TRX{"
KNOWN_SUFFIX = b"}"
CHARSET = bytes(sorted(set(b"TRX{}_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")))
TIMEOUT = 20.0
MAX_SESSIONS = 40
STOP_AFTER = 3

# 24-query signature code with minimum pairwise distance 10 modulo complement.
QUERY_BYTES = [
    0x2A, 0xA9, 0x04, 0x7D, 0x91, 0xA7, 0x73, 0x87,
    0x18, 0xFD, 0x32, 0x49, 0xDA, 0x4E, 0xAC, 0xDE,
    0x34, 0xE2, 0x77, 0xE0, 0x9B, 0x0F, 0xD4, 0x41,
]


def byte_bits(value):
    return [(value >> (7 - i)) & 1 for i in range(8)]


QUERY_COLS = [
    [byte_bits(q)[bit_index] for q in QUERY_BYTES]
    for bit_index in range(8)
]

PREFIX_BITS = [byte_bits(ch) for ch in KNOWN_PREFIX]
SUFFIX_BITS = byte_bits(KNOWN_SUFFIX[0])


def encrypt_byte(tube, value):
    tube.recvuntil(b"> ")
    tube.sendline(b"1")
    tube.recvuntil(b"(one hex byte) ")
    tube.sendline(f"{value:02x}".encode())
    return bytes.fromhex(tube.recvline().strip().decode())


def encrypt_flag(tube):
    tube.recvuntil(b"> ")
    tube.sendline(b"2")
    return bytes.fromhex(tube.recvline().strip().decode())


def hamming(a, b):
    return sum(x != y for x, y in zip(a, b))


def build_score_matrix(signature_cts, flag_ct):
    observed = [
        # Single-byte inputs with the MSB set produce two blocks because of the
        # challenge's broken bit padding; the queried byte is always the last one.
        [byte_bits(ct[-1])[out_bit] for ct in signature_cts]
        for out_bit in range(8)
    ]
    prefix_obs = [byte_bits(ch) for ch in flag_ct[: len(KNOWN_PREFIX)]]
    suffix_obs = byte_bits(flag_ct[-1])

    score = [[float("-inf")] * 8 for _ in range(8)]
    inv = [[0] * 8 for _ in range(8)]
    eps = [[0.0] * 8 for _ in range(8)]

    n = len(signature_cts)
    for out_bit in range(8):
        series = observed[out_bit]
        for in_bit in range(8):
            for candidate_inv in (0, 1):
                template = [b ^ candidate_inv for b in QUERY_COLS[in_bit]]
                mismatches = hamming(series, template)
                error = (mismatches + 0.5) / (n + 1.0)
                ll = (n - mismatches) * math.log(1.0 - error) + mismatches * math.log(error)

                for idx, known in enumerate(PREFIX_BITS):
                    predicted = known[in_bit] ^ candidate_inv
                    ll += math.log((1.0 - error) if prefix_obs[idx][out_bit] == predicted else error)

                predicted = SUFFIX_BITS[in_bit] ^ candidate_inv
                ll += math.log((1.0 - error) if suffix_obs[out_bit] == predicted else error)

                if ll > score[out_bit][in_bit]:
                    score[out_bit][in_bit] = ll
                    inv[out_bit][in_bit] = candidate_inv
                    eps[out_bit][in_bit] = error

    return score, inv, eps


def recover_mapping(score):
    best_perm = None
    best_score = float("-inf")
    for perm in itertools.permutations(range(8)):
        current = sum(score[out_bit][perm[out_bit]] for out_bit in range(8))
        if current > best_score:
            best_score = current
            best_perm = perm
    return best_perm, best_score


def decode_session(signature_cts, flag_ct):
    score, inv_table, eps_table = build_score_matrix(signature_cts, flag_ct)
    perm, _ = recover_mapping(score)

    inv = [inv_table[out_bit][perm[out_bit]] for out_bit in range(8)]
    eps = [eps_table[out_bit][perm[out_bit]] for out_bit in range(8)]

    decoded = bytearray()
    total_margin = 0.0

    for idx, ciphertext_byte in enumerate(flag_ct):
        if idx < len(KNOWN_PREFIX):
            decoded.append(KNOWN_PREFIX[idx])
            continue
        if idx == len(flag_ct) - 1:
            decoded.append(KNOWN_SUFFIX[0])
            continue

        y = byte_bits(ciphertext_byte)
        scored = []
        for candidate in CHARSET:
            x = byte_bits(candidate)
            ll = 0.0
            for out_bit in range(8):
                predicted = x[perm[out_bit]] ^ inv[out_bit]
                ll += math.log((1.0 - eps[out_bit]) if y[out_bit] == predicted else eps[out_bit])
            scored.append((ll, candidate))

        scored.sort(reverse=True)
        decoded.append(scored[0][1])
        total_margin += scored[0][0] - scored[1][0]

    confidence = total_margin
    return bytes(decoded), confidence


def solve_one_session(host, port):
    tube = remote(host, port, timeout=TIMEOUT)
    try:
        signature_cts = [encrypt_byte(tube, q) for q in QUERY_BYTES]
        flag_ct = encrypt_flag(tube)
    finally:
        tube.close()
    return decode_session(signature_cts, flag_ct)


def aggregate(candidates):
    weighted = []
    for candidate, confidence in candidates:
        weight = max(confidence, 1.0)
        weighted.append((candidate, weight))

    result = []
    for idx in range(len(weighted[0][0])):
        scores = defaultdict(float)
        for candidate, weight in weighted:
            scores[candidate[idx]] += weight
        result.append(max(scores.items(), key=lambda item: item[1])[0])
    return bytes(result)


def main():
    context.log_level = "error"

    host, port = sys.argv[1].split(":")
    port = int(port)

    full_candidate_counts = Counter()
    collected = []

    for session_idx in range(1, MAX_SESSIONS + 1):
        candidate, confidence = solve_one_session(host, port)
        collected.append((candidate, confidence))
        full_candidate_counts[candidate] += 1

        best = aggregate(collected)
        print(f"[{session_idx:02d}] conf={confidence:.2f} candidate={candidate.decode(errors='replace')}")
        print(f"[{session_idx:02d}] aggregate={best.decode(errors='replace')}")

        if full_candidate_counts[candidate] >= STOP_AFTER:
            print(candidate.decode())
            return

        if re.fullmatch(rb"TRX\{[A-Z0-9_]+\}", best):
            top_count = full_candidate_counts[best]
            if top_count >= STOP_AFTER:
                print(best.decode())
                return

    print(aggregate(collected).decode())


if __name__ == "__main__":
    main()
