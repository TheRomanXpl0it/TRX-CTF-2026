param(
    [string]$ExePath = "$PSScriptRoot\..\build\challenge.exe",
    [int]$TimeoutSec = 15
)

$ErrorActionPreference = "Stop"

$regKeyPath = "HKCU:\Software\Microsoft\CTF"
$regValueName = "TRX"

$tests = @(
    @{
        Name = "wrong_1"
        Flag = "TRX{definitely_wrong_1}"
        Expected = "Can't you afford a license? Here's one for free: TRX{y0u_4r3_th3_b3s7_4t_r3v3rs1ng}"
    },
    @{
        Name = "correct"
        Flag = "TRX{f0rz4_R0m4_d4j3!!___f0rc3_R0m3_L3tS_g0!!}"
        Expected = "lessgoo"
    },
    @{
        Name = "wrong_2"
        Flag = "TRX{f0rz4_R0m4_d4j3!!---f0rc3_R0m3_L3tS_g0!!}"
        Expected = "Can't you afford a license? Here's one for free: TRX{y0u_4r3_th3_b3s7_4t_r3v3rs1ng}"
    }
)

if (-not (Test-Path -LiteralPath $ExePath)) {
    throw "Challenge executable not found: $ExePath"
}

if (-not (Test-Path $regKeyPath)) {
    New-Item -Path $regKeyPath -Force | Out-Null
}

$hadOriginal = $false
$originalValue = $null
try {
    $existing = Get-ItemProperty -Path $regKeyPath -Name $regValueName -ErrorAction Stop
    $hadOriginal = $true
    $originalValue = $existing.$regValueName
} catch {
    $hadOriginal = $false
}

$passed = 0
$total = $tests.Count

foreach ($test in $tests) {
    Set-ItemProperty -Path $regKeyPath -Name $regValueName -Value $test.Flag -Type String

    $stdout = Join-Path $env:TEMP ("challenge_test_" + [guid]::NewGuid().ToString() + ".out.txt")
    $stderr = Join-Path $env:TEMP ("challenge_test_" + [guid]::NewGuid().ToString() + ".err.txt")

    try {
        $proc = Start-Process -FilePath $ExePath -NoNewWindow -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr

        if (-not $proc.WaitForExit($TimeoutSec * 1000)) {
            try { $proc.Kill() } catch {}
            Write-Host ("[FAIL] {0}: timeout after {1}s" -f $test.Name, $TimeoutSec)
            continue
        }

        $outText = ""
        $errText = ""
        if (Test-Path $stdout) {
            $outRaw = Get-Content -Raw -LiteralPath $stdout -ErrorAction SilentlyContinue
            if ($null -ne $outRaw) { $outText = $outRaw.Trim() }
        }
        if (Test-Path $stderr) {
            $errRaw = Get-Content -Raw -LiteralPath $stderr -ErrorAction SilentlyContinue
            if ($null -ne $errRaw) { $errText = $errRaw.Trim() }
        }

        if ($outText -match [regex]::Escape($test.Expected)) {
            $passed++
            Write-Host ("[PASS] {0}: expected='{1}', got='{2}'" -f $test.Name, $test.Expected, $outText)
        } else {
            Write-Host ("[FAIL] {0}: expected='{1}', got='{2}', code={3}" -f $test.Name, $test.Expected, $outText, $proc.ExitCode)
            if ($errText) {
                Write-Host ("       stderr: {0}" -f $errText)
            }
        }
    } finally {
        if (Test-Path $stdout) { Remove-Item -LiteralPath $stdout -Force -ErrorAction SilentlyContinue }
        if (Test-Path $stderr) { Remove-Item -LiteralPath $stderr -Force -ErrorAction SilentlyContinue }
    }
}

if ($hadOriginal) {
    Set-ItemProperty -Path $regKeyPath -Name $regValueName -Value $originalValue -Type String
} else {
    Remove-ItemProperty -Path $regKeyPath -Name $regValueName -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host ("Passed {0}/{1} tests" -f $passed, $total)

if ($passed -eq $total) {
    exit 0
}

exit 1
