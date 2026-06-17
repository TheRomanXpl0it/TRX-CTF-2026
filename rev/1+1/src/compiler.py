#!/usr/bin/env python3

import sys, os, random, itertools

BITS = 64

class AddleqVM:
	def __init__(self, program, memory, merged=False):
		self.program = list(program)
		self.merged = merged
		if self.merged or memory is None:
			self.mem = None
		else:
			self.mem = list(memory)

	def read(self, addr):
		if self.mem is not None:
			return self.mem[addr]
		else:
			return self.program[addr]

	def write(self, addr, value):
		if self.mem is not None:
			self.mem[addr] = value
		else:
			self.program[addr] = value

	def load_instruction(self, pc):
		if self.mem is not None:
			return self.program[pc]
		else:
			return self.program[pc], self.program[pc+1], self.program[pc+2]

	def instruction_size(self):
		if self.mem is not None:
			return 1
		else:
			return 3

	def run(self, debug_level=0):
		pc = 0
		while 0 <= pc < len(self.program):
			a, b, c = self.load_instruction(pc)

			# print(a, b, c)

			if a == -1:
				self.write(b, sys.stdin.read(1).encode()[0])
				branch = True
			elif a == -2:
				sys.stdout.write(hex(self.read(b) & ((1 << (BITS))-1))[2:])
				sys.stdout.write(" ")
				branch = True
			else:
				self.write(b, self.read(a) + self.read(b))

				if self.read(b) >= (1 << (BITS-1)): # handle overflow
					self.write(b, self.read(b) - (1 << BITS))
				elif self.read(b) < -(1 << (BITS-1)): # handle underflow
					self.write(b, self.read(b) + (1 << BITS))

				branch = self.read(b) <= 0

			if debug_level:
				print(
					f"pc={pc:04d} instr=({a},{b},{c}) "
					f"mem[{a}]={self.read(a)} mem[{b}]={self.read(b)} branch={branch} "
					f'm={self.mem}',
					end=''
				)
				if debug_level < 2: print()
			if debug_level > 1: input()

			pc = c if branch else pc + self.instruction_size()

		if self.mem is not None:
			return self.mem
		else:
			return self.program


TBD = "TBD"
ZERO = 0
ONE = 1
NEG_ONE = 2
BIT_COUNT = 3


