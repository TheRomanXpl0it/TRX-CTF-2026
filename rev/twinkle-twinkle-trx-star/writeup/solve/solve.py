#!/usr/bin/env python3
import subprocess
import sys

from Crypto.Cipher import AES


ADDRESS = "0x585173"
BITRATE = 128000
SAMPLE_RATE = 44100
IV = b"\x67" * 16


def get_reservoir_values(mp3_path):
    data = Path(mp3_path).read_bytes()
    values = []
    pos = 0

    while pos + 6 <= len(data):
        if data[pos] != 0xFF or (data[pos + 1] & 0xE0) != 0xE0:
            pos += 1
            continue

        padding = (data[pos + 2] >> 1) & 1
        main_data_begin = (data[pos + 4] << 1) | (data[pos + 5] >> 7)
        values.append(main_data_begin)

        pos += 144 * BITRATE // SAMPLE_RATE + padding

    return values


def extract_ciphertext(values):
    values = list(values)
    while values and values[-1] == 0:
        values.pop()

    ciphertext = bytearray()
    previous = 0
    after_flush = False

    for value in values:
        if value == 0:
            if after_flush:
                ciphertext.append(0)
                after_flush = False
            else:
                after_flush = True
            previous = 0
            continue

        if after_flush:
            ciphertext.append(value)
        else:
            ciphertext.append(value - previous)

        previous = value
        after_flush = False

    return bytes(ciphertext)


def run_until_key(binary):
    gdb_script = f'''
gdb -q -nx {binary} -batch -ex "set pagination off" -ex "break *{ADDRESS}" -ex "run A" -ex 'x/16bx $rax'
'''

    run = subprocess.run(gdb_script, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    parts = []
    for line in run.stdout.splitlines():
        if ":" not in line:
            continue
        _, values = line.split(":", 1)
        for part in values.split():
            if part.startswith("0x"):
                parts.append(int(part, 16))
        if len(parts) >= 16:
            return bytes(parts[:16])

    raise Exception(":(")


def collect_all_keys(binary):
    seen = set()
    while len(seen) < 1024:
        key = run_until_key(binary)
        if key in seen:
            continue
        seen.add(key)
        print(f"{len(seen)}/1024")
        aes = AES.new(key, AES.MODE_CTR, nonce=b"", initial_value=IV)
        text = aes.decrypt(ciphertext).decode(errors="ignore")

        if "TRX" in text:
            print(text)
            sys.exit(0)


mp3_path = sys.argv[1] if len(sys.argv) > 1 else "song.mp3"
binary = "encoder"

reservoir_values = get_reservoir_values(mp3_path)
ciphertext = extract_ciphertext(reservoir_values)
collect_all_keys(binary)
