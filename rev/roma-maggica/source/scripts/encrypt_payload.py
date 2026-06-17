#!/usr/bin/env python3
"""Encrypt a binary payload with XOR key 0x1337 and write encrypted_payload.bin."""

from __future__ import annotations

import argparse
from pathlib import Path


def xor_with_u16_key(data: bytes, key: int) -> bytes:
    # Apply XOR using the 16-bit key as a repeating little-endian byte stream.
    key_bytes = key.to_bytes(2, "little")
    out = bytearray(len(data))
    for i, b in enumerate(data):
        out[i] = b ^ key_bytes[i % 2]
    return bytes(out)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="XOR-encrypt a DLL payload with 16-bit key (default: 0x1337)."
    )
    parser.add_argument("--input", default="payload.dll", help="Input payload path")
    parser.add_argument(
        "--output", default="encrypted_payload.bin", help="Encrypted output path"
    )
    parser.add_argument(
        "--key",
        default="0x1337",
        help="16-bit XOR key (hex like 0x1337 or decimal)",
    )
    args = parser.parse_args()

    key = int(args.key, 0) & 0xFFFF
    src = Path(args.input)
    dst = Path(args.output)

    if not src.exists():
        raise FileNotFoundError(f"Input file not found: {src}")

    plain = src.read_bytes()
    encrypted = xor_with_u16_key(plain, key)
    dst.write_bytes(encrypted)

    print(f"Input: {src} ({len(plain)} bytes)")
    print(f"Output: {dst} ({len(encrypted)} bytes)")
    print(f"XOR key: 0x{key:04X} (pattern: {key.to_bytes(2, 'little').hex()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