class Builder:
	def __init__(self, zero_randomization=False, jmp_randomization=False, FIXED_SEED=False):
		self.mem = []
		self.program = []
		self.zero_randomization = zero_randomization
		self.jmp_randomization = jmp_randomization
		self.FIXED_SEED = FIXED_SEED
		
		if self.jmp_randomization:
			seed = int.from_bytes(os.urandom(16), 'little')
			if self.FIXED_SEED: seed = 1337
			random.seed(seed)

		global ZERO, ONE, NEG_ONE, BIT_COUNT
		ZERO = self.alloc(0)
		ONE = self.alloc(1)
		NEG_ONE = self.alloc(-1)
		BIT_COUNT = self.alloc(BITS)
	
	def alloc(self, value=None):
		if value is None:
			if self.FIXED_SEED:
				value = 0
			else:
				value = int.from_bytes(os.urandom(4), 'little')

		if value >= (1 << (BITS-1)): # handle overflow
			value -= 1 << BITS
		elif value < -(1 << (BITS-1)): # handle underflow
			value += 1 << BITS

		self.mem.append(value)
		return len(self.mem) - 1

	def here(self):
		return len(self.program)

	def patch(self, idx, c=None):
		if c is None:
			c = self.here()
		self.program[idx][2] = c

	def patch_prev(self, next_instruction, target=None):
		self.patch(next_instruction-1, target)


	#! COMPILE !#

	def compile(self, mix_code=False, junk_padding=False, mix_memory=False, merge=False):
		for idx, instr in enumerate(self.program):
			if "TBD" in instr:
				raise ValueError(f"Unpatched instruction at index {idx}: {instr}")

		if mix_code: self.mix_ops(junk_padding=junk_padding)
		if mix_memory: self.mix_memory()
		if merge: self.merge_code_and_memory()
		else: self.remove_tags()

		return self.program, self.mem

	def mix_ops(self, junk_padding=False):
		mixable_idxs = [i for i in range(len(self.program)) if self.program[i][5]]
		mixable_idxs = sorted(set([-1] + mixable_idxs + [len(self.program)-1]))

		idx = 0
		mixables = []
		for i in range(len(mixable_idxs)-1):
			block = []
			for op in self.program[mixable_idxs[i]+1:mixable_idxs[i+1]+1]:
				block.append((idx, op))
				idx += 1
			mixables.append(block)

		seed = int.from_bytes(os.urandom(16), 'little')
		if self.FIXED_SEED: seed = 1337
		random.seed(seed)
		random.shuffle(mixables)

		if junk_padding:
			mem_max = len(self.mem) - 1
			for _ in range(int(len(mixables) // 3 * 2)):
				junk = [
					(-1, [random.randint(0, mem_max), random.randint(0, mem_max), random.randint(0, idx-1), False, False, False])
					for _ in range(random.randint(5, 15))
				]
				mixables.insert(random.randint(0, len(mixables)), junk)

		new_addr_mapping = {}
		new_idx = 1
		for block in mixables:
			for (i, op) in block:
				new_addr_mapping[i] = new_idx
				new_idx += 1
		new_addr_mapping[idx] = new_idx # for exit point

		mixed_prog = [[ZERO, ZERO, new_addr_mapping[0], False, False, True]] # jump to entry point
		for block in mixables:
			for _, op in block:
				if op[3]: # code_mem_a
					op[0] = new_addr_mapping[op[0] // 3] * 3 + (op[0] % 3)
				if op[4]: # code_mem_b
					op[1] = new_addr_mapping[op[1] // 3] * 3 + (op[1] % 3)
				op[2] = new_addr_mapping[op[2]] # remap jump targets
				mixed_prog.append(op)

		self.program = mixed_prog

	def mix_memory(self):
		mixed_mem = [(i, m) for i, m in enumerate(self.mem)]

		seed = int.from_bytes(os.urandom(16), 'little')
		if self.FIXED_SEED: seed = 1337
		random.seed(seed)
		random.shuffle(mixed_mem)

		new_mem_mapping = {}
		for new_idx, (old_idx, m) in enumerate(mixed_mem):
			new_mem_mapping[old_idx] = new_idx

		global ZERO, ONE, NEG_ONE, BIT_COUNT
		ZERO = new_mem_mapping[ZERO]
		ONE = new_mem_mapping[ONE]
		NEG_ONE = new_mem_mapping[NEG_ONE]
		BIT_COUNT = new_mem_mapping[BIT_COUNT]

		for i in range(len(self.program)):
			a, b, c, *flags = self.program[i]
			if a >= 0 and not flags[0]: # code_mem_a
				a = new_mem_mapping[a]
			if b >= 0 and not flags[1]: # code_mem_b
				b = new_mem_mapping[b]
			self.program[i] = [a, b, c] + flags

		mixed_mem = [m for _, m in mixed_mem]
		self.mem = mixed_mem

	def remove_tags(self):
		for i in range(len(self.program)):
			self.program[i] = self.program[i][:3]

	def merge_code_and_memory(self):
		self.program += [[ZERO, ZERO, len(self.program)+len(self.mem)+2, False, False, True]] # jump to exit point

		prog_len = len(self.program)
		for i in range(prog_len):
			if self.program[i][0] >= 0 and not self.program[i][3]: # code_mem_a
				self.program[i][0] += (prog_len * 3)
			if self.program[i][1] >= 0 and not self.program[i][4]: # code_mem_b
				self.program[i][1] += (prog_len * 3)
			self.program[i][2] *= 3

		self.remove_tags()

		self.program = list(itertools.chain.from_iterable(self.program))
		self.program += self.mem


	#! INSTRUCTIONS !#

	def ADDLEQ(self, a, b, c=None, code_mem_a=False, code_mem_b=False, mixable=False):
		if c is None:
			c = len(self.program) + 1
		self.program.append([a, b, c, code_mem_a, code_mem_b, mixable])
		return len(self.program) - 1

	def INPUT(self, dst):
		return self.ADDLEQ(-1, dst, mixable=True)

	def PRINT(self, src):
		return self.ADDLEQ(-2, src, mixable=True)

	def JMP(self, target):
		if self.jmp_randomization:
			b = random.choice([ZERO, NEG_ONE])
		else:
			b = ZERO
		return self.ADDLEQ(ZERO, b, target, mixable=True)

	def NOP(self):
		return self.ADDLEQ(ZERO, ZERO, self.here()+1)

	def ADD(self, dst, src, code_mem_dst=False, code_mem_src=False):
		return self.ADDLEQ(src, dst, code_mem_a=code_mem_src, code_mem_b=code_mem_dst)

	def DEC(self, dst):
		return self.ADD(dst, NEG_ONE)

	def INC(self, dst):
		return self.ADD(dst, ONE)

	def DOUBLE(self, dst):
		return self.ADD(dst, dst)

	def ZERO(self, dst, code_mem_dst=False):
		ip = self.here()
		for _ in range(BITS):
			if self.zero_randomization:
				self.JMP(self.here()+1)
			self.ADD(dst, dst, code_mem_dst=code_mem_dst, code_mem_src=code_mem_dst)
		return ip

	def MOV(self, dst, src, code_mem_dst=False, code_mem_src=False):
		ip = self.ZERO(dst, code_mem_dst=code_mem_dst)
		self.ADD(dst, src, code_mem_dst=code_mem_dst, code_mem_src=code_mem_src)
		return ip

	def COPY_ALLOC(self, src):
		dst = self.alloc()
		return self.MOV(dst, src), dst

	def JLEZ(self, src, target):
		return self.ADDLEQ(ZERO, src, target)

	def JLZ(self, src, target, tmp0=None):
		if tmp0 is None:
			tmp0 = self.alloc()
		ip = self.MOV(tmp0, src)

		less_then_zero = self.ADDLEQ(ZERO, tmp0, TBD) # if x <= 0
		positive = self.JMP(TBD)

		self.patch(less_then_zero) # if x <= 0: jmp here
		self.ADDLEQ(ONE, tmp0, target)

		self.patch(positive) # if if x > 0 and x+1 <= 0 (overflow) jmp here

		return ip

	def JGZ(self, src, target):
		ip = self.JLEZ(src, TBD)
		self.JMP(target)
		self.patch(ip)
		return ip

	def JGEZ(self, src, target, tmp0=None):
		ip = self.JLZ(src, TBD, tmp0)
		after_jmp = self.JMP(target)
		self.patch_prev(after_jmp)
		return ip

	def SHL(self, dst, src, tmp0=None):
		counter = tmp0
		if counter is None:
			counter = self.alloc()
		ip = self.MOV(counter, src)

		loop = self.JLEZ(counter, TBD)

		self.DOUBLE(dst)
		self.DEC(counter)
		self.JMP(loop)

		self.patch(loop)

		return ip

	def NOT(self, src, tmp0=None, tmp1=None):
		counter = tmp0
		if counter is None:
			counter = self.alloc()
		ip = self.MOV(counter, BIT_COUNT)

		loop = self.JLEZ(counter, TBD)

		self.JLZ(src, TBD, tmp1)

		bit_zero = self.DOUBLE(src) # if bit is 0: shift left, and keep 1
		self.ADD(src, ONE)
		bit_zero_jmp = self.JMP(TBD)

		self.patch_prev(bit_zero) # else bit is 1, shift left, and keep 0
		self.DOUBLE(src)

		self.patch(bit_zero_jmp) # end if

		self.DEC(counter)
		self.JMP(loop)

		self.patch(loop)

		return ip

	def OR(self, dst, src, tmp0=None, tmp1=None, tmp2=None):
		counter = tmp0
		if counter is None:
			counter = self.alloc()
		ip = self.MOV(counter, BIT_COUNT)

		src_cpy = tmp1
		if src_cpy is None:
			src_cpy = self.alloc()
		self.MOV(src_cpy, src)

		loop = self.JLEZ(counter, TBD)

		self.JLZ(src_cpy, TBD, tmp2)
		src_bit_one = self.here()
		self.JLZ(dst, TBD, tmp2)
		dst_bit_one = self.here()

		# if src and dst bits are 0, shift left and keep 0
		self.DOUBLE(src_cpy)
		self.DOUBLE(dst)
		bit_zero_jmp = self.JMP(TBD)

		self.patch_prev(src_bit_one) # if src bit is 1
		self.patch_prev(dst_bit_one) # if dst bit is 1

		# shift left and keep 1
		self.DOUBLE(src_cpy)
		self.DOUBLE(dst)
		self.ADD(dst, ONE)

		self.patch(bit_zero_jmp) # end if

		self.DEC(counter)
		self.JMP(loop)

		self.patch(loop)

		return ip

	def AND(self, dst, src, tmp0=None, tmp1=None, tmp2=None):
		counter = tmp0
		if counter is None:
			counter = self.alloc()
		ip = self.MOV(counter, BIT_COUNT)

		src_cpy = tmp1
		if src_cpy is None:
			src_cpy = self.alloc()
		self.MOV(src_cpy, src)

		loop = self.JLEZ(counter, TBD)

		self.JGEZ(src_cpy, TBD, tmp2)
		src_bit_zero = self.here()
		self.JGEZ(dst, TBD, tmp2)
		dst_bit_zero = self.here()

		# if src and dst bits are 1, shift left and keep 1
		self.DOUBLE(src_cpy)
		self.DOUBLE(dst)
		self.ADD(dst, ONE)
		bit_one_jmp = self.JMP(TBD)

		self.patch_prev(src_bit_zero) # if src bit is 0
		self.patch_prev(dst_bit_zero) # if dst bit is 0

		# shift left and keep 0
		self.DOUBLE(src_cpy)
		self.DOUBLE(dst)

		self.patch(bit_one_jmp) # end if

		self.DEC(counter)
		self.JMP(loop)

		self.patch(loop)

		return ip

	def XOR(self, dst, src, tmp0=None, tmp1=None, tmp2=None):
		counter = tmp0
		if counter is None:
			counter = self.alloc()
		ip = self.MOV(counter, BIT_COUNT)

		src_cpy = tmp1
		if src_cpy is None:
			src_cpy = self.alloc()
		self.MOV(src_cpy, src)

		loop = self.JLEZ(counter, TBD)

		self.JLZ(src_cpy, TBD, tmp2) # if 1 jmp
		src_bit_zero = self.here()

		self.JLZ(dst, TBD, tmp2) # if 0 and 1 jmp
		zero_zero = self.JMP(TBD)

		self.patch_prev(src_bit_zero)
		self.JLZ(dst, TBD, tmp2) # if 1 and 1 jmp
		one_one = self.here()

		# keep 1
		self.patch_prev(zero_zero)
		self.DOUBLE(src_cpy)
		self.DOUBLE(dst)
		self.ADD(dst, ONE)
		bit_one_jmp = self.JMP(TBD)

		# keep 0
		self.patch(zero_zero)
		self.patch_prev(one_one)
		self.DOUBLE(src_cpy)
		self.DOUBLE(dst)

		self.patch(bit_one_jmp) # end if

		self.DEC(counter)
		self.JMP(loop)

		self.patch(loop)

		return ip

	def NEG(self, dst, tmp0=None, tmp1=None):
		ip = self.NOT(dst, tmp0, tmp1)
		self.INC(dst)
		return ip

	def SUB(self, dst, src, tmp0=None, tmp1=None, tmp2=None):
		src_cpy = tmp0
		if src_cpy is None:
			src_cpy = self.alloc()
		ip = self.MOV(src_cpy, src)

		self.NEG(dst, tmp1, tmp2)
		self.ADD(dst, src_cpy)
		self.NEG(dst, tmp1, tmp2)

		return ip

	def MUL(self, dst, src, tmp0=None, tmp1=None, tmp2=None, tmp3=None):
		counter = tmp0
		if counter is None:
			counter = self.alloc()
		ip = self.MOV(counter, src)

		coefficient = tmp1
		if coefficient is None:
			coefficient = self.alloc()
		self.MOV(coefficient, dst)

		self.JGEZ(counter, TBD, tmp2)
		positive = self.here()

		self.NEG(coefficient, tmp2, tmp3) # x < 0: swap signs
		self.NEG(counter, tmp2, tmp3)

		self.patch_prev(positive) # x >= 0

		self.ZERO(dst)

		loop = self.JLEZ(counter, TBD)

		self.ADD(dst, coefficient)
		self.DEC(counter)
		self.JMP(loop)

		self.patch(loop)

		return ip

	def ARRAY_READ(self, dst, arr, offset, tmp0=None):
		if tmp0 is None:
			tmp0 = self.alloc()

		before_mov = self.here()
		self.MOV(tmp0, arr) # set tmp0 to the base address of the array
		mov_size = self.here() - before_mov

		self.ADD(tmp0, offset) # add the offset to tmp0, now tmp0 points to arr[offset]

		self.ZERO(dst) # set to 0 the output

		# move the value at tmp0 (arr[offset]) to the add of next instruction
		# so it does mem[dst] += mem[arr[offset]] where mem[dst] is 0
		self.MOV((self.here() + mov_size)*3, tmp0, code_mem_dst=True)

		self.ADD(dst, 0) # read the value from the array
	
	def ARRAY_WRITE(self, arr, offset, src, tmp0=None, tmp1=None, tmp2=None):
		diff = tmp0
		if diff is None:
			diff = self.alloc()
		if tmp1 is None:
			tmp1 = self.alloc()

		# diff = src - arr[offset]
		self.ARRAY_READ(diff, arr, offset, tmp1)
		self.NEG(diff, tmp1, tmp2)
		self.ADD(diff, src)

		before_mov = self.here()
		self.MOV(tmp1, arr) # set tmp1 to the base address of the array
		mov_size = self.here() - before_mov

		self.ADD(tmp1, offset) # add the offset to tmp1, now tmp1 points to arr[offset]

		# move the value at tmp1 (arr[offset]) to the add of next instruction
		# so it does mem[arr[offset]] += mem[diff]
		self.MOV((self.here() + mov_size)*3 + 1, tmp1, code_mem_dst=True)

		self.ADD(0, diff) # read the value from the array


	#! SECOND ORDER INSTRUCTIONS !#

	def ZERO_2o(self, dst, tmp0=None, tmp1=None, tmp2=None):
		return self.SUB(dst, dst, tmp0, tmp1, tmp2)

	def MOV_2o(self, dst, src, tmp0=None, tmp1=None, tmp2=None):
		ip = self.ZERO_2o(dst, tmp0, tmp1, tmp2)
		self.ADD(dst, src)
		return ip

	def COPY_ALLOC_2o(self, src, tmp0=None, tmp1=None, tmp2=None):
		dst = self.alloc()
		return self.MOV_2o(dst, src, tmp0, tmp1, tmp2), dst

	def JLZ_2o(self, src, target, tmp0=None, tmp1=None, tmp2=None, tmp3=None):
		if tmp0 is None:
			tmp0 = self.alloc()
		ip = self.MOV_2o(tmp0, src, tmp1, tmp2, tmp3)

		less_then_zero = self.ADDLEQ(ZERO, tmp0, TBD) # if x <= 0
		positive = self.JMP(TBD)

		self.patch(less_then_zero) # if x <= 0: jmp here
		self.ADDLEQ(ONE, tmp0, target)

		self.patch(positive) # if if x > 0 and x+1 <= 0 (overflow) jmp here

		return ip

	def JGEZ_2o(self, src, target, tmp0=None, tmp1=None, tmp2=None, tmp3=None):
		ip = self.JLZ_2o(src, TBD, tmp0, tmp1, tmp2, tmp3)
		after_jmp = self.JMP(target)
		self.patch_prev(after_jmp)
		return ip

	def SHL_2o(self, dst, src, tmp0=None, tmp1=None, tmp2=None, tmp3=None):
		counter = tmp0
		if counter is None:
			counter = self.alloc()
		ip = self.MOV_2o(counter, src, tmp1, tmp2, tmp3)

		loop = self.JLEZ(counter, TBD)

		self.DOUBLE(dst)
		self.DEC(counter)
		self.JMP(loop)

		self.patch(loop)

		return ip

	def NOT_2o(self, src, tmp0=None, tmp1=None, tmp2=None, tmp3=None, tmp4=None):
		counter = tmp0
		if counter is None:
			counter = self.alloc()
		ip = self.MOV_2o(counter, BIT_COUNT, tmp1, tmp2, tmp3)

		loop = self.JLEZ(counter, TBD)

		self.JLZ_2o(src, TBD, tmp1, tmp2, tmp3, tmp4)

		bit_zero = self.DOUBLE(src) # if bit is 0: shift left, and keep 1
		self.ADD(src, ONE)
		bit_zero_jmp = self.JMP(TBD)

		self.patch_prev(bit_zero) # else bit is 1, shift left, and keep 0
		self.DOUBLE(src)

		self.patch(bit_zero_jmp) # end if

		self.DEC(counter)
		self.JMP(loop)

		self.patch(loop)

		return ip

	def OR_2o(self, dst, src, tmp0=None, tmp1=None, tmp2=None, tmp3=None, tmp4=None, tmp5=None):
		counter = tmp0
		if counter is None:
			counter = self.alloc()
		ip = self.MOV_2o(counter, BIT_COUNT, tmp1, tmp2, tmp3)

		src_cpy = tmp1
		if src_cpy is None:
			src_cpy = self.alloc()
		self.MOV_2o(src_cpy, src, tmp2, tmp3, tmp4)

		loop = self.JLEZ(counter, TBD)

		self.JLZ_2o(src_cpy, TBD, tmp2, tmp3, tmp4, tmp5)
		src_bit_one = self.here()
		self.JLZ_2o(dst, TBD, tmp2, tmp3, tmp4, tmp5)
		dst_bit_one = self.here()

		# if src and dst bits are 0, shift left and keep 0
		self.DOUBLE(src_cpy)
		self.DOUBLE(dst)
		bit_zero_jmp = self.JMP(TBD)

		self.patch_prev(src_bit_one) # if src bit is 1
		self.patch_prev(dst_bit_one) # if dst bit is 1

		# shift left and keep 1
		self.DOUBLE(src_cpy)
		self.DOUBLE(dst)
		self.ADD(dst, ONE)

		self.patch(bit_zero_jmp) # end if

		self.DEC(counter)
		self.JMP(loop)

		self.patch(loop)

		return ip

	def AND_2o(self, dst, src, tmp0=None, tmp1=None, tmp2=None, tmp3=None, tmp4=None, tmp5=None):
		counter = tmp0
		if counter is None:
			counter = self.alloc()
		ip = self.MOV_2o(counter, BIT_COUNT, tmp1, tmp2, tmp3)

		src_cpy = tmp1
		if src_cpy is None:
			src_cpy = self.alloc()
		self.MOV_2o(src_cpy, src, tmp2, tmp3, tmp4)

		loop = self.JLEZ(counter, TBD)

		self.JGEZ_2o(src_cpy, TBD, tmp2, tmp3, tmp4, tmp5)
		src_bit_zero = self.here()
		self.JGEZ_2o(dst, TBD, tmp2, tmp3, tmp4, tmp5)
		dst_bit_zero = self.here()

		# if src and dst bits are 1, shift left and keep 1
		self.DOUBLE(src_cpy)
		self.DOUBLE(dst)
		self.ADD(dst, ONE)
		bit_one_jmp = self.JMP(TBD)

		self.patch_prev(src_bit_zero) # if src bit is 0
		self.patch_prev(dst_bit_zero) # if dst bit is 0

		# shift left and keep 0
		self.DOUBLE(src_cpy)
		self.DOUBLE(dst)

		self.patch(bit_one_jmp) # end if

		self.DEC(counter)
		self.JMP(loop)

		self.patch(loop)

		return ip

	def XOR_2o(self, dst, src, tmp0=None, tmp1=None, tmp2=None, tmp3=None, tmp4=None, tmp5=None):
		counter = tmp0
		if counter is None:
			counter = self.alloc()
		ip = self.MOV_2o(counter, BIT_COUNT, tmp1, tmp2, tmp3)

		src_cpy = tmp1
		if src_cpy is None:
			src_cpy = self.alloc()
		self.MOV_2o(src_cpy, src, tmp2, tmp3, tmp4)

		loop = self.JLEZ(counter, TBD)

		self.JLZ_2o(src_cpy, TBD, tmp2, tmp3, tmp4, tmp5) # if 1 jmp
		src_bit_zero = self.here()

		self.JLZ_2o(dst, TBD, tmp2, tmp3, tmp4, tmp5) # if 0 and 1 jmp
		zero_zero = self.JMP(TBD)

		self.patch_prev(src_bit_zero)
		self.JLZ_2o(dst, TBD, tmp2, tmp3, tmp4, tmp5) # if 1 and 1 jmp
		one_one = self.here()

		# keep 1
		self.patch_prev(zero_zero)
		self.DOUBLE(src_cpy)
		self.DOUBLE(dst)
		self.ADD(dst, ONE)
		bit_one_jmp = self.JMP(TBD)

		# keep 0
		self.patch(zero_zero)
		self.patch_prev(one_one)
		self.DOUBLE(src_cpy)
		self.DOUBLE(dst)

		self.patch(bit_one_jmp) # end if

		self.DEC(counter)
		self.JMP(loop)

		self.patch(loop)

		return ip

	def NEG_2o(self, dst, tmp0=None, tmp1=None, tmp2=None, tmp3=None, tmp4=None):
		ip = self.NOT_2o(dst, tmp0, tmp1, tmp2, tmp3, tmp4)
		self.INC(dst)
		return ip

	def SUB_2o(self, dst, src, tmp0=None, tmp1=None, tmp2=None, tmp3=None, tmp4=None, tmp5=None):
		src_cpy = tmp0
		if src_cpy is None:
			src_cpy = self.alloc()
		ip = self.MOV_2o(src_cpy, src, tmp1, tmp2, tmp3)

		self.NEG_2o(dst, tmp1, tmp2, tmp3, tmp4, tmp5)
		self.ADD(dst, src_cpy)
		self.NEG_2o(dst, tmp1, tmp2, tmp3, tmp4, tmp5)

		return ip

	def MUL_2o(self, dst, src, tmp0=None, tmp1=None, tmp2=None, tmp3=None, tmp4=None, tmp5=None, tmp6=None):
		counter = tmp0
		if counter is None:
			counter = self.alloc()
		ip = self.MOV_2o(counter, src, tmp1, tmp2, tmp3)

		coefficient = tmp1
		if coefficient is None:
			coefficient = self.alloc()
		self.MOV_2o(coefficient, dst, tmp2, tmp3, tmp4)

		self.JGEZ_2o(counter, TBD, tmp2, tmp3, tmp4, tmp5)
		positive = self.here()

		self.NEG_2o(coefficient, tmp2, tmp3, tmp4, tmp5, tmp6) # x < 0: swap signs
		self.NEG_2o(counter, tmp2, tmp3, tmp4, tmp5, tmp6)

		self.patch_prev(positive) # x >= 0

		self.ZERO_2o(dst, tmp2, tmp3, tmp4)

		loop = self.JLEZ(counter, TBD)

		self.ADD(dst, coefficient)
		self.DEC(counter)
		self.JMP(loop)

		self.patch(loop)

		return ip

	def ARRAY_READ_2o(self, dst, arr, offset, tmp0=None, tmp1=None, tmp2=None, tmp3=None):
		if tmp0 is None:
			tmp0 = self.alloc()

		self.MOV_2o(tmp0, arr, tmp1, tmp2, tmp3) # set tmp0 to the base address of the array
		
		# create a normal mov to compute its size then delete it
		pog_size, mem_size = len(self.program), len(self.mem)
		before_mov = self.here()
		self.MOV(tmp0, arr)
		mov_size = self.here() - before_mov
		self.program, self.mem = self.program[:pog_size], self.mem[:mem_size]

		self.ADD(tmp0, offset) # add the offset to tmp0, now tmp0 points to arr[offset]

		self.ZERO_2o(dst, tmp1, tmp2, tmp3) # set to 0 the output

		# move the value at tmp0 (arr[offset]) to the add of next instruction
		# so it does mem[dst] += mem[arr[offset]] where mem[dst] is 0
		self.MOV((self.here() + mov_size)*3, tmp0, code_mem_dst=True)

		self.ADD(dst, 0) # read the value from the array

	def ARRAY_WRITE_2o(self, arr, offset, src, tmp0=None, tmp1=None, tmp2=None, tmp3=None, tmp4=None, tmp5=None):
		diff = tmp0
		if diff is None:
			diff = self.alloc()
		if tmp1 is None:
			tmp1 = self.alloc()

		# diff = src - arr[offset]
		self.ARRAY_READ_2o(diff, arr, offset, tmp1, tmp2, tmp3, tmp4)
		self.NEG_2o(diff, tmp1, tmp2, tmp3, tmp4, tmp5)
		self.ADD(diff, src)

		self.MOV_2o(tmp1, arr, tmp2, tmp3, tmp4) # set tmp1 to the base address of the array

		# create a normal mov to compute its size then delete it
		pog_size, mem_size = len(self.program), len(self.mem)
		before_mov = self.here()
		self.MOV(tmp0, arr)
		mov_size = self.here() - before_mov
		self.program, self.mem = self.program[:pog_size], self.mem[:mem_size]

		self.ADD(tmp1, offset) # add the offset to tmp1, now tmp1 points to arr[offset]

		# move the value at tmp1 (arr[offset]) to the add of next instruction
		# so it does mem[arr[offset]] += mem[diff]
		self.MOV((self.here() + mov_size)*3 + 1, tmp1, code_mem_dst=True)

		self.ADD(0, diff) # read the value from the array

