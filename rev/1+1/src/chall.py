import random
from math import ceil

flag = b'TRX{you_really_did_it_you_can_do_additions_you_won_this_cookie_-->_http://youtube.com/post/UgkxZyfYqbQJRn86UCsEh8AZBnE8GVO-4fXI}'


seed = 0x1337
random.seed(seed)


box = list(range(0, 256))
random.shuffle(box)

box2 = [None] * 256
for i in range(len(box)):
	box2[i] = box[box[i]]

pbox = list(range(0, len(flag)))
random.shuffle(pbox)

PBOX_CYCLES = 7

def spn(data):
	data = list(map(int, data))
	data = data[::-1]

	for i in range(len(data)):
		data[i] = box[data[i]]
		data[i] = (data[i] + 1) % 256

	new = [None] * len(data)
	for _ in range(PBOX_CYCLES):
		for i in range(len(data)-1, -1, -1):
			new[i] = data[pbox[i]]
		data = new[:]

	for i in range(len(data)):
		data[i] = box2[data[i]]
		data[i] ^= 0x67

	return bytes(data[::-1])

def inv_spn(data):
	data = list(map(int, data))
	data = data[::-1]

	for i in range(len(data)):
		data[i] ^= 0x67
		data[i] = box2.index(data[i])

	new = [None] * len(data)
	for _ in range(PBOX_CYCLES):
		for i in range(len(data)-1, -1, -1):
			new[i] = data[pbox.index(i)]
		data = new[:]

	for i in range(len(data)):
		data[i] = (data[i] - 1 + 256) % 256
		data[i] = box.index(data[i])
	
	return bytes(data[::-1])

def fnv_32_step(data, seed):
	h = seed
	for b in data:
		h = (h * 0x01013255) % (1 << 32)
		h = h ^ b
	return h

FNV_SEED = 0x0a1b2c3d
def fnv_32(data):
	seeds = [FNV_SEED]
	for i in range(0, len(data), 4):
		seeds.append(fnv_32_step(data[i:i+4], seeds[-1]))
	return seeds[1:]

print(flag.decode())
def main():
	enc = spn(flag)
	assert inv_spn(enc) == flag
	blocks = fnv_32(enc)
	for block in blocks:
		print(hex(block)[2:], end=" ")
	print()


from compiler import *

FIXED_SEED = True
zero_randomization = True
jmp_randomization = True
mix_code = True
junk_padding = True # only with mix_code
mix_memory = False
merge = True


b = Builder(
	zero_randomization=zero_randomization,
	jmp_randomization=jmp_randomization,
	FIXED_SEED=FIXED_SEED,
)

#! CODE !#

ORDER_2 = True


PROG_SIZE = (58327) * 3
if ORDER_2:
	PROG_SIZE = (252822) * 3


box_arr = [None] * len(box)
for i in range(len(box_arr)):
	box_arr[i] = b.alloc(box[i])
box_arr_addr = b.alloc(box_arr[0] + PROG_SIZE)

pbox_arr = [None] * len(pbox)
for i in range(len(pbox_arr)):
	pbox_arr[i] = b.alloc(pbox[i])
pbox_arr_addr = b.alloc(pbox_arr[0] + PROG_SIZE)

flag_arr = [None] * len(flag)
for i in range(len(flag_arr)):
	flag_arr[i] = b.alloc(0)
flag_input_addr = b.alloc(flag_arr[0] + PROG_SIZE)

tmp_flag_arr = [None] * len(flag)
for i in range(len(tmp_flag_arr)):
	tmp_flag_arr[i] = b.alloc()
tmp_flag_input_addr = b.alloc(tmp_flag_arr[0] + PROG_SIZE)

hashes_length = ceil(len(flag) / 4) + 1
hashes = [None] * hashes_length
hashes[0] = b.alloc(FNV_SEED)
for i in range(1, hashes_length):
	hashes[i] = b.alloc()
hashes_addr = b.alloc(hashes[0] + PROG_SIZE)

