#include <linux/miscdevice.h>
#include <linux/mm.h>
#include <linux/vmalloc.h>
#include <linux/random.h>
#include <asm/io.h>

#define COM1 				0x3f8
#define REGN				14					// RSP, RBP are excluded

#define NPAGES				4
#define BUFF_SIZE			NPAGES*PAGE_SIZE

#define GET_MMIO			0x10

#define PRESERVE_CONTEXT 	"rax", "rbx", "rcx", "rdx", "rdi", "rsi", "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15", "rbp"
#define INVLPG(addr) 		asm volatile("invlpg (%0)" :: "r"(addr) : "memory")

#define BLOCK_SZ 			0x10
#define BLOCK_N				(BUFF_SIZE / sizeof(unsigned short)) / BLOCK_SZ

#define LCG_A 				13					// Xn+1 = (aXn + c) mod 256
#define LCG_C 				7


typedef unsigned long *user_regs;

struct entities {
	unsigned long wolf;
	unsigned long goat;
	unsigned long cabbage;
	union {
		unsigned long side;
		unsigned long empty;
	};
};

struct mmio_data {
	struct entities addr;
	struct entities regs;
};

struct rng {
	unsigned int seed;
	unsigned char target[6];
	unsigned char junk[6];
	unsigned char key;
};

static char flag[] = "TRX{p463f4u17_45_mm10}";
static char buff[BUFF_SIZE];

static struct entities state;
static struct mmio_data mmio;

unsigned char rnd = 0;

void pfh(void);				// pagefault_handler
void rsh(void);				// resched_handler

__attribute__((always_inline))
static inline void gen_mmio(void) {
	get_random_bytes(&mmio.addr.wolf, 4);
	get_random_bytes(&mmio.addr.goat, 4);
	get_random_bytes(&mmio.addr.cabbage, 4);
	get_random_bytes(&mmio.addr.empty, 4);

	mmio.regs.wolf = get_random_u32_below(REGN);
	mmio.regs.goat = get_random_u32_below(REGN);
	mmio.regs.cabbage = get_random_u32_below(REGN);
	mmio.regs.empty = get_random_u32_below(REGN);
}

__attribute__((always_inline))
static inline void die(void) {
	memset(&state, 0, sizeof(state));
	gen_mmio();
}

__attribute__((always_inline))
static inline void check_status(void) {
	gen_mmio();

	if ((state.wolf == state.goat && state.goat != state.side) || (state.goat == state.cabbage && state.goat != state.side))
		die();

	if (state.wolf + state.goat + state.cabbage == 3) {
		for (int i=0; i<strlen(flag); i++)
			outb(flag[i], COM1);
	}
}

// put them as global cuz the compiler optimizes it and doesnt set up correctly the stack frame
unsigned long cr2;
user_regs uregs;
char gdt[10];
int count;

__attribute__((always_inline))
static inline void move(void) {
	asm volatile("mov %%cr2,%0" : "=r" (cr2));

	asm volatile ("sgdt (%0)\n" :: "r" (&gdt) );

	uregs = (user_regs) ((*(unsigned long*) &gdt[2]) + 0x1f58);
	count = 0;

	if (cr2 == mmio.addr.wolf) {
		if (uregs[mmio.regs.wolf] != cr2)
			goto bad;
		
		for (int i=0; i<REGN; i++) {
			if (uregs[i] == cr2)
				count++;
		}
		if (count != 1)
			goto bad; 

		if (state.side != state.wolf)
			goto bad;
		
		state.side ^= 1;
		state.wolf ^= 1;

	} else if (cr2 == mmio.addr.goat) {
		if (uregs[mmio.regs.goat] != cr2)
			goto bad;
		
		for (int i=0; i<REGN; i++) {
			if (uregs[i] == cr2)
				count++;
		}
		if (count != 1)
			goto bad; 

		if (state.side != state.goat)
			goto bad;
		
		state.side ^= 1;
		state.goat ^= 1;

 	} else if (cr2 == mmio.addr.cabbage) {
		if (uregs[mmio.regs.cabbage] != cr2)
			goto bad;
		
		for (int i=0; i<REGN; i++) {
			if (uregs[i] == cr2)
				count++;
		}
		if (count != 1)
			goto bad; 

		if (state.side != state.cabbage)
			goto bad;
		
		state.side ^= 1;
		state.cabbage ^= 1;

	}  else if (cr2 == mmio.addr.empty) {
		if (uregs[mmio.regs.empty] != cr2)
			goto bad;
		
		for (int i=0; i<REGN; i++) {
			if (uregs[i] == cr2)
				count++;
		}
		if (count != 1)
			goto bad; 
		
		state.side ^= 1;
	} else 
		goto bad;

	return;

bad:
	die();
}

