#include "slop.h"
#include <string.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <stdbool.h>
#include <stdio.h>

struct slop_cache slop_caches[SLOP_CACHES];
struct page all_pages[ALLOCABLE_PAGES];
uint32_t page_allocated = 0;
uint8_t bitmap[ALLOCABLE_PAGES / 8];
void *base_memory;

static void panic(const char* msg)
{
    printf("%s\n", msg);
    exit(1);
}

static void list_init(struct list_head *entry)
{
    entry->next = entry;
    entry->prev = entry;
}

static void list_del(struct list_head *entry)
{
    if (entry->prev)
        entry->prev->next = entry->next;

    if (entry->next)
        entry->next->prev = entry->prev;
}

static void list_add_tail(struct list_head *head, struct list_head *new)
{
    new->next = head;
    new->prev = head->prev;
    head->prev->next = new;
    head->prev = new;
}

static struct page *list_first_entry(struct list_head *head)
{
    return container_of(head->next, struct page, list);
}

static bool list_empty(struct list_head *entry)
{
    return entry == entry->next;
}

static struct page *addr_to_page(void *addr)
{
    void *base = (void *)((uint64_t)addr & ~(PAGE_SIZE - 1));
    uint32_t idx = (addr - base_memory) >> PAGE_ZEROS;

    if (idx >= ALLOCABLE_PAGES)
        panic("Invalid address, can't convert to page pointer");

    return &all_pages[idx];
}

static inline bool bitmap_lookup(uint32_t idx)
{
    uint32_t arr_idx = idx >> PAGE_SHIFT;
    if (arr_idx >= ALLOCABLE_PAGES)
        panic("Exceeded bitmap len!");

    uint8_t tmp_idx = idx & PAGE_MASK;

    uint8_t tmp = bitmap[arr_idx];

    return (tmp >> (PAGE_MASK - tmp_idx)) & 1;
}

static inline void bitmap_set(uint32_t idx)
{
    uint32_t arr_idx = idx >> PAGE_SHIFT;
    if (arr_idx >= ALLOCABLE_PAGES)
        panic("Exceeded bitmap len!");

    uint8_t tmp_idx = idx & PAGE_MASK;

    uint8_t new = 1 << (PAGE_MASK - tmp_idx);
    bitmap[arr_idx] |= new;
}

static inline void bitmap_del(uint32_t idx)
{
    uint32_t arr_idx = idx >> PAGE_SHIFT;
    if (arr_idx >= ALLOCABLE_PAGES)
        panic("Exceeded bitmap len!");

    uint8_t tmp_idx = idx & PAGE_MASK;

    uint8_t new = 1 << (PAGE_MASK - tmp_idx);
    bitmap[arr_idx] &= ~new;
}

static struct page *page_alloc()
{   
    if (page_allocated >= ALLOCABLE_PAGES)
        panic("We are out of memory!");

    uint32_t idx = 0;

    for (size_t i = 0; i < ALLOCABLE_PAGES; i++)
        if (!bitmap_lookup(i)) {
            idx = i;
            break;
        }

    struct page *p = &all_pages[idx];
    bitmap_set(idx);
    page_allocated++;

    return p;
}

static void page_free(struct page *p)
{
    uint32_t idx = (p->start - base_memory) >> PAGE_ZEROS;
    bitmap_del(idx);

    p->free_list = NULL;
    p->back = NULL;
    page_allocated--;
}

static void slop_page_init(struct slop_cache *cache, struct page *p)
{
    list_init(&p->list);

    size_t obj_size = cache->size;
    uintptr_t start = (uintptr_t)p->start;
    uintptr_t ptr = start + PAGE_SIZE - obj_size;

    struct slobject *next = NULL;
    uint32_t count = 1;
    while (ptr >= start) {
        struct slobject *obj = (struct slobject *)ptr;
        obj->next_free = next;
        obj->count = count++;
        next = (struct slobject *)ptr;
        ptr -= obj_size;
    }

    p->back = cache;
    p->free_list = (struct slobject *)start;
}

static void slop_cache_init(struct slop_cache *slop_cache, size_t order)
{
    slop_cache->size = 1 << order;
    slop_cache->allocated_slobject = 0;
    slop_cache->allocated_slop = 1;
    slop_cache->full_count = 0;
    slop_cache->ready_count = 0;

    list_init(&slop_cache->full_list);
    list_init(&slop_cache->ready_list);

    struct page *p = page_alloc();
    slop_cache->active = p;
    slop_page_init(slop_cache, p);
}

