import secrets
from trx import p, flag

poly = [secrets.randbelow(p) for _ in range(32)]

print(f"{p = }")

for i in range(16):
    x = int(input("> ")) % p
    
    if x == 0:
        break
    
    print(sum([c * pow(x, i, p) for i, c in enumerate(poly)]) % p)

x = int(input("> ")) % p

if x == poly[0]:
    print(flag)
else:
    print("nope")