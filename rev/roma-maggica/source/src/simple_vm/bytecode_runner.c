#include "bytecode_vm.h"
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    if (argc < 3) {
        fprintf(stderr, "Usage: %s <bytecode_file> <flag>\n", argv[0]);
        return 1;
    }
    
    const char *bytecode_file = argv[1];
    const char *flag = argv[2];
    
    // Read bytecode
    FILE *f = fopen(bytecode_file, "rb");
    if (!f) {
        fprintf(stderr, "Error: Cannot open bytecode file '%s'\n", bytecode_file);
        return 1;
    }
    
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    
    if (size <= 0 || size > 1000000) {
        fprintf(stderr, "Error: Invalid bytecode file size\n");
        fclose(f);
        return 1;
    }
    
    uint8_t *bytecode = (uint8_t *)malloc(size);
    if (!bytecode) {
        fprintf(stderr, "Error: Memory allocation failed\n");
        fclose(f);
        return 1;
    }
    
    size_t bytes_read = fread(bytecode, 1, size, f);
    fclose(f);
    
    if (bytes_read != (size_t)size) {
        fprintf(stderr, "Error: Failed to read entire bytecode file\n");
        free(bytecode);
        return 1;
    }
    
    // Create and run VM
    BytecodeVM *vm = vm_create();
    if (!vm) {
        fprintf(stderr, "Error: Failed to create VM\n");
        free(bytecode);
        return 1;
    }
    
    vm_set_bytecode(vm, bytecode, size);
    vm_set_flag(vm, flag);
    
    int exit_code = vm_execute(vm);
    
    if (exit_code == 0) {
        printf("SUCCESS: Flag is correct!\n");
    } else {
        printf("FAILURE: Flag is incorrect.\n");
    }
    
    vm_destroy(vm);
    free(bytecode);
    
    return exit_code;
}
