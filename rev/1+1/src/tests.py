#!/usr/bin/env python3

from compiler import *


def test_add():
	b = Builder()

	X = 2
	Y = 3
	Z = 9
	W = -7

	x_cell = b.alloc(X)
	y_cell = b.alloc(Y)
	z_cell = b.alloc(Z)
	w_cell = b.alloc(W)

	b.ADD(x_cell, y_cell) # positive + positive = positive

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = X + Y
	result_cell = x_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.ADD(x_cell, w_cell) # positive + negative = negative

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = (X + Y) + W
	result_cell = x_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.ADD(x_cell, ZERO) # negative + 0 = negative

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = (X + Y) + W
	result_cell = x_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.ADD(x_cell, z_cell) # negative + positive = positive

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = (X + Y + W) + Z
	result_cell = x_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	print("✔️  ADD")
	return mem




def test_zero():
	b = Builder()

	X = 2
	Y = 0
	Z = -7

	x_cell = b.alloc(X)
	y_cell = b.alloc(Y)
	z_cell = b.alloc(Z)

	b.ZERO(x_cell) # positive

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	result_cell = x_cell
	expected = 0
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.ZERO(y_cell) # zero

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	result_cell = y_cell
	expected = 0
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.ZERO(z_cell) # negative

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	result_cell = z_cell
	expected = 0
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	print("✔️  ZERO")
	return mem




def test_mov():
	b = Builder()

	X = 2
	Y = 0
	Z = -7
	W = 13

	x_cell = b.alloc(X)
	y_cell = b.alloc(Y)
	z_cell = b.alloc(Z)
	w_cell = b.alloc(W)


	b.MOV(x_cell, w_cell) # positive

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	result_cell = x_cell
	expected = W
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.MOV(y_cell, w_cell) # zero

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	result_cell = y_cell
	expected = W
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.MOV(z_cell, w_cell) # negative

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	result_cell = z_cell
	expected = W
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	print("✔️  MOV")
	return mem




