#!/bin/sh

TIMEOUT=180

timeout $TIMEOUT qemu-system-x86_64 \
	-kernel ./bzImage \
	-cpu qemu64,+smap,+smep \
	-smp 1 \
	-m 1G \
	-initrd ./initramfs.cpio.gz \
	-append "console=ttyS0 quiet loglevel=3 oops=panic panic_on_warn=1 panic=-1 nokaslr page_alloc.shuffle=1" \
	-no-reboot \
	-nographic \
	-monitor /dev/null