length = b.alloc(len(flag))
pbox_cycles = b.alloc(PBOX_CYCLES)
hashes_len = b.alloc(hashes_length)
fnv_seed = b.alloc(FNV_SEED)
fnv_const = b.alloc(0x13255)
fnv_const_24 = b.alloc(24)
fnv_char_per_block = b.alloc(3)
mask32 = b.alloc(0xffffffff)

out = b.alloc()
out_tmp = b.alloc()
char = b.alloc()
counter = b.alloc()

tmp0 = b.alloc()
tmp1 = b.alloc()
tmp2 = b.alloc()
tmp3 = b.alloc()

i = b.alloc()
j = b.alloc()


if not ORDER_2:
	#! READ CYCLE !#

	# for i in range(len(flag)-1, -1, -1)
	b.MOV(i, length)
	loop = b.JLEZ(i, TBD)
	b.DEC(i)

	# flag_input_addr[i] = read(1)
	b.INPUT(char)
	b.ARRAY_WRITE(flag_input_addr, i, char, tmp0, tmp1, tmp2)

	b.JMP(loop)
	b.patch(loop)


	#! SBOX CYCLE !#

	# for i in range(len(flag)-1, -1, -1)
	b.MOV(i, length)
	loop = b.JLEZ(i, TBD)
	b.DEC(i)

	# char = flag_input_addr[i]
	b.ARRAY_READ(char, flag_input_addr, i, tmp0)

	# out = box[char]
	b.ARRAY_READ(out, box_arr_addr, char, tmp0)

	# out = (out + 1) % 256
	b.INC(out)
	b.AND(out, box_arr[box.index(0xff)], tmp0, tmp1, tmp2)

	# flag_input_addr[i] = out
	b.ARRAY_WRITE(flag_input_addr, i, out, tmp0, tmp1, tmp2)

	b.JMP(loop)
	b.patch(loop)


	#! PBOX CYCLE !#

	# for i in range(pbox_cycles, 0, -1)
	b.MOV(j, pbox_cycles)
	pbox_loop = b.JLEZ(j, TBD)

	# for i in range(len(flag)-1, -1, -1)
	b.MOV(i, length)
	loop = b.JLEZ(i, TBD)
	b.DEC(i)

	# tmp_flag_input_addr[i] = flag_input_addr[pbox[i]]
	b.ARRAY_READ(out, pbox_arr_addr, i, tmp0)
	b.ARRAY_READ(char, flag_input_addr, out, tmp0)
	b.ARRAY_WRITE(tmp_flag_input_addr, i, char, tmp0, tmp1, tmp2)

	b.JMP(loop)
	b.patch(loop)


	# for i in range(len(flag)-1, -1, -1)
	b.MOV(i, length)
	loop = b.JLEZ(i, TBD)
	b.DEC(i)

	# flag_input_addr[i] = tmp_flag_input_addr[i]
	b.ARRAY_READ(out, tmp_flag_input_addr, i, tmp0)
	b.ARRAY_WRITE(flag_input_addr, i, out, tmp0, tmp1, tmp2)

	b.JMP(loop)
	b.patch(loop)


	b.DEC(j)
	b.JMP(pbox_loop)
	b.patch(pbox_loop)


	#! SBOX 2 CYCLE !#

	# for i in range(len(flag)-1, -1, -1)
	b.MOV(i, length)
	loop = b.JLEZ(i, TBD)
	b.DEC(i)

	# out = flag_input_addr[i]
	b.ARRAY_READ(out, flag_input_addr, i, tmp0)

	# out = box[box[out]]
	b.ARRAY_READ(out_tmp, box_arr_addr, out, tmp0)
	b.ARRAY_READ(out, box_arr_addr, out_tmp, tmp0)

	# out ^= 0x67
	b.XOR(out, box_arr[box.index(0x67)], tmp0, tmp1, tmp2)

	# flag_input_addr[i] = out
	b.ARRAY_WRITE(flag_input_addr, i, out, tmp0, tmp1, tmp2)

	b.JMP(loop)
	b.patch(loop)


	#! FNV CYCLE !#

	b.MOV(out, fnv_seed)

	# for j in range(len(length)-1, -1, -1)
	b.MOV(j, length)
	hashes_loop = b.JLEZ(j, TBD)
	b.DEC(j)

	# h *= 0x01000193
	b.MOV(out_tmp, out)
	b.MUL(out_tmp, fnv_const, tmp0, tmp1, tmp2, tmp3) # h *= 0x193
	b.SHL(out, fnv_const_24, tmp0) # h <<= 24  ===  h *= 0x1000000
	b.ADD(out, out_tmp)

	b.AND(out, mask32, tmp0, tmp1, tmp2)

	# h ^= flag_input_addr[j]
	b.ARRAY_READ(char, flag_input_addr, j, tmp0)
	b.XOR(out, char, tmp0, tmp1, tmp2)

	# counter = (j & 3) - 1
	b.MOV(counter, j)
	b.AND(counter, fnv_char_per_block, tmp0, tmp1, tmp2)
	# b.DEC(counter)
	
	# if countr != 0 jump
	b.JLZ(counter, TBD, tmp0)
	skip_print = b.here()
	b.JGZ(counter, TBD)
	skip_print2 = b.here()

	# print(hex(out)[2:], end=" ")
	b.PRINT(out)

	b.patch_prev(skip_print)
	b.patch_prev(skip_print2)

	b.JMP(hashes_loop)
	b.patch(hashes_loop)

	if len(flag) % 4 != 0:
		# print(hex(out)[2:], end=" ")
		b.PRINT(out)


