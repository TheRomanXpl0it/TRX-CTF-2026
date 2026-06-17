import random

random.seed(1337)

FLAG = 'TRX{t0_Mak3_lLm5_go_cr4zY_0n_th1s_Chall3nGe_i_hAd_To_g3neRat3_tHi5_fLag_l1k3_4_p0Em_onLy_tO_m4kE_it_vErY_VeRy_l0ng_so_ThaT_maYb3_th3y_would_Not_b3_aBLe_TO_r3c0v3r_1t_oN3_sh0t_AnD_nOt_BrUtE_forc3_1t!!}'

# the DAGs for each block, each block has 21 operations,
# and the last one is always 'xor' with the flag piece,
# so we have 20 operations to obfuscate the flag piece
dags = [
	[(0, 1), (0, 2), (1, 3), (1, 5), (1, 4), (2, 3), (3, 6), (3, 7), (4, 7), (4, 6), (5, 7), (5, 6), (6, 9), (6, 8), (7, 9), (7, 8), (8, 12), (8, 10), (8, 11), (9, 10), (9, 12), (9, 11), (10, 13), (11, 14), (12, 14), (12, 13), (13, 15), (13, 16), (14, 15), (14, 17), (14, 16), (15, 18), (15, 19), (15, 20), (16, 19), (17, 19), (18, 21), (19, 21), (20, 21)],
	[(0, 1), (0, 2), (0, 3), (1, 5), (1, 4), (2, 4), (2, 5), (3, 4), (4, 7), (4, 6), (4, 8), (5, 7), (5, 6), (6, 9), (6, 10), (7, 9), (7, 10), (8, 10), (8, 9), (9, 12), (9, 13), (9, 11), (10, 12), (11, 15), (11, 14), (12, 14), (13, 15), (13, 14), (14, 17), (14, 16), (14, 18), (15, 18), (15, 17), (15, 16), (16, 19), (16, 20), (17, 19), (17, 20), (18, 20), (18, 19), (19, 21), (20, 21)],
	[(0, 1), (0, 2), (1, 5), (1, 4), (2, 3), (2, 5), (2, 4), (3, 7), (3, 8), (3, 6), (4, 6), (4, 7), (4, 8), (5, 7), (6, 10), (7, 10), (7, 9), (8, 9), (8, 10), (9, 13), (10, 12), (10, 11), (10, 13), (11, 15), (11, 14), (12, 14), (12, 15), (13, 15), (13, 14), (14, 16), (14, 17), (15, 16), (15, 17), (16, 20), (16, 18), (17, 19), (17, 20), (18, 21), (19, 21), (20, 21)],
	[(0, 1), (0, 2), (0, 3), (1, 4), (1, 6), (1, 5), (2, 6), (3, 6), (3, 4), (4, 8), (4, 7), (5, 7), (5, 8), (6, 8), (6, 7), (7, 10), (7, 9), (8, 10), (8, 9), (9, 12), (9, 11), (9, 13), (10, 12), (11, 15), (11, 14), (12, 14), (12, 15), (13, 15), (13, 14), (14, 16), (14, 17), (15, 16), (15, 17), (16, 19), (16, 18), (16, 20), (17, 19), (17, 20), (17, 18), (18, 21), (19, 21), (20, 21)],
	[(0, 1), (0, 2), (1, 3), (1, 4), (2, 3), (3, 5), (4, 7), (4, 5), (4, 6), (5, 8), (5, 9), (5, 10), (6, 8), (6, 9), (6, 10), (7, 10), (8, 13), (8, 12), (9, 11), (9, 13), (9, 12), (10, 11), (10, 12), (11, 14), (12, 14), (12, 15), (12, 16), (13, 15), (13, 14), (13, 16), (14, 17), (14, 18), (15, 18), (15, 17), (16, 17), (17, 19), (18, 20), (18, 19), (19, 21), (20, 21)],
	[(0, 1), (0, 2), (0, 3), (1, 6), (1, 5), (1, 4), (2, 5), (2, 6), (2, 4), (3, 6), (4, 7), (4, 8), (5, 7), (5, 8), (6, 7), (7, 9), (7, 10), (8, 10), (8, 9), (9, 13), (9, 11), (9, 12), (10, 13), (10, 11), (11, 16), (11, 14), (11, 15), (12, 14), (12, 15), (12, 16), (13, 14), (13, 15), (13, 16), (14, 17), (14, 18), (15, 17), (15, 18), (16, 18), (16, 17), (17, 19), (17, 20), (18, 20), (19, 21), (20, 21)],
	[(0, 1), (0, 2), (0, 14), (1, 3), (1, 4), (1, 5), (2, 5), (2, 4), (3, 6), (3, 7), (4, 6), (4, 7), (5, 6), (5, 7), (6, 8), (6, 9), (7, 8), (7, 9), (8, 12), (8, 11), (8, 10), (9, 12), (9, 10), (9, 11), (10, 15), (10, 13), (11, 15), (12, 15), (13, 16), (13, 18), (13, 17), (14, 18), (14, 17), (15, 17), (15, 18), (16, 19), (16, 20), (17, 19), (17, 20), (18, 20), (18, 19), (19, 21), (20, 21)],
	[(0, 1), (0, 2), (0, 3), (1, 5), (1, 4), (1, 6), (2, 5), (2, 6), (2, 4), (3, 5), (4, 8), (4, 7), (5, 7), (5, 8), (6, 7), (6, 8), (7, 11), (7, 9), (7, 10), (8, 10), (8, 9), (8, 11), (9, 12), (9, 14), (9, 13), (10, 13), (11, 12), (11, 14), (12, 18), (13, 17), (13, 15), (13, 16), (13, 18), (14, 18), (14, 17), (15, 19), (15, 20), (16, 20), (16, 19), (17, 20), (17, 19), (18, 19), (19, 21), (20, 21)],
	[(0, 1), (0, 2), (0, 3), (1, 4), (1, 5), (1, 6), (2, 4), (3, 5), (3, 6), (3, 4), (4, 8), (5, 9), (5, 8), (5, 7), (6, 7), (6, 8), (6, 9), (7, 12), (7, 11), (7, 10), (8, 12), (9, 10), (10, 14), (11, 15), (11, 13), (11, 14), (12, 13), (13, 18), (13, 16), (13, 17), (14, 18), (14, 16), (15, 16), (15, 17), (15, 18), (16, 20), (16, 19), (17, 19), (18, 19), (18, 20), (19, 21), (20, 21)],
	[(0, 1), (0, 2), (1, 5), (1, 3), (1, 4), (2, 3), (3, 8), (4, 8), (4, 7), (4, 6), (5, 8), (5, 7), (5, 6), (6, 10), (6, 11), (6, 9), (7, 10), (7, 11), (7, 9), (8, 10), (8, 11), (9, 12), (9, 13), (9, 14), (10, 13), (10, 12), (11, 14), (11, 12), (11, 13), (12, 17), (12, 16), (13, 15), (13, 16), (13, 17), (14, 15), (14, 17), (15, 20), (15, 19), (15, 18), (16, 18), (16, 20), (17, 18), (17, 19), (17, 20), (18, 21), (19, 21), (20, 21)],
	[(0, 1), (0, 2), (0, 3), (0, 4), (0, 11), (0, 13), (1, 5), (2, 7), (3, 5), (3, 6), (4, 6), (4, 5), (4, 7), (5, 8), (5, 9), (6, 8), (7, 8), (8, 10), (9, 10), (10, 12), (11, 15), (11, 17), (11, 16), (11, 14), (12, 17), (12, 16), (12, 14), (13, 15), (13, 14), (14, 18), (14, 20), (14, 19), (15, 18), (15, 20), (15, 19), (16, 19), (16, 18), (16, 20), (17, 18), (17, 19), (17, 20), (18, 21), (19, 21), (20, 21)]
]

