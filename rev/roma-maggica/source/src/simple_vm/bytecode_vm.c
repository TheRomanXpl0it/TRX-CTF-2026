#include "bytecode_vm.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>

BytecodeVM* vm_create(void) {
    BytecodeVM *vm = (BytecodeVM *)calloc(1, sizeof(BytecodeVM));
    if (!vm) return NULL;
    
    vm->sp = 0;
    vm->pc = 0;
    vm->running = 0;
    vm->exit_code = 0;
    
    return vm;
}

void vm_destroy(BytecodeVM *vm) {
    if (vm) free(vm);
}

void vm_set_bytecode(BytecodeVM *vm, const uint8_t *code, size_t len) {
    vm->bytecode = code;
    vm->bytecode_len = len;
    vm->pc = 0;
}

void vm_set_flag(BytecodeVM *vm, const char *flag) {
    strncpy(vm->flag, flag, FLAG_MAX_LEN - 1);
    vm->flag[FLAG_MAX_LEN - 1] = '\0';
    vm->flag_len = strlen(vm->flag);
}

void vm_reset(BytecodeVM *vm) {
    vm->sp = 0;
    vm->pc = 0;
    memset(vm->regs, 0, sizeof(vm->regs));
    memset(vm->stack, 0, sizeof(vm->stack));
    memset(vm->memory, 0, sizeof(vm->memory));
    memset(vm->matrices, 0, sizeof(vm->matrices));
}

#define EPSILON 1e-9

static inline double peek_stack(BytecodeVM *vm) {
    if (vm->sp > 0) return vm->stack[vm->sp - 1];
    return 0.0;
}

static inline void push_stack(BytecodeVM *vm, double val) {
    if (vm->sp < STACK_SIZE) {
        vm->stack[vm->sp++] = val;
    }
}

static inline double pop_stack(BytecodeVM *vm) {
    if (vm->sp > 0) {
        return vm->stack[--vm->sp];
    }
    return 0.0;
}

static inline uint8_t read_byte(BytecodeVM *vm) {
    if (vm->pc < vm->bytecode_len) {
        return vm->bytecode[vm->pc++];
    }
    return 0;
}

static inline uint32_t read_u32(BytecodeVM *vm) {
    uint32_t val = 0;
    val |= (uint32_t)read_byte(vm) << 0;
    val |= (uint32_t)read_byte(vm) << 8;
    val |= (uint32_t)read_byte(vm) << 16;
    val |= (uint32_t)read_byte(vm) << 24;
    return val;
}

static inline double read_double(BytecodeVM *vm) {
    uint64_t bits = 0;
    for (int i = 0; i < 8; i++) {
        bits |= ((uint64_t)read_byte(vm)) << (i * 8);
    }
    double *p = (double *)&bits;
    return *p;
}

static void matrix_multiply(double A[MATRIX_DIM][MATRIX_DIM],
                           double B[MATRIX_DIM][MATRIX_DIM],
                           double C[MATRIX_DIM][MATRIX_DIM]) {
    double temp[MATRIX_DIM][MATRIX_DIM];
    memset(temp, 0, sizeof(temp));
    
    for (int i = 0; i < MATRIX_DIM; i++) {
        for (int j = 0; j < MATRIX_DIM; j++) {
            for (int k = 0; k < MATRIX_DIM; k++) {
                temp[i][j] += A[i][k] * B[k][j];
            }
        }
    }
    
    memcpy(C, temp, sizeof(temp));
}

static void matrix_transpose(double A[MATRIX_DIM][MATRIX_DIM],
                            double B[MATRIX_DIM][MATRIX_DIM]) {
    for (int i = 0; i < MATRIX_DIM; i++) {
        for (int j = 0; j < MATRIX_DIM; j++) {
            B[i][j] = A[j][i];
        }
    }
}

static int matrices_equal(double A[MATRIX_DIM][MATRIX_DIM],
                         double B[MATRIX_DIM][MATRIX_DIM]) {
    for (int i = 0; i < MATRIX_DIM; i++) {
        for (int j = 0; j < MATRIX_DIM; j++) {
            if (fabs(A[i][j] - B[i][j]) > EPSILON) {
                return 0;
            }
        }
    }
    return 1;
}

