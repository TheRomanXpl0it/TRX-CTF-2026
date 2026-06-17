#!/bin/sh

qemu-system-x86_64 \
	-kernel ./bzImage \
	-cpu qemu64,+smap,+smep,+fsgsbase \
	-smp 1 \
	-m 256M \
	-initrd ./initramfs.cpio.gz \
	-append "console=ttyS0 quiet loglevel=3 panic=-1 pti=on" \
	-drive format=raw,file=flag.txt,if=ide \
	-no-reboot \
	-nographic \
	-monitor /dev/null
