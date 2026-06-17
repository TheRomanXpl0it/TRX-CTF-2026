#include <stdio.h>

typedef unsigned int u32;

u32 blocks[] = {
	0x0a1b2c3d, // original seed
	0x2826264,
	0x372f09b9,
	0xa3cb52cf,
	0x76846083,
	0x6b5946b8,
	0x8ac24a53,
	0xddef4b23,
	0x811cd4b8,
	0x825fdfd8,
	0x8ff66ead,
	0x88a802a5,
	0x7703c946,
	0x5caa31c5,
	0x88f66426,
	0x955e92fb,
	0x664927b7,
	0xd24e908c,
	0xa5313f9e,
	0x6bf08e0c,
	0xba92690e,
	0xea3d98e9,
	0xdee7fcf0,
	0x5197b1f3,
	0x31d42f22,
	0x6bbea1ba,
	0xec8500a9,
	0x37806f42,
	0xed701688,
	0x60918bd8,
	0xf8a48263,
	0x9739f77f,
	0x6fe6a62c,
};

#define CONST 0x01013255

int main() {
	for (int i = 0; i < (sizeof(blocks) / sizeof(blocks[0])); i++) {
		u32 seed = blocks[i];
		for (u32 c0 = 0; c0 < 0x100; c0++) {
			u32 h0 = seed;
			h0 *= CONST;
			h0 ^= c0;
			for (u32 c1 = 0; c1 < 0x100; c1++) {
				u32 h1 = h0 * CONST;
				h1 ^= c1;
				for (u32 c2 = 0; c2 < 0x100; c2++) {
					u32 h2 = h1 * CONST;
					h2 ^= c2;
					for (u32 c3 = 0; c3 < 0x100; c3++) {
						u32 h3 = h2 * CONST;
						h3 ^= c3;

						if (h3 == blocks[i+1]) {
							printf("%d, 0x%02x, 0x%02x, 0x%02x, 0x%02x,\n", i, c0, c1, c2, c3);
						}
					}
				}
			}
		}
	}
}