dags *= 20
dags = dags[:50]
random.shuffle(dags)

# the operations to chose from with their bash implementation
ops = {
	'add': lambda x, y: f'$((($(</{x}) + {y}) & 0xFFFFFFFF))',
	'sub': lambda x, y: f'$((($(</{x}) - {y}) & 0xFFFFFFFF))',
	'mul': lambda x, y: f'$((($(</{x}) * {y}) & 0xFFFFFFFF))',
	'not': lambda x, y: f'$(((~$(</{x})) & 0xFFFFFFFF))',
	'and': lambda x, y: f'$((($(</{x}) & {y}) & 0xFFFFFFFF))',
	'or': lambda x, y: f'$((($(</{x}) | {y}) & 0xFFFFFFFF))',
	'xor': lambda x, y: f'$((($(</{x}) ^ {y}) & 0xFFFFFFFF))',
	'lsh': lambda x, y: f'$((($(</{x}) << {y}) & 0xFFFFFFFF))',
	'rsh': lambda x, y: f'$((($(</{x}) >> {y}) & 0xFFFFFFFF))',
	'rol': lambda x, y: f'$(((($(</{x}) << {y}) | ($(</{x}) >> {32 - y})) & 0xFFFFFFFF))',
	'ror': lambda x, y: f'$(((($(</{x}) >> {y}) | ($(</{x}) << {32 - y})) & 0xFFFFFFFF))',
}

