param(
    [ValidateSet("Source", "OneFile", "OneDir")]
    [string]$Mode = "OneDir",
    [string]$CursorPath = "C:\Windows\Cursors\aero_arrow.cur",
    [int]$TimeoutSeconds = 15
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Join-Chars {
    param([int[]]$Codes)
    return -join ($Codes | ForEach-Object { [char]$_ })
}

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$exeName = Join-Chars @(0x9F20, 0x6807, 0x6307, 0x9488, 0x914D, 0x7F6E, 0x751F, 0x6210, 0x5668, 0x005F, 0x7EFF, 0x8272, 0x7A0B, 0x5E8F)
$exeFile = "$exeName.exe"

if (-not (Test-Path -LiteralPath $CursorPath)) {
    throw "Missing cursor: $CursorPath"
}

if ($Mode -eq "Source") {
    $file = Join-Path $root ".venv\Scripts\pythonw.exe"
    if (-not (Test-Path -LiteralPath $file)) {
        $file = Join-Path $root ".venv\Scripts\python.exe"
    }
    $arguments = @((Join-Path $root "main.py"), "--preview-cursor", $CursorPath)
    $working = $root
    $processName = [System.IO.Path]::GetFileNameWithoutExtension($file)
} elseif ($Mode -eq "OneFile") {
    $file = Join-Path $root "release-assets\$exeFile"
    $arguments = @("--preview-cursor", $CursorPath)
    $working = Split-Path -Parent $file
    $processName = $exeName
} else {
    $file = Join-Path $root "release-assets\MousePointer_Portable_Directory\$exeFile"
    $arguments = @("--preview-cursor", $CursorPath)
    $working = Split-Path -Parent $file
    $processName = $exeName
}

if (-not (Test-Path -LiteralPath $file)) {
    throw "Missing executable: $file"
}

Get-Process -Name $processName -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

$watch = [System.Diagnostics.Stopwatch]::StartNew()
$process = Start-Process -FilePath $file -ArgumentList $arguments -WorkingDirectory $working -PassThru
$windowAt = $null
$deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)

while ([DateTime]::UtcNow -lt $deadline) {
    foreach ($proc in @(Get-Process -Name $processName -ErrorAction SilentlyContinue)) {
        $proc.Refresh()
        if ($proc.MainWindowHandle -ne 0 -and $proc.MainWindowTitle) {
            $windowAt = $watch.Elapsed
            break
        }
    }
    if ($windowAt) {
        break
    }
    Start-Sleep -Milliseconds 50
}

$watch.Stop()
$rows = @(Get-Process -Name $processName -ErrorAction SilentlyContinue)
Get-Process -Name $processName -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

[PSCustomObject]@{
    Mode = $Mode
    CursorPath = $CursorPath
    PreviewWindowMilliseconds = if ($windowAt) { [int]$windowAt.TotalMilliseconds } else { $null }
    TimedOut = -not [bool]$windowAt
    ProcessCount = $rows.Count
}
