CFLAGS=-fstack-protector-strong -fno-reorder-blocks-and-partition -fno-inline -fno-gcse -O2 -mpopcnt -D_FORTIFY_SOURCE=0
LDFLAGS=-Wl,-z,relro,-z,now

build:
	docker build -f Dockerfile.build -t mask_builder .
	docker run -it -u 1000 -v "$(PWD):/build" mask_builder sh -c 'make clean && make mask'
.PHONY: build

mask: mask.o

default: build

clean:
	rm -f mask mask.o
.PHONY: clean