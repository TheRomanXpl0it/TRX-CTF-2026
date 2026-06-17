BITS 64
org 0x400000

ehdr:                           ; ELF header
	db 0x7F, "ELF"              ; magic
	db 2                        ; 64-bit
	db 1                        ; little endian
	db 1                        ; ELF version
	db 0                        ; ABI
	times 8 db 0

	dw 2                        ; executable
	dw 0x3E                     ; x86-64
	dd 1                        ; version

	dq _start                   ; entry point
	dq phdr - $$                ; program header offset
	dq 0                        ; section header offset

	dd 0                        ; flags
	dw ehdrsize                 ; ELF header size
	dw phdrsize                 ; program header size
	dw 1                        ; number of program headers
	dw 0                        ; section header size
	dw 0                        ; number of section headers
	dw 0                        ; string table index

ehdrsize equ $ - ehdr

phdr:                           ; program header
	dd 1                        ; PT_LOAD
	dd 5                        ; flags (R+X)
	dq 0                        ; file offset
	dq $$                       ; virtual address
	dq $$                       ; physical address
	dq filesize                 ; file size
	dq filesize                 ; memory size
	dq 0x1000                   ; alignment

phdrsize equ $ - phdr


_start:
; argc < 2, fatal error
	mov rdi, [rsp] ; argc
	cmp rdi, 2
	jl fatal_exit

; open argv[1] file read only
	mov rdi, [rsp + 0x10] ; argv[1]
	mov rax, 2 ; sys_open
	xor rsi, rsi ; O_RDONLY
	xor rdx, rdx
	syscall
	test rax, rax
	js fatal_exit
	mov r12, rax ; file descriptor

; fstat the file to get its size
	sub rsp, 0x90 ; struct stat
	mov rdi, r12
	mov rsi, rsp
	mov rax, 5 ; sys_fstat
	syscall
	mov r13, [rsp + 0x30] ; st_size
	add rsp, 0x90

; read the file into buffer
	; lea r14, [prog]
	sub rsp, r13 ; allocate buffer on stack
	lea r14, [rsp]
	xor r15, r15
read_loop:
	cmp r15, r13
	jge read_done

	xor rax, rax
	mov rdi, r12
	lea rsi, [r14 + r15]
	mov rdx, r13
	sub rdx, r15
	syscall
	test rax, rax
	jle read_done
	add r15, rax

	jmp read_loop

read_done:
	mov rax, 3 ; sys_close
	mov rdi, r12
	syscall


; execute the program
	shr r13, 3 ; get num of elements (8 bytes each)
	xor r15, r15 ; pc
vm:
	test r15, r15
	js success_exit
	cmp r15, r13
	jge success_exit

	; a, b, c = prog[pc], prog[pc+1], prog[pc+2]
	mov rax, [r14 + r15 * 8] ; a
	mov rbx, [r14 + r15 * 8 + 8] ; b
	mov rcx, [r14 + r15 * 8 + 16] ; c

	cmp rax, -1
	je input
	cmp rax, -2
	je output

	; prog[b] += prog[a]
	mov rdx, [r14 + rax * 8]
	add [r14 + rbx * 8], rdx
	cmp qword [r14 + rbx * 8], 0
	jg no_branch
	jmp branch

input:
	sub rsp, 8

	xor rax, rax ; sys_read
	xor rdi, rdi ; stdin
	mov rsi, rsp ; buffer
	mov rdx, 1 ; count
	push rcx
	syscall
	pop rcx

	movzx rax, byte [rsp]
	mov [r14 + rbx * 8], rax

	add rsp, 8
	jmp branch

output:
	push rcx
	mov rdi, [r14 + rbx * 8]
	call put_num
	push 0x20 ; " "
	mov rax, 1 ; sys_write
	mov rdi, 1 ; stdout
	mov rsi, rsp ; buffer
	mov rdx, 1 ; count
	syscall
	pop rax
	pop rcx

branch:
	; pc = c
	mov r15, rcx
	jmp vm

no_branch:
	; pc += 3
	add r15, 3
	jmp vm



success_exit:
	mov rdi, 0 ; exit code 0
	jmp exit
fatal_exit:
	mov rdi, 1 ; exit code 1
exit:
	mov rax, 0x3c ; sys_exit
	syscall



hexstr:
	db "0123456789abcdef"

put_num:
	cmp rdi, 0xf ; rdi <= 15: write
	jbe write_hex_nibble

	push rdi
	shr rdi, 4 ; rdi / 16
	call put_num
	pop rdi

write_hex_nibble:
	and rdi, 0xf
	lea rsi, byte [hexstr + rdi] ; get hex char

	mov rax, 1 ; sys_write
	mov rdi, 1 ; stdout
	mov rdx, 1 ; count
	syscall

	ret



filesize equ $ - $$