int vm_execute(BytecodeVM *vm) {
    vm->running = 1;
    vm->exit_code = 0;
    
    while (vm->running && vm->pc < vm->bytecode_len) {
        uint8_t op = read_byte(vm);
        
        switch (op) {
            case OP_NOP:
                break;
                
            case OP_PUSH_IMM: {
                double val = read_double(vm);
                push_stack(vm, val);
                break;
            }
            
            case OP_POP:
                pop_stack(vm);
                break;
                
            case OP_DUP: {
                double val = peek_stack(vm);
                push_stack(vm, val);
                break;
            }
            
            case OP_LOAD_REG: {
                uint8_t reg = read_byte(vm);
                if (reg < NUM_REGS) {
                    push_stack(vm, vm->regs[reg]);
                }
                break;
            }
            
            case OP_STORE_REG: {
                uint8_t reg = read_byte(vm);
                if (reg < NUM_REGS) {
                    vm->regs[reg] = pop_stack(vm);
                }
                break;
            }
            
            case OP_ADD: {
                double b = pop_stack(vm);
                double a = pop_stack(vm);
                push_stack(vm, a + b);
                break;
            }
            
            case OP_MUL: {
                double b = pop_stack(vm);
                double a = pop_stack(vm);
                push_stack(vm, a * b);
                break;
            }
            
            case OP_SUB: {
                double b = pop_stack(vm);
                double a = pop_stack(vm);
                push_stack(vm, a - b);
                break;
            }
            
            case OP_DIV: {
                double b = pop_stack(vm);
                double a = pop_stack(vm);
                if (fabs(b) > EPSILON) {
                    push_stack(vm, a / b);
                } else {
                    push_stack(vm, 0.0);
                }
                break;
            }
            
            case OP_NEG: {
                double a = pop_stack(vm);
                push_stack(vm, -a);
                break;
            }
            
            case OP_MAT_INIT_IDENTITY: {
                uint8_t mat_id = read_byte(vm);
                uint8_t n = read_byte(vm);
                if (mat_id < NUM_MATRICES && n <= MATRIX_DIM) {
                    for (int i = 0; i < MATRIX_DIM; i++) {
                        for (int j = 0; j < MATRIX_DIM; j++) {
                            vm->matrices[mat_id][i][j] = (i == j && i < n) ? 1.0 : 0.0;
                        }
                    }
                }
                break;
            }
            
            case OP_MAT_SET: {
                uint8_t mat_id = read_byte(vm);
                uint8_t i = read_byte(vm);
                uint8_t j = read_byte(vm);
                double val = pop_stack(vm);
                if (mat_id < NUM_MATRICES && i < MATRIX_DIM && j < MATRIX_DIM) {
                    vm->matrices[mat_id][i][j] = val;
                }
                break;
            }
            
            case OP_MAT_GET: {
                uint8_t mat_id = read_byte(vm);
                uint8_t i = read_byte(vm);
                uint8_t j = read_byte(vm);
                if (mat_id < NUM_MATRICES && i < MATRIX_DIM && j < MATRIX_DIM) {
                    push_stack(vm, vm->matrices[mat_id][i][j]);
                } else {
                    push_stack(vm, 0.0);
                }
                break;
            }
            
            case OP_MAT_MUL: {
                uint8_t dest = read_byte(vm);
                uint8_t src1 = read_byte(vm);
                uint8_t src2 = read_byte(vm);
                if (dest < NUM_MATRICES && src1 < NUM_MATRICES && src2 < NUM_MATRICES) {
                    matrix_multiply(vm->matrices[src1], vm->matrices[src2], 
                                   vm->matrices[dest]);
                }
                break;
            }
            
            case OP_MAT_TRANS: {
                uint8_t dest = read_byte(vm);
                uint8_t src = read_byte(vm);
                if (dest < NUM_MATRICES && src < NUM_MATRICES) {
                    matrix_transpose(vm->matrices[src], vm->matrices[dest]);
                }
                break;
            }
            
            case OP_MAT_CMP: {
                uint8_t mat1 = read_byte(vm);
                uint8_t mat2 = read_byte(vm);
                if (mat1 < NUM_MATRICES && mat2 < NUM_MATRICES) {
                    int result = matrices_equal(vm->matrices[mat1], vm->matrices[mat2]);
                    push_stack(vm, result ? 1.0 : 0.0);
                } else {
                    push_stack(vm, 0.0);
                }
                break;
            }
            
            case OP_JMP: {
                uint32_t offset = read_u32(vm);
                vm->pc = offset;
                break;
            }
            
            case OP_JNE: {
                uint32_t offset = read_u32(vm);
                double b = pop_stack(vm);
                double a = pop_stack(vm);
                if (fabs(a - b) > EPSILON) {
                    vm->pc = offset;
                }
                break;
            }
            
            case OP_JEQ: {
                uint32_t offset = read_u32(vm);
                double b = pop_stack(vm);
                double a = pop_stack(vm);
                if (fabs(a - b) <= EPSILON) {
                    vm->pc = offset;
                }
                break;
            }
            
            case OP_READ_FLAG: {
                uint8_t reg = read_byte(vm);
                // Flag is already set via vm_set_flag
                vm->regs[reg] = vm->flag_len;
                break;
            }
            
            case OP_PUSH_FLAG_CHAR: {
                int idx = (int)pop_stack(vm);
                if (idx >= 0 && idx < vm->flag_len) {
                    push_stack(vm, (double)((unsigned char)vm->flag[idx]));
                } else {
                    push_stack(vm, 0.0);
                }
                break;
            }
            
            case OP_FLAG_LEN: {
                push_stack(vm, (double)vm->flag_len);
                break;
            }
            
            case OP_EQ: {
                double b = pop_stack(vm);
                double a = pop_stack(vm);
                push_stack(vm, (fabs(a - b) <= EPSILON) ? 1.0 : 0.0);
                break;
            }
            
            case OP_EXIT:
                vm->exit_code = (int)pop_stack(vm);
                vm->running = 0;
                break;
                
            default:
                // Unknown opcode, exit
                vm->running = 0;
                break;
        }
    }
    
    return vm->exit_code;
}