#define SAVE_CONTEXT()										\
	asm volatile(											\
		".intel_syntax noprefix\n"                          \
		"cld\n"                                             \
		"clac\n"	                                        \
		"push rbp\n"                                        \
		"push rax\n"										\
		"push rbx\n"                                        \
		"push rcx\n"                                        \
		"push rdx\n"                                        \
		"push rdi\n"                                        \
		"push rsi\n"                                        \
		"push r8\n"                                         \
		"push r9\n"                                         \
		"push r10\n"                                        \
		"push r11\n"                                        \
		"push r12\n"                                        \
		"push r13\n"                                        \
		"push r14\n"                                        \
		"push r15\n"                                        \
		"mov rax, 0xfffffe0000000000\n"						\
		"cmp rax, rsp\n"									\
		"ja 1f\n"											\
		"swapgs\n"		                                 	\
		"1:\n"												\
		".att_syntax prefix\n"                              \
		:                                                   \
		:                                                   \
		: PRESERVE_CONTEXT                                  \
	)


#define POP_CONTEXT() 										\
	asm volatile(											\
		".intel_syntax noprefix\n"                          \
		"mov rax, 0xfffffe0000000000\n"						\
		"cmp rax, rsp\n"									\
		"ja 1f\n"											\
		"swapgs\n"		                                 	\
		"1:\n"												\
		"pop r15\n"                                         \
		"pop r14\n"                                         \
		"pop r13\n"                                         \
		"pop r12\n"                                         \
		"pop r11\n"                                         \
		"pop r10\n"                                         \
		"pop r9\n"                                          \
		"pop r8\n"                                          \
		"pop rsi\n"                                         \
		"pop rdi\n"                                         \
		"pop rdx\n"                               	        \
		"pop rcx\n"                                         \
		"pop rbx\n"                                         \
		"pop rax\n"                                         \
		"pop rbp\n"                                         \
		".att_syntax prefix\n"                              \
		:                                                   \
		:                                                   \
		: PRESERVE_CONTEXT                                  \
	)

__attribute__((naked))
__attribute__((no_stack_protector))
void pfh(void) {
	SAVE_CONTEXT();

	move();

	POP_CONTEXT();

	asm volatile("jmp 0xffffffff81001280\n");

	__builtin_unreachable();
}

__attribute__((naked))
void rsh(void) {
	SAVE_CONTEXT();

	check_status();

	POP_CONTEXT();

	asm volatile("jmp 0xffffffff81001470");

	__builtin_unreachable();
}

__attribute__((always_inline))
static inline pte_t* v2p(unsigned long virtual) {
	struct mm_struct *mm = current->mm;;
	pgd_t *pgd;
	p4d_t *p4d;
	pud_t *pud;
	pmd_t *pmd;

	down_read(&mm->mmap_lock);

	pgd = pgd_offset(mm, virtual);
	if (pgd_none(*pgd) || pgd_bad(*pgd))
		goto bad;

	p4d = p4d_offset(pgd, virtual);	
	if (p4d_none(*p4d) || p4d_bad(*p4d))
		goto bad;

	pud = pud_offset(p4d, virtual);
	if (pud_none(*pud) || pud_bad(*pud))
		goto bad;

	pmd = pmd_offset(pud, virtual);
	if (pmd_none(*pmd) || pmd_bad(*pmd)){
		goto bad;
	}

	up_read(&mm->mmap_lock);
	return pte_offset_kernel(pmd, virtual);

bad:
	up_read(&mm->mmap_lock);
	return NULL;
}