def test_jlz():
	b = Builder()

	X = 2
	Y = 0
	Z = -1
	W = (1 << (BITS-1)) - 1 # max positive value
	U = -(1 << (BITS-1))

	x_cell = b.alloc(X)
	y_cell = b.alloc(Y)
	z_cell = b.alloc(Z)
	w_cell = b.alloc(W)
	u_cell = b.alloc(U)

	pre_mem = len(b.mem)

	b.JLZ(x_cell, TBD) # not jump
	after_jmp = b.here()
	b.INC(x_cell)
	b.patch_prev(after_jmp)
	b.INC(x_cell)

	post_mem = len(b.mem)
	assert pre_mem+1 == post_mem, b.mem # should allocate 1 new element

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = X + 2
	result_cell = x_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.JLZ(y_cell, TBD) # not jump
	after_jmp = b.here()
	b.INC(y_cell)
	b.patch_prev(after_jmp)
	b.INC(y_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = Y + 2
	result_cell = y_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.JLZ(z_cell, TBD) # jump
	after_jmp = b.here()
	b.INC(z_cell)
	b.patch_prev(after_jmp)
	b.INC(z_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = Z + 1
	result_cell = z_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'
	
	
	b.JLZ(w_cell, TBD) # not jump (overflow case)
	after_jmp = b.here()
	b.INC(w_cell)
	b.patch_prev(after_jmp)
	b.INC(w_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = -W # max_int + 1 -> min_int (-max_int-1), min_int + 1 -> -max_int
	result_cell = w_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'
	
	
	b.JLZ(u_cell, TBD) # jump
	after_jmp = b.here()
	b.INC(u_cell)
	b.patch_prev(after_jmp)
	b.INC(u_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = U + 1 # min_int + 1
	result_cell = u_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	tmp0 = b.alloc(-1337)
	pre_mem = len(b.mem)

	b.JLZ(x_cell, TBD, tmp0) # not jump
	after_jmp = b.here()
	b.INC(x_cell)
	b.patch_prev(after_jmp)
	b.INC(x_cell)

	post_mem = len(b.mem)
	assert pre_mem == post_mem, b.mem # should not allocate

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = X + 2 + 2
	result_cell = x_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	print("✔️  JLZ")
	return mem




def test_jgz():
	b = Builder()

	X = 2
	Y = 0
	Z = -1

	x_cell = b.alloc(X)
	y_cell = b.alloc(Y)
	z_cell = b.alloc(Z)

	jmp = b.JGZ(x_cell, TBD) # jump
	after_jmp = b.here()
	b.INC(x_cell)
	b.patch_prev(after_jmp)
	b.INC(x_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = X + 1
	result_cell = x_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.JGZ(y_cell, TBD) # not jump
	after_jmp = b.here()
	b.INC(y_cell)
	b.patch_prev(after_jmp)
	b.INC(y_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = Y + 2
	result_cell = y_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.JGZ(z_cell, TBD) # not jump
	after_jmp = b.here()
	b.INC(z_cell)
	b.patch_prev(after_jmp)
	b.INC(z_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = Z + 2
	result_cell = z_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'
	
	
	print("✔️  JGZ")
	return mem




def test_jgez():
	b = Builder()

	X = 2
	Y = 0
	Z = -1
	W = (1 << (BITS-1)) - 1 # max positive value
	U = -(1 << (BITS-1))

	x_cell = b.alloc(X)
	y_cell = b.alloc(Y)
	z_cell = b.alloc(Z)
	w_cell = b.alloc(W)
	u_cell = b.alloc(U)

	pre_mem = len(b.mem)

	b.JGEZ(x_cell, TBD) # jump
	after_jmp = b.here()
	b.INC(x_cell)
	b.patch_prev(after_jmp)
	b.INC(x_cell)

	post_mem = len(b.mem)
	assert pre_mem+1 == post_mem, b.mem # should allocate 1 new element

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = X + 1
	result_cell = x_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.JGEZ(y_cell, TBD) # jump
	after_jmp = b.here()
	b.INC(y_cell)
	b.patch_prev(after_jmp)
	b.INC(y_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = Y + 1
	result_cell = y_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.JGEZ(z_cell, TBD) # not jump
	after_jmp = b.here()
	b.INC(z_cell)
	b.patch_prev(after_jmp)
	b.INC(z_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = Z + 2
	result_cell = z_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'
	
	
	b.JGEZ(w_cell, TBD) # jump (overflow case)
	after_jmp = b.here()
	b.INC(w_cell)
	b.patch_prev(after_jmp)
	b.INC(w_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = -W-1 # max_int + 1 -> min_int (-max_int-1)
	result_cell = w_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'
	
	
	b.JGEZ(u_cell, TBD) # not jump
	after_jmp = b.here()
	b.INC(u_cell)
	b.patch_prev(after_jmp)
	b.INC(u_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = U + 2
	result_cell = u_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	tmp0 = b.alloc(-1337)
	pre_mem = len(b.mem)

	b.JGEZ(w_cell, TBD, tmp0) # not jump
	after_jmp = b.here()
	b.INC(w_cell)
	b.patch_prev(after_jmp)
	b.INC(w_cell)

	post_mem = len(b.mem)
	assert pre_mem == post_mem, b.mem # should not allocate

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = -W - 1 + 2
	result_cell = w_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	print("✔️  JGEZ")
	return mem




def test_shl():
	b = Builder()

	X = 8
	Y = 0
	Z = -2
	W = (1 << (BITS-1))

	x_cell = b.alloc(X)
	y_cell = b.alloc(Y)
	z_cell = b.alloc(Z)
	w_cell = b.alloc(W)

	pre_mem = len(b.mem)

	b.SHL(x_cell, ONE)

	post_mem = len(b.mem)
	assert pre_mem+1 == post_mem, b.mem # should allocate 1 new element

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = X << 1
	result_cell = x_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.SHL(y_cell, ONE)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = Y << 1
	result_cell = y_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'

	
	b.SHL(z_cell, ONE)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = Z << 1
	result_cell = z_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'
	
	
	b.SHL(w_cell, ONE)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = (W << 1) % (1 << BITS)
	assert expected == 0, "W << 1 should overflow to 0"
	result_cell = w_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	tmp0 = b.alloc(-1337)
	pre_mem = len(b.mem)

	b.SHL(x_cell, ONE, tmp0)

	post_mem = len(b.mem)
	assert pre_mem == post_mem, b.mem # should not allocate

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = X << 2
	result_cell = x_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	print("✔️  SHL")
	return mem




def test_not():
	mask = (1<<BITS)-1

	b = Builder()
	X = -1
	X_ptr = b.alloc(X)

	pre_mem = len(b.mem)

	b.NOT(X_ptr)

	post_mem = len(b.mem)
	assert pre_mem+2 == post_mem, b.mem # should allocate 2 new elements

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = (~X & mask)
	assert expected == mem[X_ptr], f"expected {expected:x}, got {mem[X_ptr] & mask:x}"


	b = Builder()
	X = 0
	X_ptr = b.alloc(X)

	b.NOT(X_ptr)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = (~X & mask)
	assert expected == (mem[X_ptr] & mask), f"expected {expected:x}, got {mem[X_ptr] & mask:x}"


	b = Builder()
	X = 0x133742069
	X_ptr = b.alloc(X)

	b.NOT(X_ptr)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = (~X & mask)
	assert expected == (mem[X_ptr] & mask), f"expected {expected:x}, got {mem[X_ptr] & mask:x}"


	b = Builder()
	X = 0xff67676767676767
	X_ptr = b.alloc(X)

	b.NOT(X_ptr)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = (~X & mask)
	assert expected == (mem[X_ptr] & mask), f"expected {expected:x}, got {mem[X_ptr] & mask:x}"
	
	
	b = Builder()
	X = 0
	X_ptr = b.alloc(X)

	tmp0 = b.alloc(-1337)
	tmp1 = b.alloc(-1337)
	pre_mem = len(b.mem)

	b.NOT(X_ptr, tmp0, tmp1)

	post_mem = len(b.mem)
	assert pre_mem == post_mem, b.mem # should not allocate

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = (~X & mask)
	assert expected == (mem[X_ptr] & mask), f"expected {expected:x}, got {mem[X_ptr] & mask:x}"


	print("✔️  NOT")
	return mem




def test_or():
	b = Builder()

	X = 10
	Y = 5
	Z = -1
	W = 0xffffffff
	U = 0xffffffff00000000

	x_cell = b.alloc(X)
	y_cell = b.alloc(Y)
	z_cell = b.alloc(Z)
	w_cell = b.alloc(W)
	u_cell = b.alloc(U)

	pre_mem = len(b.mem)
	
	b.OR(x_cell, x_cell)

	post_mem = len(b.mem)
	assert pre_mem+4 == post_mem, b.mem # should allocate 4 new elements

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = X
	result_cell = x_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.OR(x_cell, ZERO)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = X
	result_cell = x_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.OR(x_cell, y_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = X | Y
	result_cell = x_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.OR(x_cell, y_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = X | Y
	result_cell = x_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.OR(y_cell, x_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = Y | X
	result_cell = y_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.OR(z_cell, ZERO)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = Z
	result_cell = z_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.OR(z_cell, z_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = Z
	result_cell = z_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.OR(ZERO, ZERO)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = 0
	result_cell = ZERO
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.OR(z_cell, y_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = Z | Y
	result_cell = z_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.OR(w_cell, y_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = W | Y
	result_cell = w_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.OR(u_cell, w_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = -1
	result_cell = u_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	tmp0 = b.alloc(-1337)
	tmp1 = b.alloc(-1337)
	tmp2 = b.alloc(-1337)
	pre_mem = len(b.mem)

	b.OR(z_cell, u_cell, tmp0, tmp1, tmp2)
	
	post_mem = len(b.mem)
	assert pre_mem == post_mem, b.mem # should not allocate more

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = Z
	result_cell = z_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	print("✔️  OR")
	return mem




def test_and():
	b = Builder()

	X = 10
	Y = 5
	Z = -1
	W = 6

	x_cell = b.alloc(X)
	y_cell = b.alloc(Y)
	z_cell = b.alloc(Z)
	w_cell = b.alloc(W)

	pre_mem = len(b.mem)
	
	b.AND(x_cell, x_cell)

	post_mem = len(b.mem)
	assert pre_mem+4 == post_mem, b.mem # should allocate 4 new elements

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = X
	result_cell = x_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.AND(w_cell, y_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = W & Y
	result_cell = w_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.AND(x_cell, y_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = X & Y
	result_cell = x_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.AND(y_cell, ZERO)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = 0
	result_cell = y_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'
	
	
	b.AND(y_cell, ZERO)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = 0
	result_cell = y_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.AND(y_cell, x_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = 0
	result_cell = y_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.AND(w_cell, z_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = (W & Y) & Z
	result_cell = w_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.AND(z_cell, z_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = Z
	result_cell = z_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.AND(ZERO, ZERO)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = 0
	result_cell = ZERO
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.AND(z_cell, ZERO)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = 0
	result_cell = z_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	tmp0 = b.alloc(-1337)
	tmp1 = b.alloc(-1337)
	tmp2 = b.alloc(-1337)
	pre_mem = len(b.mem)

	b.AND(w_cell, ZERO, tmp0, tmp1, tmp2)
	
	post_mem = len(b.mem)
	assert pre_mem == post_mem, b.mem # should not allocate more

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = 0
	result_cell = w_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	print("✔️  AND")
	return mem




def test_xor():
	b = Builder()

	X = 10
	Y = 5
	Z = -1
	W = 6

	x_cell = b.alloc(X)
	y_cell = b.alloc(Y)
	z_cell = b.alloc(Z)
	w_cell = b.alloc(W)

	pre_mem = len(b.mem)

	b.XOR(x_cell, ZERO)

	post_mem = len(b.mem)
	assert pre_mem+5 == post_mem, b.mem # should allocate 5 new elements

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = X
	result_cell = x_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.XOR(x_cell, y_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = X ^ Y
	result_cell = x_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.XOR(x_cell, y_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = X ^ Y ^ Y
	result_cell = x_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.XOR(y_cell, w_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = Y ^ W
	result_cell = y_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'
	

	b.XOR(y_cell, z_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = (Y ^ W) ^ Z
	result_cell = y_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.XOR(y_cell, y_cell)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = 0
	result_cell = y_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.XOR(ZERO, ZERO)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = 0
	result_cell = ZERO
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.XOR(z_cell, ZERO)

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = Z
	result_cell = z_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	tmp0 = b.alloc(-1337)
	tmp1 = b.alloc(-1337)
	tmp2 = b.alloc(-1337)
	pre_mem = len(b.mem)

	b.XOR(w_cell, ZERO, tmp0, tmp1, tmp2)
	
	post_mem = len(b.mem)
	assert pre_mem == post_mem, b.mem # should not allocate more

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = W
	result_cell = w_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	print("✔️  XOR")
	return mem




def test_sub():
	b = Builder()

	X = 2
	Y = 3
	Z = -7

	x_cell = b.alloc(X)
	y_cell = b.alloc(Y)
	z_cell = b.alloc(Z)

	pre_mem = len(b.mem)

	b.SUB(y_cell, ZERO) # positive - 0 = positive

	post_mem = len(b.mem)
	assert pre_mem+5 == post_mem, b.mem # should allocate 5 new elements

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = Y
	result_cell = y_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.SUB(y_cell, x_cell) # positive - positive = positive

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = Y - X
	result_cell = y_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.SUB(y_cell, x_cell) # positive - positive = negative

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = (Y - X) - X
	result_cell = y_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.SUB(y_cell, x_cell) # negative - positive = negative

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = (Y - X - X) - X
	result_cell = y_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.SUB(y_cell, ZERO) # negative - 0 = negative

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = Y - X - X - X
	result_cell = y_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.SUB(y_cell, z_cell) # negative - negative = positive

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = (Y - X - X - X) - Z
	result_cell = y_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.SUB(y_cell, z_cell) # positive - negative = positive

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = (Y - X - X - X - Z) - Z
	result_cell = y_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'
	

	b.SUB(z_cell, z_cell) # 0

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = 0
	result_cell = z_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	tmp0 = b.alloc(-1337)
	tmp1 = b.alloc(-1337)
	tmp2 = b.alloc(-1337)
	pre_mem = len(b.mem)

	b.SUB(y_cell, x_cell, tmp0, tmp1, tmp2) # zero memory usage
	
	post_mem = len(b.mem)
	assert pre_mem == post_mem, b.mem # should not allocate more

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = (Y - X - X - X - Z - Z) - X
	result_cell = y_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	print("✔️  SUB")
	return mem




def test_mul():
	b = Builder()

	X = 4
	Y = 3
	Z = -2

	x_cell = b.alloc(X)
	y_cell = b.alloc(Y)
	z_cell = b.alloc(Z)

	pre_mem = len(b.mem)

	b.MUL(x_cell, y_cell) # positive * positive = positive

	post_mem = len(b.mem)
	assert pre_mem+7 == post_mem, b.mem # should allocate 7 new elements

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()
	
	expected = X * Y
	result_cell = x_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	b.MUL(x_cell, z_cell) # positive * negative = negative

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()
	
	expected = (X * Y) * Z
	result_cell = x_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'
	
	
	b.MUL(z_cell, y_cell) # negative * positive = negative

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()
	
	expected = Z * Y
	result_cell = z_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'
	
	
	b.MUL(z_cell, x_cell) # negative * negative = positive

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()
	
	expected = (Z * Y) * (X * Y * Z)
	result_cell = z_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	tmp0 = b.alloc(-1337)
	tmp1 = b.alloc(-1337)
	tmp2 = b.alloc(-1337)
	tmp3 = b.alloc(-1337)
	pre_mem = len(b.mem)

	b.MUL(y_cell, z_cell, tmp0, tmp1, tmp2, tmp3) # zero memory usage
	
	post_mem = len(b.mem)
	assert pre_mem == post_mem, b.mem # should not allocate more

	prog, mem = b.compile()
	vm = AddleqVM(prog, mem)
	mem = vm.run()

	expected = Y * (Z * Y) * (X * Y * Z)
	result_cell = y_cell
	assert mem[result_cell] == expected, f'mem: {mem}\nexpected: {expected}\ngot: mem[{result_cell}]={mem[result_cell]}'


	print("✔️  MUL")
	return mem



#! TESTS

test_add()
test_zero()
test_mov()
test_jlz()
test_jgz()
test_jgez()
test_shl()
test_not()
test_or()
test_and()
test_xor()
test_sub()
test_mul()