# the operations to chose from but in python (to future compute)
real_ops = {
	# 'mov': lambda x, y: y,

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

# chose one random operation and a random value for it
def random_op():
	op = random.choice(list(ops.keys()))
	if op in ("rol", "ror"):
		value = random.randint(1, 31)
	else:
		value = random.getrandbits(32)
	return op, value


# Generate a random path from the DAG
def random_path(graph, start, visited):
	visited.append(start)
	if start == 21:
		return
	next_node = random.choice(graph.get(start, []))
	random_path(graph, next_node, visited)


def gen_from_dag(dag, flag_block):
	# builds the graph from the DAG
	g = {}
	for e in dag:
		start, to = e[0], e[1]
		g[start] = g.get(start, []) + [to]

	# generates a random path from the graph
	path = []
	random_path(g, 0, path)

	# builds the list of operations, plus an initial seed
	X = random.getrandbits(32)
	operations = \
		[('mov', X)] + \
		[random_op() for _ in range(20)] + \
		[('xor', 0)]

	# computes the the last value after each step of the path
	# to get the correct value for the last operation (xor with the flag piece)
	for p in path[1:]:
		op, value = operations[p]
		X = real_ops[op](X, value)
	operations[-1] = ('xor', flag_block ^ X)

	return path, operations


# generates the blocks of operations for each flag piece
all_operations = []
for i, dag in enumerate(dags):
	flag_block = int.from_bytes(FLAG[i*4:(i+1)*4].encode(), 'big')
	path, operations = gen_from_dag(dag, flag_block)
	all_operations.append(operations)


# completes the operations by adding the block_idx to each operation
layers = [[]]
for i, dag in enumerate(dags):
	operations = all_operations[i]
	for j, (op, value) in enumerate(operations):
		if j != 0:
			layers.append([(op, i, value)])
		else:
			layers[-1].append((op, i, value))


# joins the graphs of each block
g = {}
for i, dag in enumerate(dags):
	for edge in dag:
		start, to = edge[0]+i*21, edge[1]+i*21
		g[to] = g.get(to, []) + [start]


# verify that no cycle is present in the graph
for (curr, prevs) in g.items():
	for prev in prevs:
		assert prev < curr, f'{prev} should be less than {curr}'


# add the mov operation to the ops dict to not make it selectable before,
# and to be able to use it to initialize the blocks
ops['mov'] = lambda x, y: f'$(({y} & 0xFFFFFFFF))'


# generate the stages of the dockerfile,
# each stage will compute one operation of the graph,
# and copy the previous stages if needed
max_block_idx = layers[-1][0][1]
for i, operations in enumerate(layers):
	L = f'FROM alpine-bash AS l{i}\n'

	(op, block_idx, value) = operations[0]
	for prev in g.get(i, []):
		for idx in range(max_block_idx+1):
			L += f'COPY --from=l{prev} /{idx} /{idx}\n'

	
	for (op, block_idx, value) in operations:
		L +=f'RUN echo "{ops[op](block_idx, value)}" > /{block_idx}\n'
	if i == 0:
		for j in range(1, max_block_idx+1):
			L +=f'RUN echo "{ops["mov"](j, 0)}" > /{j}\n'
	
	L += '\n'
	print(L)


# Finally, we print the command to run the last stage and get the flag
format = "%.8x"*max_block_idx
inputs = " ".join([f"$(</{i})" for i in range(max_block_idx+1)])
print(f'CMD ["bash", "-c", "printf \'0: {format}\', {inputs} | xxd -r -g0"]')


if False: # Enable to visualize the graph
	g = {}
	edges = []
	for i, es in enumerate(dags):
		for e in es:
			start, to = e[0]+i*21, e[1]+i*21
			g[start] = g.get(start, []) + [to]
			edges.append((start, to))

	from pyvis.network import Network
	net = Network(notebook = True, cdn_resources = "remote",
					bgcolor = "#222222",
					font_color = "white",
					height = "750px",
					width = "100%",
	)
	net.add_nodes(list(range((21 * 10)+1)))
	net.add_edges(edges)
	net.show("graph.html")
