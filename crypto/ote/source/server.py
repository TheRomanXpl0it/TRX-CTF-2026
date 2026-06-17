from channel import StdIOChannel, Curve
import os, secrets, ote

n = 16
m = 256
ell = Curve.p.bit_length()

flag = os.getenv("FLAG", "TRX{this_is_a_fake_flag}").encode()
assert len(flag) <= m
flag += b"\x00" * secrets.randbelow(m - len(flag) + 1)
flag = b"\x00" * (m - len(flag)) + flag
assert len(flag) == m

shares = [[secrets.randbelow(Curve.p) for _ in range(n - 1)] for _ in range(m)]
for i in range(m):
    shares[i].append((flag[i] - sum(shares[i])) % Curve.p)
    assert sum(shares[i]) % Curve.p == flag[i]

print(f"Generated {n} shares for {m} blocks of size {ell} bits each.")
param = ote.OTEParam(n=n, m=m, ell=ell)
channel = StdIOChannel()
while True:
    try:
        ote.send(param, channel, shares)
        break
    except ote.OTEAbort:
        print("Protocol aborted due to a check failure. Restarting...")
        if input("Do you want to try again? (y/n): ").strip().lower() != 'y':
            print("Exiting.")
            break
