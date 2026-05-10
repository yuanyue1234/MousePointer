param(
    [ValidateSet("OneDir", "OneFile", "Both")]
    [string]$PackageMode = "Both"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Join-Chars {
    param([int[]]$Codes)
    return -join ($Codes | ForEach-Object { [char]$_ })
}

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $root ".venv\Scripts\python.exe"
$exeName = Join-Chars @(0x9F20, 0x6807, 0x6307, 0x9488, 0x914D, 0x7F6E, 0x751F, 0x6210, 0x5668, 0x005F, 0x7EFF, 0x8272, 0x7A0B, 0x5E8F)
$exeFile = "$exeName.exe"
$distDir = Join-Path $root "dist"
$releaseDir = Join-Path $root "release-assets"
$oneDirName = "MousePointer_Portable_Directory"
$oneDirZip = Join-Path $releaseDir "$oneDirName.zip"
$sumFile = Join-Path $releaseDir "SHA256SUMS.txt"
$payloadRoot = Join-Path $root "build\package_payload"
$payloadAssets = Join-Path $payloadRoot "assets"
$iconFinalName = "icon" + (Join-Chars @(0x7EC8)) + ".png"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing Python runtime: $python"
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

    $payloadPrefix = [System.IO.Path]::GetFullPath($payloadRoot) + [System.IO.Path]::DirectorySeparatorChar
    $roleIconFiles = & git -C $root ls-files -- "assets/role_icons/*.png"
    if (-not $roleIconFiles) {
        throw "No tracked role icons found for package payload."
    }
    foreach ($file in $roleIconFiles) {
        & git -C $root checkout-index -f --prefix=$payloadPrefix -- $file
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to restore tracked role icon into package payload: $file"
        }
    }
}

function Clear-ManagedReleaseOutputs {
    Remove-InWorkspace (Join-Path $distDir $exeFile)
    Remove-InWorkspace (Join-Path $distDir $exeName)
    Remove-InWorkspace (Join-Path $releaseDir $exeFile)
    Remove-InWorkspace (Join-Path $releaseDir $oneDirName)
    Remove-InWorkspace $oneDirZip
    Remove-InWorkspace $sumFile
    Remove-InWorkspace (Join-Path $distDir "_build")
    Remove-InWorkspace (Join-Path $distDir "错误记录.txt")
    Remove-InWorkspace (Join-Path $releaseDir "_build")
    Remove-InWorkspace (Join-Path $releaseDir "错误记录.txt")
}

function Invoke-PyInstaller {
    param(
        [switch]$OneFile
    )
    $work = Join-Path $root ("build\pyinstaller_" + ($(if ($OneFile) { "onefile" } else { "onedir" })))
    $spec = Join-Path $root ("build\spec_" + ($(if ($OneFile) { "onefile" } else { "onedir" })))
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
        "--collect-all", "qfluentwidgets",
        "--exclude-module", "tkinter",
        "--exclude-module", "_tkinter",
        "--exclude-module", "tkinterdnd2"
    )
    if ($OneFile) {
        $args += "--onefile"
    } else {
        $args += "--onedir"
    }
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

$results = @()

if ($PackageMode -in @("OneFile", "Both")) {
    Invoke-PyInstaller -OneFile
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
}

if ($PackageMode -in @("OneDir", "Both")) {
    $distOneDir = Join-Path $distDir $exeName
    $releaseOneDir = Join-Path $releaseDir $oneDirName
    Invoke-PyInstaller
    Move-Item -LiteralPath $distOneDir -Destination $releaseOneDir -Force
    $exe = Join-Path $releaseOneDir $exeFile
    Compress-Archive -Path (Join-Path $releaseOneDir "*") -DestinationPath $oneDirZip -Force
    $size = (Get-ChildItem -LiteralPath $releaseOneDir -Recurse -File | Measure-Object -Property Length -Sum).Sum
    $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $exe
    $results += [PSCustomObject]@{
        Kind = "onedir"
        Path = $releaseOneDir
        ReleaseName = $oneDirName
        SizeMB = [math]::Round($size / 1MB, 2)
        SHA256 = $hash.Hash
    }
    $zipHash = Get-FileHash -Algorithm SHA256 -LiteralPath $oneDirZip
    $results += [PSCustomObject]@{
        Kind = "onedir_zip"
        Path = $oneDirZip
        ReleaseName = "$oneDirName.zip"
        SizeMB = [math]::Round((Get-Item -LiteralPath $oneDirZip).Length / 1MB, 2)
        SHA256 = $zipHash.Hash
    }
}

$results | ForEach-Object {
    $name = $_.ReleaseName
    "{0}  {1}" -f $_.SHA256, $name
} | Set-Content -LiteralPath $sumFile -Encoding ASCII

$results
