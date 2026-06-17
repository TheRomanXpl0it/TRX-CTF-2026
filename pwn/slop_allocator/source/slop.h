#include <stdint.h>
#include <stddef.h> 

#define SLOP_MAX_ORDER 12
#define SLOP_MIN_ORDER 4

#define SLOP_MAX_SIZE (1ULL << SLOP_MAX_ORDER)
#define SLOP_CACHES (SLOP_MAX_ORDER - SLOP_MIN_ORDER + 1)
#define SLOP_READY_THRESHOLD 3
#define PAGE_SIZE 0x1000
#define PAGE_SHIFT 3
#define PAGE_MASK ((1 << PAGE_SHIFT) - 1)
#define PAGE_ZEROS 12
#define ALLOCABLE_PAGES 0x1000

#define container_of(ptr, type, member) \
    ((type *)((char *)(ptr) - offsetof(type, member)))

struct list_head {
    struct list_head *next;
    struct list_head *prev;
};

struct slop_cache {
    size_t size;
    struct page *active;
    struct list_head ready_list;
    struct list_head full_list;
    uint32_t allocated_slobject;
    uint32_t allocated_slop;
    uint32_t full_count;
    uint32_t ready_count;
};

struct slobject {
    struct slobject *next_free;
    uint32_t count;
};

struct page {
    void *start;
    struct list_head list;
    struct slop_cache *back;
    struct slobject *free_list;
};

extern struct slop_cache slop_caches[SLOP_CACHES];

void slop_init();

void *slop_alloc(size_t size);

void slop_free(void *ptr);