else: #! #################### ORDER 2 #################### !#
	tmp4 = b.alloc()
	tmp5 = b.alloc()
	tmp6 = b.alloc()

	#! READ CYCLE !#

	# for i in range(len(flag)-1, -1, -1)
	b.MOV_2o(i, length, tmp0, tmp1, tmp2)
	loop = b.JLEZ(i, TBD)
	b.DEC(i)

	# flag_input_addr[i] = read(1)
	b.INPUT(char)
	b.ARRAY_WRITE_2o(flag_input_addr, i, char, tmp0, tmp1, tmp2, tmp3, tmp4, tmp5)

	b.JMP(loop)
	b.patch(loop)


	#! SBOX CYCLE !#

	# for i in range(len(flag)-1, -1, -1)
	b.MOV_2o(i, length, tmp0, tmp1, tmp2)
	loop = b.JLEZ(i, TBD)
	b.DEC(i)

	# char = flag_input_addr[i]
	b.ARRAY_READ_2o(char, flag_input_addr, i, tmp0, tmp1, tmp2, tmp3)

	# out = box[char]
	b.ARRAY_READ_2o(out, box_arr_addr, char, tmp0, tmp1, tmp2, tmp3)

	# out = (out + 1) % 256
	b.INC(out)
	b.AND_2o(out, box_arr[box.index(0xff)], tmp0, tmp1, tmp2, tmp3, tmp4, tmp5)

	# flag_input_addr[i] = out
	b.ARRAY_WRITE_2o(flag_input_addr, i, out, tmp0, tmp1, tmp2, tmp3, tmp4, tmp5)

	b.JMP(loop)
	b.patch(loop)


	#! PBOX CYCLE !#

	# for i in range(pbox_cycles, 0, -1)
	b.MOV_2o(j, pbox_cycles, tmp0, tmp1, tmp2)
	pbox_loop = b.JLEZ(j, TBD)

	# for i in range(len(flag)-1, -1, -1)
	b.MOV_2o(i, length, tmp0, tmp1, tmp2)
	loop = b.JLEZ(i, TBD)
	b.DEC(i)

	# tmp_flag_input_addr[i] = flag_input_addr[pbox[i]]
	b.ARRAY_READ_2o(out, pbox_arr_addr, i, tmp0, tmp1, tmp2, tmp3)
	b.ARRAY_READ_2o(char, flag_input_addr, out, tmp0, tmp1, tmp2, tmp3)
	b.ARRAY_WRITE_2o(tmp_flag_input_addr, i, char, tmp0, tmp1, tmp2, tmp3, tmp4, tmp5)

	b.JMP(loop)
	b.patch(loop)


	# for i in range(len(flag)-1, -1, -1)
	b.MOV_2o(i, length, tmp0, tmp1, tmp2)
	loop = b.JLEZ(i, TBD)
	b.DEC(i)

	# flag_input_addr[i] = tmp_flag_input_addr[i]
	b.ARRAY_READ_2o(out, tmp_flag_input_addr, i, tmp0, tmp1, tmp2, tmp3)
	b.ARRAY_WRITE_2o(flag_input_addr, i, out, tmp0, tmp1, tmp2, tmp3, tmp4, tmp5)

	b.JMP(loop)
	b.patch(loop)


	b.DEC(j)
	b.JMP(pbox_loop)
	b.patch(pbox_loop)


	#! SBOX 2 CYCLE !#

	# for i in range(len(flag)-1, -1, -1)
	b.MOV_2o(i, length, tmp0, tmp1, tmp2)
	loop = b.JLEZ(i, TBD)
	b.DEC(i)

	# out = flag_input_addr[i]
	b.ARRAY_READ_2o(out, flag_input_addr, i, tmp0, tmp1, tmp2, tmp3)

	# out = box[box[out]]
	b.ARRAY_READ_2o(out_tmp, box_arr_addr, out, tmp0, tmp1, tmp2, tmp3)
	b.ARRAY_READ_2o(out, box_arr_addr, out_tmp, tmp0, tmp1, tmp2, tmp3)

	# out ^= 0x67
	b.XOR_2o(out, box_arr[box.index(0x67)], tmp0, tmp1, tmp2, tmp3, tmp4, tmp5)

	# flag_input_addr[i] = out
	b.ARRAY_WRITE_2o(flag_input_addr, i, out, tmp0, tmp1, tmp2, tmp3, tmp4, tmp5)

	b.JMP(loop)
	b.patch(loop)

	
	#! FNV CYCLE !#

	b.MOV_2o(out, fnv_seed, tmp0, tmp1, tmp2)

	# for j in range(len(length)-1, -1, -1)
	b.MOV_2o(j, length, tmp0, tmp1, tmp2)
	hashes_loop = b.JLEZ(j, TBD)
	b.DEC(j)

	# h *= 0x01000193
	b.MOV_2o(out_tmp, out, tmp0, tmp1, tmp2)
	b.MUL_2o(out_tmp, fnv_const, tmp0, tmp1, tmp2, tmp3, tmp4, tmp5, tmp6) # h *= 0x193
	b.SHL_2o(out, fnv_const_24, tmp0, tmp1, tmp2, tmp3) # h <<= 24  ===  h *= 0x1000000
	b.ADD(out, out_tmp)

	b.AND_2o(out, mask32, tmp0, tmp1, tmp2, tmp3, tmp4, tmp5)

	# h ^= flag_input_addr[j]
	b.ARRAY_READ_2o(char, flag_input_addr, j, tmp0, tmp1, tmp2, tmp3)
	b.XOR_2o(out, char, tmp0, tmp1, tmp2, tmp3, tmp4, tmp5)

	# counter = (j & 3) - 1
	b.MOV_2o(counter, j, tmp0, tmp1, tmp2)
	b.AND_2o(counter, fnv_char_per_block, tmp0, tmp1, tmp2, tmp3, tmp4, tmp5)
	# b.DEC(counter)

	# if countr != 0 jump
	b.JLZ_2o(counter, TBD, tmp0, tmp1, tmp2, tmp3)
	skip_print = b.here()
	b.JGZ(counter, TBD)
	skip_print2 = b.here()

	# print(hex(out)[2:], end=" ")
	b.PRINT(out)

	b.patch_prev(skip_print)
	b.patch_prev(skip_print2)

	b.JMP(hashes_loop)
	b.patch(hashes_loop)

	if len(flag) % 4 != 0:
		# print(hex(out)[2:], end=" ")
		b.PRINT(out)



#! END CODE !#
debug_level = 0


prog, mem = b.compile(
	mix_code=mix_code,
	junk_padding=junk_padding,
	mix_memory=mix_memory,
	merge=merge,
)
print((len(prog) - len(mem)) // 3, "instructions")


with open("bytecode.bin", "wb") as f:
	for b in prog:
		f.write((b & ((1 << BITS)-1)).to_bytes(8, 'little'))


vm = AddleqVM(prog, mem, merged=merge)
prog = vm.run(debug_level)
main()
