CFLAGS = -O1 -static -no-pie -g
CC = musl-gcc

e: e.c
	$(CC) e.c helpers.c -o exploit $(CFLAGS)
	base64 exploit > exploit.b64