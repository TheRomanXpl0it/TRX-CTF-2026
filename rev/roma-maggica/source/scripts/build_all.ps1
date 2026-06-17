param(
    [string]$CC = "C:\msys64\ucrt64\bin\gcc.exe",
    [string]$Windres = "C:\msys64\ucrt64\bin\windres.exe",
    [string]$Strip = "C:\msys64\ucrt64\bin\strip.exe",
    [string]$Python = "python",
    [string]$Mpress,
    [string]$Upx,
    [string]$BuildDir,
    [switch]$Dbg
)

$ErrorActionPreference = "Stop"

if ($args -contains "--dbg") {
    $Dbg = $true
}

$SourceRoot = Split-Path -Parent $PSScriptRoot
$SrcRoot = Join-Path $SourceRoot "src"
$SrcC = Join-Path $SourceRoot "src\c"
$SrcVm = Join-Path $SourceRoot "src\simple_vm"
$ResourceScript = Join-Path $SourceRoot "resources\payload.rc"
$EncryptScript = Join-Path $PSScriptRoot "encrypt_payload.py"

if ([string]::IsNullOrWhiteSpace($BuildDir)) {
    $BuildDir = Join-Path $SourceRoot "build"
}
if ([string]::IsNullOrWhiteSpace($Mpress)) {
    $Mpress = Join-Path $SourceRoot "tools\mpress.exe"
}
if ([string]::IsNullOrWhiteSpace($Upx)) {
    $Upx = Join-Path $SourceRoot "tools\upx.exe"
}

Set-Location $SourceRoot

if (-not (Test-Path -LiteralPath $CC)) {
    throw "Compiler not found: $CC"
}
if (-not (Test-Path -LiteralPath $Windres)) {
    throw "windres not found: $Windres"
}
if (-not (Test-Path -LiteralPath $Strip)) {
    throw "strip not found: $Strip"
}
if (-not (Test-Path -LiteralPath $EncryptScript)) {
    throw "Encrypt script not found: $EncryptScript"
}

New-Item -ItemType Directory -Path $BuildDir -Force | Out-Null

$PayloadDll = Join-Path $BuildDir "payload.dll"
$EncryptedPayload = Join-Path $BuildDir "encrypted_payload.bin"
$PayloadRes = Join-Path $BuildDir "payload.res"
$ChallengeExe = Join-Path $BuildDir "challenge.exe"

Write-Host "[1/6] Building DLL ($PayloadDll)..."
if ($Dbg) {
    & $CC -shared -O0 -Wall -Wextra -DDEBUG -I $SrcRoot -I $SrcC -I $SrcVm -o $PayloadDll (Join-Path $SrcC "vm_runner_dll.c") (Join-Path $SrcVm "bytecode_vm.c") -lws2_32 -ladvapi32
} else {
    & $CC -shared -O0 -Wall -Wextra -I $SrcRoot -I $SrcC -I $SrcVm -o $PayloadDll (Join-Path $SrcC "vm_runner_dll.c") (Join-Path $SrcVm "bytecode_vm.c") -lws2_32 -ladvapi32
}
if ($LASTEXITCODE -ne 0) { throw "DLL build failed" }

Write-Host "[2/6] Encrypting DLL -> $EncryptedPayload..."
& $Python $EncryptScript --input $PayloadDll --output $EncryptedPayload --key 0x1337
if ($LASTEXITCODE -ne 0) { throw "Encryption step failed" }

Write-Host "[3/6] Building resource object ($PayloadRes)..."
& $Windres $ResourceScript -I $SrcC -O coff -o $PayloadRes
if ($LASTEXITCODE -ne 0) { throw "Resource build failed" }

Write-Host "[4/6] Building final executable ($ChallengeExe)..."
if ($Dbg) {
    & $CC -O0 -Wall -Wextra -DDEBUG -I $SrcRoot -I $SrcC -I $SrcVm -o $ChallengeExe (Join-Path $SrcC "payload_loader.c") $PayloadRes -lws2_32 -ladvapi32
} else {
    & $CC -O0 -Wall -Wextra -I $SrcRoot -I $SrcC -I $SrcVm -o $ChallengeExe (Join-Path $SrcC "payload_loader.c") $PayloadRes -lws2_32 -ladvapi32
}
if ($LASTEXITCODE -ne 0) { throw "Final executable build failed" }

Write-Host "[5/6] Stripping symbols from $ChallengeExe..."
& $Strip --strip-all $ChallengeExe
if ($LASTEXITCODE -ne 0) { throw "Strip step failed" }

$Packed = $false
$PackedWith = ""

if (Test-Path -LiteralPath $Mpress) {
    Write-Host "[6/7] Packing executable with MPRESS..."
    & $Mpress -q -i $ChallengeExe
    if ($LASTEXITCODE -eq 0) {
        $Packed = $true
        $PackedWith = "MPRESS"
    } else {
        Write-Warning "MPRESS could not pack this binary (exit code: $LASTEXITCODE)."
    }
} else {
    Write-Warning "MPRESS not found at: $Mpress"
}

if ((-not $Packed) -and (Test-Path -LiteralPath $Upx)) {
    Write-Host "[7/7] Packing executable with UPX..."
    & $Upx --best --lzma $ChallengeExe
    if ($LASTEXITCODE -eq 0) {
        $Packed = $true
        $PackedWith = "UPX"
    } else {
        Write-Warning "UPX could not pack this binary (exit code: $LASTEXITCODE)."
    }
} elseif (-not (Test-Path -LiteralPath $Upx)) {
    Write-Warning "UPX not found at: $Upx"
}

Write-Host "Done. Built files:"
Write-Host "  - $PayloadDll"
Write-Host "  - $EncryptedPayload"
Write-Host "  - $PayloadRes"
if ($Packed) {
    Write-Host "  - $ChallengeExe (stripped + packed via $PackedWith)"
} else {
    Write-Host "  - $ChallengeExe (stripped, packing skipped)"
}