__attribute__((always_inline))
static inline unsigned long get_zero_pfn(char* arg, int len) {
	pte_t* user_pte = v2p((unsigned long) arg);
	*(unsigned long*) user_pte = 0;
	INVLPG(arg);

	if (copy_from_user(&buff[len], arg, BUFF_SIZE-len))
		return -EINVAL;
	
	return (*(unsigned long*) v2p((unsigned long) arg) >> 12) & 0xffffffff;
}


static unsigned char next_lcg(unsigned char* lcg) {
	*lcg = (*lcg * LCG_A + LCG_C);
	return *lcg;
}

static void block(unsigned short* pages, unsigned int offset, struct rng* r) {
	if (offset & 0x3f) {
		for (int i=0; i<6; i+=2) {
			pages[offset + r->target[i]] = r->seed & 0xffff;
			pages[offset + r->target[i+1]] = (r->seed >> 16) & 0xffff;
		}
		
		for (int i=0; i<6; i++) {
			((char*) &pages[offset + r->junk[i]])[0] = next_lcg(&rnd);
			((char*) &pages[offset + r->junk[i]])[1] = next_lcg(&rnd);
		}
		for (int i=0; i<BLOCK_SZ*2; i++)
		((char*) &pages[offset])[i] ^= r->key;
	}

	next_lcg(&r->key);

	for (int i=0; i<6; i++) {
		r->target[i] = (r->target[i] + 1) & 0xf;
		r->junk[i] = (r->junk[i] + 1) & 0xf;
	}
}

static void not_rng(unsigned short* pages) {
	struct rng rs = {
		.seed = (unsigned int) ((unsigned long) &rsh & 0xffffffff),
		.target = {5, 8, 14, 0, 1, 4},
		.junk = {11, 12, 13, 15, 2, 3},
		.key = 139,
	};

	struct rng pf = {
		.seed = (unsigned int) ((unsigned long) &pfh & 0xffffffff),
		.target = {13, 0, 6, 8, 9, 12},
		.junk = {3, 4, 5, 7, 10, 11},
		.key = 3,
	};

	for (int bn=0; bn<BLOCK_N; bn+=2) {
		unsigned int offset =  bn * BLOCK_SZ;

		block(pages, offset, &rs);

		offset += BLOCK_SZ;

		block(pages, offset, &pf);
	}
}


static long dev_ioctl(struct file *file, unsigned int cmd, unsigned long arg) {
	if (cmd == GET_MMIO) {
		if (copy_to_user((void*) arg, (void*) &mmio, sizeof(mmio)))
			return -EINVAL;
		return 0;
	}
	
	if (copy_from_user(&buff, (void*) arg, BUFF_SIZE-1))
		return -EINVAL;

	unsigned long zero_pfn = get_zero_pfn((char*) arg, strlen(buff));
	
	struct page** pg = kvmalloc_array(NPAGES, sizeof(struct page*), __GFP_ZERO);
	for (int i=0; i<NPAGES; i++)
		pg[i] = pfn_to_page(zero_pfn+i);
	unsigned short* pages = (unsigned short*) vmap(pg, NPAGES, VM_MAP, PAGE_KERNEL);
	
	not_rng(pages);

	return 0;
}

static int dev_open(struct inode *inode, struct file *file) {
	file->private_data = NULL;
	return 0;
}

static int dev_release(struct inode *inode, struct file *file) {
	return 0;
}

static struct file_operations chall_fops = {
	.open = dev_open,
	.release = dev_release,
	.unlocked_ioctl = dev_ioctl
};

struct miscdevice chall_dev = {
	.minor = MISC_DYNAMIC_MINOR,
	.name = "faulty_road",
	.fops = &chall_fops,
};

static int __init init_dev(void) {
	if (misc_register(&chall_dev) < 0) {
		printk(KERN_INFO "[CHALL] [ERR] Failed to register device\n");
		return -1;
	}

	return 0;
}

static void __exit exit_dev(void) {
	misc_deregister(&chall_dev);
}

module_init(init_dev);
module_exit(exit_dev);

MODULE_AUTHOR("leave");
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("TRXCTF 2026");
