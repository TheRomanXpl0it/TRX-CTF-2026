#ifndef BYTECODE_VM_H
#define BYTECODE_VM_H

#include <stdint.h>
#include <stddef.h>

/* Bytecode Instruction Set */
typedef enum {
    /* Stack operations */
    OP_PUSH_IMM   = 0x01,  /* Push immediate value: arg1, arg2 (little-endian double) */
    OP_POP        = 0x02,  /* Pop from stack */
    OP_DUP        = 0x03,  /* Duplicate top of stack */
    
    /* Memory operations */
    OP_LOAD_REG   = 0x04,  /* Load from register to stack: reg_id */
    OP_STORE_REG  = 0x05,  /* Store stack top to register: reg_id */
    OP_LOAD_MEM   = 0x06,  /* Load from memory: addr (from stack) */
    OP_STORE_MEM  = 0x07,  /* Store to memory: addr (from stack) */
    
    /* Arithmetic */
    OP_ADD        = 0x08,  /* Pop two, push result */
    OP_MUL        = 0x09,
    OP_SUB        = 0x0A,
    OP_DIV        = 0x0B,
    OP_NEG        = 0x0C,  /* Negate top */
    
    /* Matrix operations */
    OP_MAT_INIT_IDENTITY = 0x10,  /* Initialize NxN identity matrix: mat_id, N */
    OP_MAT_SET   = 0x11,  /* Set matrix element: mat_id, i, j (values from stack) */
    OP_MAT_GET   = 0x12,  /* Get matrix element: mat_id, i, j (push to stack) */
    OP_MAT_MUL   = 0x13,  /* Multiply matrices: dest, src1, src2 */
    OP_MAT_TRANS = 0x14,  /* Transpose matrix: dest, src */
    OP_MAT_CMP   = 0x15,  /* Compare matrices (push 1 if equal, 0 if not): mat1, mat2, N */
    
    /* Control flow */
    OP_JMP        = 0x20,  /* Jump to offset */
    OP_JNE        = 0x21,  /* Jump if not equal (pop two, compare) */
    OP_JEQ        = 0x22,  /* Jump if equal */
    
    /* I/O and special */
    OP_READ_FLAG  = 0x30,  /* Read flag from input into register: reg_id, max_len */
    OP_PUSH_FLAG_CHAR = 0x31,  /* Push flag[index]: index from stack */
    OP_FLAG_LEN   = 0x32,  /* Push flag length */
    
    /* Comparison and logic */
    OP_CMP        = 0x40,  /* Compare stack top two values, push result */
    OP_EQ         = 0x41,  /* Check equality, push bool */
    OP_LT         = 0x42,
    OP_GT         = 0x43,
    
    /* Special */
    OP_NOP        = 0x00,  /* No operation */
    OP_EXIT       = 0xFF,  /* Exit with code from stack */
} BytecodeOp;

#define NUM_REGS 16
#define STACK_SIZE 256
#define NUM_MATRICES 8
#define MATRIX_DIM 9
#define FLAG_MAX_LEN 256
#define MEM_SIZE 4096

typedef struct {
    // Stack
    double stack[STACK_SIZE];
    int sp;  // Stack pointer
    
    // Registers (general purpose)
    double regs[NUM_REGS];
    
    // Matrices (pre-allocated dense storage)
    double matrices[NUM_MATRICES][MATRIX_DIM][MATRIX_DIM];
    
    // Memory (for additional data)
    double memory[MEM_SIZE];
    
    // Flag input
    char flag[FLAG_MAX_LEN];
    int flag_len;
    
    // Execution state
    const uint8_t *bytecode;
    size_t bytecode_len;
    size_t pc;  // Program counter
    int running;
    int exit_code;
} BytecodeVM;

/* VM Functions */
BytecodeVM* vm_create(void);
void vm_destroy(BytecodeVM *vm);
void vm_set_bytecode(BytecodeVM *vm, const uint8_t *code, size_t len);
void vm_set_flag(BytecodeVM *vm, const char *flag);
int vm_execute(BytecodeVM *vm);
void vm_reset(BytecodeVM *vm);

#endif
