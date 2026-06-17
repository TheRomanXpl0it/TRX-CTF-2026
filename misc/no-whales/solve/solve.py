from tqdm import tqdm
import re

BLOCKS = 50

FILE = './Dockerfile'


with open(FILE) as f:
	data = f.read()

# Split stages
stages = [x.strip() for x in data.split('FROM alpine-bash AS ') if x.strip()]


# Retrive previous stages for each stage
prevs_stages = []
for i in range(len(stages)):
	copies = re.findall(r'COPY --from=l\d+ /\d+ /\d+\n', stages[i])
	unique_previous = list(set([int(x.split('--from=l')[1].split(' ')[0]) for x in copies]))
	prevs_stages.append(unique_previous)


# Build the graph
g = {}
for i, prevs_stage in enumerate(prevs_stages):
	for prev in prevs_stage:
		g[prev] = g.get(prev, []) + [i]


# Clean the copies from the stages
for i in tqdm(range(len(stages))):
	for j in range(21 * BLOCKS):
		for k in range(BLOCKS):
			stages[i] = stages[i].replace(f'COPY --from=l{j} /{k} /{k}\n', '')
	stages[i] = stages[i][stages[i].find('\n')+1:]


# Normalize the first and last stages
stages[0] = f'RUN echo "$((53538893 & 0xFFFFFFFF))" > /0'
stages[-1] = stages[-1].split('\n')[0]


# Split the stages into blocks as the computation is done in 11 blocks
block_ops = [[]]
for op in stages:
	if '\n' in op:
		ops = op.split('\n')
		block_ops[-1].append(ops[0])
		block_ops.append([ops[1]])
	else:
		block_ops[-1].append(op)


# Define the real operations for each instruction
real_ops = {
	'mov': lambda x, y: y & 0xFFFFFFFF,
	'add': lambda x, y: (x + y) & 0xFFFFFFFF,
	'sub': lambda x, y: (x - y) & 0xFFFFFFFF,
	'mul': lambda x, y: (x * y) & 0xFFFFFFFF,
	'not': lambda x, y=None: (~x) & 0xFFFFFFFF,
	'and': lambda x, y: (x & y) & 0xFFFFFFFF,
	'or': lambda x, y: (x | y) & 0xFFFFFFFF,
	'xor': lambda x, y: (x ^ y) & 0xFFFFFFFF,
	'lsh': lambda x, y: (x << y) & 0xFFFFFFFF,
	'rsh': lambda x, y: (x >> y) & 0xFFFFFFFF,
	'rol': lambda x, y: ((x << y) | (x >> (32 - y))) & 0xFFFFFFFF,
	'ror': lambda x, y: ((x >> y) | (x << (32 - y))) & 0xFFFFFFFF,
}


# Parse the operations from the operations of the blocks
ops = []
for block in block_ops:
	ops.append(('mov', int(block[0].split('$((')[1].split(' & 0x')[0])))
	for op_str in block[1:]:
		if '+' in op_str:
			operation, value = 'add', int(op_str.split('+ ')[1].split(')')[0])
		elif '-' in op_str:
			operation, value = 'sub', int(op_str.split('- ')[1].split(')')[0])
		elif '*' in op_str:
			operation, value = 'mul', int(op_str.split('* ')[1].split(')')[0])
		elif '~' in op_str:
			operation, value = 'not', 0
		elif op_str.count('&') == 2:
			operation, value = 'and', int(op_str.split('& ')[1].split(')')[0])
		elif '|' in op_str and '<<' not in op_str:
			operation, value = 'or', int(op_str.split('| ')[1].split(')')[0])
		elif '^' in op_str:
			operation, value = 'xor', int(op_str.split('^ ')[1].split(')')[0])
		elif '<<' in op_str and '>>' not in op_str:
			operation, value = 'lsh', int(op_str.split('<< ')[1].split(')')[0])
		elif '>>' in op_str and '<<' not in op_str:
			operation, value = 'rsh', int(op_str.split('>> ')[1].split(')')[0])
		elif op_str.find('<<') < op_str.find('>>'):
			operation, value = 'rol', int(op_str.split('<< ')[1].split(')')[0])
		elif op_str.find('>>') < op_str.find('<<'):
			operation, value = 'ror', int(op_str.split('>> ')[1].split(')')[0])
		else:
			print('Invalid Operation:', op_str)
			exit(1)
		ops.append((operation, value))


# Perform a dfs bruteforce to find all possible path results, then prints only the deduplicated and ascii ones
found = set()
def dfs_brute(graph, start, x):
	# here we sum the block_idx because the last operation of each block
	# it's in the same graph node as the first operation of the next block
	op = ops[start+block_idx]
	x = real_ops[op[0]](x, op[1])

	if start >= end:
		if x not in found:
			found.add(x)
			block_bytes = x.to_bytes(4, 'big')
			if all(map(lambda x: x > 0x20 and x <= 0x7E, block_bytes)):
				print(block_bytes)
		return

	for node in graph.get(start, []):
		dfs_brute(graph, node, x)


# Runs the dsf bruteforce for each block, to get all the possible flag pieces
# for block_idx in range(0, 11):
for block_idx in range(0, BLOCKS):
	start = 21 * block_idx
	end = 21 + 21 * block_idx
	dfs_brute(g, start, 0)
	print('-----'*10)
