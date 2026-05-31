param(
    [ValidateSet("OneFile")]
    [string]$PackageMode = "OneFile"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Join-Chars {
    param([int[]]$Codes)
    return -join ($Codes | ForEach-Object { [char]$_ })
}

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
$python = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { "python" }
$exeName = Join-Chars @(0x9F20, 0x6807, 0x6307, 0x9488, 0x914D, 0x7F6E, 0x751F, 0x6210, 0x5668, 0x005F, 0x7EFF, 0x8272, 0x7A0B, 0x5E8F)
$exeFile = "$exeName.exe"
$distDir = Join-Path $root "dist"
$releaseDir = Join-Path $root "release-assets"
$sumFile = Join-Path $releaseDir "SHA256SUMS.txt"
$payloadRoot = Join-Path $root "build\package_payload"
$payloadAssets = Join-Path $payloadRoot "assets"
$runtimeBundles = Join-Path $root "runtime-bundles"
$iconFinalName = "icon" + (Join-Chars @(0x7EC8)) + ".png"

& $python --version | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw "Unable to run Python: $python"
}

function Remove-InWorkspace {
    param([string]$Path)
    $fullRoot = [System.IO.Path]::GetFullPath($root).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    if (-not $fullPath.StartsWith($fullRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove outside workspace: $fullPath"
    }
    Remove-Item -LiteralPath $fullPath -Recurse -Force -ErrorAction SilentlyContinue
}

function New-PackagePayload {
    Remove-InWorkspace $payloadRoot
    New-Item -ItemType Directory -Force -Path $payloadAssets | Out-Null

    $assets = Join-Path $root "assets"
    if (Test-Path -LiteralPath $assets) {
        Copy-Item -Path (Join-Path $assets "*") -Destination $payloadAssets -Recurse -Force -ErrorAction SilentlyContinue
    }

    $roleIconsDir = Join-Path $root "assets\role_icons"
    if (-not (Test-Path -LiteralPath $roleIconsDir)) {
        throw "No role icons directory found for package payload."
    }
    $roleIconFiles = Get-ChildItem -LiteralPath $roleIconsDir -Filter "*.png" -File
    if (-not $roleIconFiles -or $roleIconFiles.Count -eq 0) {
        throw "No role icon PNG files found for package payload."
    }
}

function Clear-ManagedReleaseOutputs {
    Remove-InWorkspace (Join-Path $distDir $exeFile)
    Remove-InWorkspace (Join-Path $distDir $exeName)
    Remove-InWorkspace (Join-Path $releaseDir $exeFile)
    Remove-InWorkspace $sumFile
    Remove-InWorkspace (Join-Path $distDir "_build")
    Remove-InWorkspace (Join-Path $distDir "错误记录.txt")
    Remove-InWorkspace (Join-Path $releaseDir "_build")
    Remove-InWorkspace (Join-Path $releaseDir "错误记录.txt")
}

function Invoke-PyInstaller {
    $work = Join-Path $root "build\pyinstaller_onefile"
    $spec = Join-Path $root "build\spec_onefile"
    $args = @(
        "-m", "PyInstaller",
        "--noconsole",
        "--windowed",
        "--clean",
        "--name", $exeName,
        "--icon", (Join-Path $root "assets\app.ico"),
        "--distpath", $distDir,
        "--workpath", $work,
        "--specpath", $spec,
        "--add-data", "$payloadAssets;assets",
        "--add-data", "$(Join-Path $root 'icon.png');.",
        "--add-data", "$(Join-Path $root $iconFinalName);.",
        "--add-data", "$runtimeBundles;runtime-bundles",
        "--collect-all", "qfluentwidgets",
        "--exclude-module", "tkinter",
        "--exclude-module", "_tkinter",
        "--exclude-module", "tkinterdnd2",
        "--onefile"
    )
    $args += (Join-Path $root "main.py")
    & $python @args
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed."
    }
}

Get-Process -Name $exeName -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $distDir, $releaseDir | Out-Null
Clear-ManagedReleaseOutputs
New-PackagePayload

& (Join-Path $PSScriptRoot "prepare_runtime_bundles.ps1") -Python $python
if ($LASTEXITCODE -ne 0) {
    throw "Runtime bundle preparation failed."
}
foreach ($bundle in @("python-pyinstaller-win-x64.zip", "7zip-win-x64.zip")) {
    $path = Join-Path $runtimeBundles $bundle
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Missing required runtime bundle: $path"
    }
}

$results = @()

Invoke-PyInstaller
$distExe = Join-Path $distDir $exeFile
$releaseExe = Join-Path $releaseDir $exeFile
Copy-Item -LiteralPath $distExe -Destination $releaseExe -Force
$hash = Get-FileHash -Algorithm SHA256 -LiteralPath $releaseExe
$results += [PSCustomObject]@{
    Kind = "onefile"
    Path = $releaseExe
    ReleaseName = "MousePointer_Portable.exe"
    SizeMB = [math]::Round((Get-Item -LiteralPath $releaseExe).Length / 1MB, 2)
    SHA256 = $hash.Hash
}

$results | ForEach-Object {
    $name = $_.ReleaseName
    "{0}  {1}" -f $_.SHA256, $name
} | Set-Content -LiteralPath $sumFile -Encoding ASCII

$results
