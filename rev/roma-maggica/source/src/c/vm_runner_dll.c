#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "../simple_vm/bytecode_vm.h"
#include "global.h"

static int read_flag_from_registry(char *buffer, size_t buffer_size) {
    HKEY hKey;
    DWORD dwType = 0;
    DWORD dwSize = (DWORD)buffer_size;

    if (RegOpenKeyExA(HKEY_CURRENT_USER, REG_PATH, 0, KEY_READ, &hKey) != ERROR_SUCCESS) {
        return 0;
    }

    if (RegQueryValueExA(hKey, REG_VALUE, NULL, &dwType, (LPBYTE)buffer, &dwSize) != ERROR_SUCCESS || dwType != REG_SZ) {
        RegCloseKey(hKey);
        return 0;
    }

    RegCloseKey(hKey);
    return 1;
}

static int send_result_to_parent(uint16_t port, char result) {
    SOCKET s = INVALID_SOCKET;
    struct sockaddr_in addr;

    s = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (s == INVALID_SOCKET) {
        return 0;
    }

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    addr.sin_addr.s_addr = inet_addr(LOOPBACK_ADDR);

    if (connect(s, (const struct sockaddr *)&addr, sizeof(addr)) == SOCKET_ERROR) {
        closesocket(s);
        return 0;
    }

    send(s, &result, 1, 0);
    closesocket(s);
    return 1;
}

static DWORD WINAPI worker_main(LPVOID lpParameter) {
    uint16_t port = (uint16_t)(uintptr_t)lpParameter;
    char flag[FLAG_MAX_LEN] = {0};
    int vm_exit = 1;
    BytecodeVM *vm;
    
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        #ifdef DEBUG
        fprintf(stderr, "WSAStartup failed\\n");
        #endif
        return EXIT_FAILURE;
    }

    if (!read_flag_from_registry(flag, sizeof(flag))) {
        (void)send_result_to_parent(port, '0');
        return EXIT_FAILURE;
    }

    vm = vm_create();
    if (!vm) {
        (void)send_result_to_parent(port, '0');
        return EXIT_FAILURE;
    }

    vm_set_bytecode(vm, kBytecode, sizeof(kBytecode));
    vm_set_flag(vm, flag);
    vm_exit = vm_execute(vm);
    vm_destroy(vm);

    (void)send_result_to_parent(port, (vm_exit == 0) ? '1' : '0');

    WSACleanup();
    return EXIT_SUCCESS;
}



BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved) {
    (void)hinstDLL;
    (void)lpvReserved;

    switch (fdwReason) {
        case DLL_PROCESS_ATTACH:
            // Run the VM in a new thread. pass port 26572 as parameter for testing, but the actual port will be sent by the parent process when it launches this DLL.
            CreateThread(NULL, 0, worker_main, (LPVOID)(uintptr_t)12345, 0, NULL);
            break;
        case DLL_THREAD_ATTACH:
        case DLL_THREAD_DETACH:
        case DLL_PROCESS_DETACH:
            break;
    }
    return TRUE;
}