static inline uint64_t next_power_of_2(size_t n)
{
    if (n <= 1)
        return 1;
    n--;
    n |= n >> 1;
    n |= n >> 2;
    n |= n >> 4;
    n |= n >> 8;
    n |= n >> 16;
    n |= n >> 32;
    return n + 1;
}

static inline size_t get_order(size_t n)
{
    if (n == 0)
        return 0;
    return __builtin_ctzll(n);
}

static void free_slop_obj(struct slobject *obj, struct slobject **free_list)
{
    size_t size = container_of(free_list, struct page, free_list)->back->size;
    memset(obj, 0, size);
    obj->count = *free_list ? (*free_list)->count + 1 : 1;
    obj->next_free = *free_list;
    *free_list = obj;
}

static void *alloc_slop_obj(struct slop_cache *cache, struct slobject **free_list)
{
    struct slobject *obj = *free_list;
    *free_list = obj->next_free;
    cache->allocated_slobject++;
    return obj;
}

void slop_init()
{
    base_memory = mmap(0, ALLOCABLE_PAGES * PAGE_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANON, -1, 0);

    if (base_memory == (void *)-1)
        panic("Mmap failed!");

    for (size_t i = 0; i < ALLOCABLE_PAGES; i++)
        all_pages[i].start = base_memory + (i * PAGE_SIZE);

    for (size_t i = 0; i < SLOP_CACHES; i++) 
        slop_cache_init(&slop_caches[i], SLOP_MAX_ORDER - i);
}

static void *slop_cache_alloc(struct slop_cache *slop_cache)
{
    struct page *slop = slop_cache->active;
    if (!slop)
        panic("There is no active slop, maybe we ran out of memory!");

    struct slobject *obj = slop->free_list;
    if (obj) {
        obj = alloc_slop_obj(slop_cache, &slop->free_list);
        return (void *)obj;
    }

    list_add_tail(&slop_cache->full_list, &slop->list);
    slop_cache->full_count++;

    struct page *new_slop;
    if (!list_empty(&slop_cache->ready_list)) {
        new_slop = list_first_entry(&slop_cache->ready_list);
        list_del(&new_slop->list);

        slop_cache->ready_count--;
        slop_cache->active = new_slop;
        list_init(&new_slop->list);

        if (!new_slop->free_list) {
            printf("SLOP=%p N_OBJS=%u\n", new_slop->start, slop_cache->allocated_slobject);
            panic("Slop in ready list was full!");
        }

        obj = alloc_slop_obj(slop_cache, &new_slop->free_list);
        return (void *)obj;
    }

    new_slop = page_alloc();
    slop_page_init(slop_cache, new_slop);

    slop_cache->allocated_slop++;
    slop_cache->active = new_slop;

    obj = alloc_slop_obj(slop_cache, &new_slop->free_list);
    return (void *)obj;
}

void *slop_alloc(size_t size)
{
    size_t new_size = next_power_of_2(size);
    size_t order = get_order(new_size);

    if (order > SLOP_MAX_ORDER)
        return NULL;

    if (order < SLOP_MIN_ORDER)
        order = SLOP_MIN_ORDER;

    struct slop_cache *slop_cache = &slop_caches[SLOP_MAX_ORDER - order];

    return slop_cache_alloc(slop_cache);
}

void slop_free(void *ptr)
{
    struct slobject *obj = (struct slobject *)ptr;
    struct page *slop = addr_to_page(ptr);

    struct slop_cache *slop_cache = slop->back;

    if (!slop_cache->allocated_slobject)
        panic("Tried to free empty slop!");

    if (!slop->free_list) {
        list_del(&slop->list);
        slop_cache->full_count--;

        free_slop_obj(obj, &slop->free_list);
        slop_cache->allocated_slobject--;

        list_add_tail(&slop_cache->ready_list, &slop->list);
        slop_cache->ready_count++;
    } else {
        free_slop_obj(obj, &slop->free_list);
        slop_cache->allocated_slobject--;
    }

    if (slop != slop_cache->active) {
        uint32_t free_objs = slop->free_list->count;
        uint32_t max_objs = PAGE_SIZE / slop_cache->size;

        if (free_objs == max_objs && slop_cache->ready_count >= SLOP_READY_THRESHOLD) {
            list_del(&slop->list);
            slop_cache->ready_count--;

            slop_cache->allocated_slop--;
            page_free(slop);
        }
    }
}
