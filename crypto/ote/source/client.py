from pwn import process, remote, context
from channel import PwnToolsChannel
import re, secrets, ote

context.log_level = 'info'
io = process(["python3", "server.py"])

line = io.recvline().strip()
n, m, ell = map(int, re.findall(rb"Generated (\d+) shares for (\d+) blocks of size (\d+) bits each\.", line)[0])
choices = [secrets.randbelow(n) for _ in range(m)]

channel = PwnToolsChannel(io)
param = ote.OTEParam(n=n, m=m, ell=ell)
received = ote.receive(param, channel, choices)

io.close()
