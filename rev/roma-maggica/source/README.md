To build
powershell -ExecutionPolicy Bypass -File scripts\build_all.ps1

Build artifacts are written to `source/build/`:
- payload.dll
- encrypted_payload.bin
- payload.res
- challenge.exe (stripped, then MPRESS is attempted, then UPX fallback)

Layout:
- scripts/: PowerShell and Python build/test scripts
- src/c/: C sources and headers
- src/simple_vm/: VM implementation
- resources/: RC/resource input files
- tools/: binary packers (mpress/upx)

To test
powershell -ExecutionPolicy Bypass -File scripts\test_challenge.ps1
