#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "payload.h"

#ifdef DEBUG
#define DBG_PRINT(...) {fprintf(stderr, "[DEBUG] " __VA_ARGS__); fflush(stderr);}
static void dbg_print_winerr(const char *api_name) {
    DWORD err = GetLastError();
    fprintf(stderr, "[DEBUG] %s failed (GetLastError=%lu)\n", api_name, (unsigned long)err);
    fflush(stderr);
}
static void dbg_print_wsaerr(const char *api_name) {
    int err = WSAGetLastError();
    fprintf(stderr, "[DEBUG] %s failed (WSAGetLastError=%d)\n", api_name, err);
    fflush(stderr);
}
#else
#define DBG_PRINT(...) ((void)0)
static void dbg_print_winerr(const char *api_name) { (void)api_name; }
static void dbg_print_wsaerr(const char *api_name) { (void)api_name; }
#endif

// Writes the given buffer to a temporary file and returns the path to that file in out_path.
// Returns EXIT_SUCCESS on success, EXIT_FAILURE on failure.
static int put_buf_in_tmp_file(uint8_t *buf_data, DWORD buf_len, char *out_path) {
    
    char temp_path[MAX_PATH];
    char temp_file[MAX_PATH];

    if (GetTempPathA(sizeof(temp_path), temp_path) == 0) {
        dbg_print_winerr("GetTempPathA");
        return EXIT_FAILURE;
    }

    if (GetTempFileNameA(temp_path, "payload", 0, temp_file) == 0) {
        dbg_print_winerr("GetTempFileNameA");
        return EXIT_FAILURE;
    }

    // append .dll to the temp_path
    strncat(temp_file, ".dll", MAX_PATH - strlen(temp_file) - 1);

    HANDLE hFile = CreateFileA(temp_file, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hFile == INVALID_HANDLE_VALUE) {
        dbg_print_winerr("CreateFileA");
        return EXIT_FAILURE;
    }

    DWORD written;
    BOOL write_result = WriteFile(hFile, buf_data, buf_len, &written, NULL);
    CloseHandle(hFile);

    if (!write_result || written != buf_len) {
        DBG_PRINT("WriteFile mismatch (ok=%d written=%lu expected=%lu)\n", (int)write_result, (unsigned long)written, (unsigned long)buf_len);
        DeleteFileA(temp_file);
        return EXIT_FAILURE;
    }

    strncpy(out_path, temp_file, MAX_PATH - 1);
    out_path[MAX_PATH - 1] = '\0';

    DBG_PRINT("Decrypted payload written to: %s\n", out_path);
    return EXIT_SUCCESS;
}


static int load_and_decrypt_payload(char *out_path) {
	HRSRC hres;
	HGLOBAL hmem;
	const void *locked;
	DWORD len;
	uint8_t *buf;
	const uint8_t key[2] = {0x37, 0x13};

    DBG_PRINT("Loading encrypted payload from resource ID %u\n", (unsigned)IDR_ENCRYPTED_PAYLOAD);

    hres = FindResourceA(NULL, MAKEINTRESOURCEA(IDR_ENCRYPTED_PAYLOAD), RT_RCDATA);
	if (!hres) {
        dbg_print_winerr("FindResourceA");
		return EXIT_FAILURE;
	}

	hmem = LoadResource(NULL, hres);
	if (!hmem) {
        dbg_print_winerr("LoadResource");
		return EXIT_FAILURE;
	}

	locked = LockResource(hmem);
	if (!locked) {
        dbg_print_winerr("LockResource");
		return EXIT_FAILURE;
	}

	len = SizeofResource(NULL, hres);
	if (len == 0) {
        dbg_print_winerr("SizeofResource");
		return EXIT_FAILURE;
	}

    DBG_PRINT("Encrypted resource size: %lu bytes\n", (unsigned long)len);

	buf = (uint8_t *)malloc(len);
	if (!buf) {
        DBG_PRINT("malloc failed for %lu bytes\n", (unsigned long)len);
		return EXIT_FAILURE;
	}

	memcpy(buf, locked, len);

	for (DWORD i = 0; i < len; i++) {
		buf[i] ^= key[i % 2];
	}

	if (put_buf_in_tmp_file(buf, len, out_path) == EXIT_FAILURE) {
		free(buf);
		return EXIT_FAILURE;
	}
    free(buf);

    DBG_PRINT("Payload decrypted and staged at: %s\n", out_path);

	return EXIT_SUCCESS;
}


