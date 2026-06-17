from pwn import *
import sys
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

url = sys.argv[1].split(":")
io = remote(url[0], url[1])

def send_point(io, p):
    io.sendlineafter(b"x: ", str(p[0]).encode())
    io.sendlineafter(b"y: ", str(p[1]).encode())
    io.sendlineafter(b"z: ", str(p[2]).encode())

def rot(io, p):
    io.sendlineafter(b"> ", b"1")
    send_point(io, p)
    s = io.recvline().decode()

    s = s[1:-2]
    coords = s.split(',')
    coords = [SR(x) for x in coords]

    return vector(coords)

p1 = vector([0, 1, 0])
p2 = rot(io, p1)
p3 = rot(io, p2)

v1 = p2 - p1
v2 = p3 - p1
n = v1.cross_product(v2)
u = n / n.norm()


io.sendlineafter(b"> ", b"2")
send_point(io, u)
ct = bytes.fromhex(io.recvline().decode())

data = '0,0,0'
h = hashlib.sha256(data.encode()).digest()
aes = AES.new(h, AES.MODE_ECB)
pt = unpad(aes.decrypt(ct), AES.block_size)
print(pt)

io.close()