// load the dll into the suspended svchost.exe, then resume it
static int load_dll(char *dll_path) {
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    char cmdline[] = "notepad.exe";  // must be mutable

    ZeroMemory(&si, sizeof(si));
    ZeroMemory(&pi, sizeof(pi));
    si.cb = sizeof(si);

    // Hide window
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    
    DBG_PRINT("Launching helper process: %s\n", cmdline);
    if (!CreateProcessA(NULL, cmdline, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) {
        // DWORD err = GetLastError();
        // printf("CreateProcess failed: %lu\n", err);
        dbg_print_winerr("CreateProcessA");
        return 1;
    }

    DBG_PRINT("Helper process launched successfully with PID %lu\n", (unsigned long)pi.dwProcessId);

    // virtualAllocEx + writeprocessMemory + createRemoteThread to run LoadLibraryA in the remote process
    size_t dll_path_len = strlen((char *)dll_path) + 1;
    LPVOID remote_mem = VirtualAllocEx(pi.hProcess, NULL, dll_path_len, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (!remote_mem) {
        dbg_print_winerr("VirtualAllocEx");
        TerminateProcess(pi.hProcess, 1);
        return EXIT_FAILURE;
    }
    DBG_PRINT("Allocated memory in remote process at %p\n", remote_mem);
    
    if (!WriteProcessMemory(pi.hProcess, remote_mem, dll_path, dll_path_len, NULL)) {
        dbg_print_winerr("WriteProcessMemory");
        VirtualFreeEx(pi.hProcess, remote_mem, 0, MEM_RELEASE);
        TerminateProcess(pi.hProcess, 1);
        return EXIT_FAILURE;
    }
    DBG_PRINT("Written DLL path to remote process memory\n");

    HMODULE hKernel32 = GetModuleHandleA("kernel32.dll");
    if (!hKernel32) {
        dbg_print_winerr("GetModuleHandleA");
        VirtualFreeEx(pi.hProcess, remote_mem, 0, MEM_RELEASE);
        TerminateProcess(pi.hProcess, 1);
        return EXIT_FAILURE;
    }
    DBG_PRINT("Retrieved kernel32.dll handle at %p\n", (void *)hKernel32);

    LPVOID load_library_addr = GetProcAddress(hKernel32, "LoadLibraryA");
    if (!load_library_addr) {
        dbg_print_winerr("GetProcAddress");
        VirtualFreeEx(pi.hProcess, remote_mem, 0, MEM_RELEASE);
        TerminateProcess(pi.hProcess, 1);
        return EXIT_FAILURE;
    }
    DBG_PRINT("Retrieved LoadLibraryA address at %p\n", load_library_addr);

    HANDLE hThread = CreateRemoteThread(pi.hProcess, NULL, 0, (LPTHREAD_START_ROUTINE)load_library_addr, remote_mem, 0, NULL);
    if (!hThread) {
        dbg_print_winerr("CreateRemoteThread");
        VirtualFreeEx(pi.hProcess, remote_mem, 0, MEM_RELEASE);
        TerminateProcess(pi.hProcess, 1);
        return EXIT_FAILURE;
    }
    DBG_PRINT("Remote thread created successfully; DLL path queued at %p\n", remote_mem);

    WaitForSingleObject(hThread, INFINITE); 
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    CloseHandle(hThread);

    return EXIT_SUCCESS;
} 

static int create_loopback_listener(SOCKET *listener, uint16_t *port_out) {
    struct sockaddr_in addr;
    int addr_len = sizeof(addr);

    *listener = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (*listener == INVALID_SOCKET) {
        dbg_print_wsaerr("socket");
        return EXIT_FAILURE;
    }

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(12345);
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);

    if (bind(*listener, (const struct sockaddr *)&addr, sizeof(addr)) == SOCKET_ERROR) {
        dbg_print_wsaerr("bind");
        closesocket(*listener);
        return EXIT_FAILURE;
    }

    if (listen(*listener, 1) == SOCKET_ERROR) {
        dbg_print_wsaerr("listen");
        closesocket(*listener);
        return EXIT_FAILURE;
    }

    if (getsockname(*listener, (struct sockaddr *)&addr, &addr_len) == SOCKET_ERROR) {
        dbg_print_wsaerr("getsockname");
        closesocket(*listener);
        return EXIT_FAILURE;
    }

    *port_out = ntohs(addr.sin_port);
    DBG_PRINT("Listener bound on 127.0.0.1:%u\n", (unsigned)*port_out);
    return EXIT_SUCCESS;
}
    
static int check_result_from_client(SOCKET listener) {
    SOCKET client;
    int recv_len;
    char result;

    DBG_PRINT("Waiting for callback on listener...\n");
    client = accept(listener, NULL, NULL);
    if (client == INVALID_SOCKET) {
        dbg_print_wsaerr("accept");
        closesocket(listener);
        return EXIT_FAILURE;
    }

    recv_len = recv(client, &result, 1, 0);
    closesocket(client);

    if (recv_len != 1) {
        dbg_print_wsaerr("recv");
        DBG_PRINT("recv_len=%d\n", recv_len);
    }

    if (recv_len == 1 && result == '1') {
        return EXIT_SUCCESS;
    }

    return EXIT_FAILURE;
}


int main(void) {
	char *tmp_path = NULL;

    SOCKET listener;
    uint16_t port;

    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        dbg_print_wsaerr("WSAStartup");
        return EXIT_FAILURE;
    }

    if (create_loopback_listener(&listener, &port) == EXIT_FAILURE) {
        DBG_PRINT("Failed to create loopback listener\n");
        WSACleanup();
        return EXIT_FAILURE;
    }

    tmp_path = (char *)malloc(MAX_PATH);
    if (!tmp_path) {
        DBG_PRINT("malloc failed for tmp_path\n");
        closesocket(listener);
        WSACleanup();
        return EXIT_FAILURE;
    }

	if (load_and_decrypt_payload(tmp_path) == EXIT_FAILURE) {
        DBG_PRINT("Failed to load and decrypt payload\n");
        closesocket(listener);
		free(tmp_path);
		WSACleanup();
		return EXIT_FAILURE;
	}

    if (load_dll(tmp_path) == EXIT_FAILURE) {
        DBG_PRINT("Failed to load DLL\n");
        closesocket(listener);
        free(tmp_path);
        WSACleanup();
        return EXIT_FAILURE;
    }

    DBG_PRINT("Helper process launched; now waiting for callback result\n");

    
    if (check_result_from_client(listener) == EXIT_SUCCESS) {
        puts("lessgoo");
    } else {
        puts("Can't you afford a license? Here's one for free: TRX{y0u_4r3_th3_b3s7_4t_r3v3rs1ng}");
    }

    WSACleanup();

    closesocket(listener);
    free(tmp_path);
	return EXIT_SUCCESS;
}
