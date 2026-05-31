param(
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet("Info", "Warning", "Error")]
        [string]$Level = "Info"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    switch ($Level) {
        "Info" { Write-Host $logMessage -ForegroundColor Green }
        "Warning" { Write-Host $logMessage -ForegroundColor Yellow }
        "Error" { Write-Host $logMessage -ForegroundColor Red }
    }
}

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$bundleDir = Join-Path $root "runtime-bundles"
$stageRoot = Join-Path $root "build\runtime_bundle_stage"
$pythonStage = Join-Path $stageRoot "python"
$zipStage = Join-Path $stageRoot "7zip"
$downloadStage = Join-Path $stageRoot "downloads"
$pythonZip = Join-Path $bundleDir "python-pyinstaller-win-x64.zip"
$sevenZipZip = Join-Path $bundleDir "7zip-win-x64.zip"

Add-Type -AssemblyName System.IO.Compression.FileSystem

function Remove-InWorkspace {
    param([string]$Path)
    $fullRoot = [System.IO.Path]::GetFullPath($root).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    if (-not $fullPath.StartsWith($fullRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove outside workspace: $fullPath"
    }
    Remove-Item -LiteralPath $fullPath -Recurse -Force -ErrorAction SilentlyContinue
}

function Test-ZipContainsAny {
    param(
        [string]$ZipPath,
        [string[]]$EntryNames
    )
    if (-not (Test-Path -LiteralPath $ZipPath)) {
        return $false
    }
    $zip = $null
    try {
        $zip = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
        foreach ($entry in $zip.Entries) {
            $normalized = $entry.FullName.Replace("\", "/")
            foreach ($name in $EntryNames) {
                if ($normalized.Equals($name.Replace("\", "/"), [System.StringComparison]::OrdinalIgnoreCase)) {
                    return $true
                }
            }
        }
        return $false
    } catch {
        return $false
    } finally {
        if ($zip) {
            $zip.Dispose()
        }
    }
}

function New-ZipFromDirectoryStored {
    param(
        [string]$SourceDirectory,
        [string]$DestinationZip
    )
    $script = @"
import os
import pathlib
import zipfile

source = pathlib.Path(r'''$SourceDirectory''')
destination = pathlib.Path(r'''$DestinationZip''')
temporary = destination.with_suffix(destination.suffix + '.tmp')
if temporary.exists():
    temporary.unlink()
with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_STORED) as archive:
    for path in source.rglob('*'):
        if path.is_file():
            archive.write(path, path.relative_to(source).as_posix())
os.replace(temporary, destination)
"@
    $scriptPath = Join-Path $stageRoot "zip_directory.py"
    Set-Content -LiteralPath $scriptPath -Value $script -Encoding UTF8
    & $Python $scriptPath
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to create zip: $DestinationZip"
    }
}

function Get-PythonVersion {
    $versionFile = Join-Path $stageRoot "python_version.txt"
    $env:PY_VERSION_OUT = $versionFile
    & $Python -c "import os, pathlib, sys; pathlib.Path(os.environ['PY_VERSION_OUT']).write_text(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}', encoding='ascii')"
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to detect Python version from $Python"
    }
    return (Get-Content -Raw -Encoding ASCII -LiteralPath $versionFile).Trim()
}

function Get-PyInstallerRequirement {
    $requirement = "pyinstaller"
    $requirements = Join-Path $root "requirements.txt"
    if (Test-Path -LiteralPath $requirements) {
        $line = Get-Content -LiteralPath $requirements | Where-Object { $_ -match '^pyinstaller==' } | Select-Object -First 1
        if ($line) {
            $requirement = $line.Trim()
        }
    }
    return $requirement
}

function Set-EmbeddedPythonPathFile {
    param([string]$PythonDirectory)
    $pth = Get-ChildItem -LiteralPath $PythonDirectory -Filter "python*._pth" -File | Select-Object -First 1
    if (-not $pth) {
        throw "Embedded Python _pth file was not found."
    }
    $pythonZipName = (Get-ChildItem -LiteralPath $PythonDirectory -Filter "python*.zip" -File | Select-Object -First 1).Name
    if (-not $pythonZipName) {
        throw "Embedded Python standard library zip was not found."
    }
    @(
        $pythonZipName,
        ".",
        "Lib\site-packages",
        "import site"
    ) | Set-Content -LiteralPath $pth.FullName -Encoding ASCII
}

Write-Log "Starting runtime bundle preparation"

if (-not $Python) {
    $venvPython = Join-Path $root ".venv\Scripts\python.exe"
    $Python = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { "python" }
}
Write-Log "Using Python: $Python"

New-Item -ItemType Directory -Force -Path $bundleDir | Out-Null
Remove-InWorkspace $stageRoot
New-Item -ItemType Directory -Force -Path $pythonStage, $zipStage, $downloadStage | Out-Null

Write-Log "Step 1: Preparing embedded Python + PyInstaller runtime bundle"
try {
    if (
        (Test-ZipContainsAny -ZipPath $pythonZip -EntryNames @("python.exe")) -and
        (Test-ZipContainsAny -ZipPath $pythonZip -EntryNames @("Lib/site-packages/PyInstaller/__init__.py")) -and
        ((Get-Item -LiteralPath $pythonZip).Length -lt 300MB)
    ) {
        Write-Log "Existing Python runtime bundle is valid; reusing: $pythonZip"
    } else {
        Remove-Item -LiteralPath $pythonZip -Force -ErrorAction SilentlyContinue
        $pythonVersion = Get-PythonVersion
        $embedUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-embed-amd64.zip"
        $embedZip = Join-Path $downloadStage "python-embed-amd64.zip"
        Write-Log "Downloading embedded Python: $embedUrl"
        Invoke-WebRequest -Uri $embedUrl -OutFile $embedZip -UseBasicParsing
        [System.IO.Compression.ZipFile]::ExtractToDirectory($embedZip, $pythonStage)

        $sitePackages = Join-Path $pythonStage "Lib\site-packages"
        New-Item -ItemType Directory -Force -Path $sitePackages | Out-Null
        $pyInstallerRequirement = Get-PyInstallerRequirement
        Write-Log "Installing PyInstaller into embedded runtime: $pyInstallerRequirement"
        & $Python -m pip install --upgrade --target $sitePackages $pyInstallerRequirement
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to install PyInstaller into embedded Python runtime."
        }
        Set-EmbeddedPythonPathFile -PythonDirectory $pythonStage

        $runtimePython = Join-Path $pythonStage "python.exe"
        & $runtimePython -c "import PyInstaller"
        if ($LASTEXITCODE -ne 0) {
            throw "Embedded Python could not import PyInstaller."
        }
        & $runtimePython -m PyInstaller --version | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "Embedded Python could not run PyInstaller as a module."
        }

        New-ZipFromDirectoryStored -SourceDirectory $pythonStage -DestinationZip $pythonZip
        Write-Log "Python runtime bundle created: $pythonZip"
    }
} catch {
    Write-Log "Failed to prepare Python runtime bundle: $($_.Exception.Message)" -Level "Error"
    throw
}

Write-Log "Step 2: Preparing 7-Zip runtime bundle"
try {
    if (
        (Test-ZipContainsAny -ZipPath $sevenZipZip -EntryNames @("7z.exe", "7za.exe", "7zz.exe")) -and
        ((Get-Item -LiteralPath $sevenZipZip).Length -lt 20MB)
    ) {
        Write-Log "Existing 7-Zip runtime bundle is valid; reusing: $sevenZipZip"
    } else {
        Remove-Item -LiteralPath $sevenZipZip -Force -ErrorAction SilentlyContinue
        $sevenZip = $null
        foreach ($name in @("7z.exe", "7za.exe", "7zz.exe")) {
            $cmd = Get-Command $name -ErrorAction SilentlyContinue
            if ($cmd) {
                $sevenZip = $cmd.Source
                break
            }
        }
        if (-not $sevenZip) {
            foreach ($candidate in @(
                "$env:ProgramFiles\7-Zip\7z.exe",
                "${env:ProgramFiles(x86)}\7-Zip\7z.exe"
            )) {
                if ($candidate -and (Test-Path -LiteralPath $candidate)) {
                    $sevenZip = $candidate
                    break
                }
            }
        }
        if (-not $sevenZip) {
            $msiUrl = "https://www.7-zip.org/a/7z2601-x64.msi"
            $msiArchive = Join-Path $downloadStage "7zip-x64.msi"
            $msiExtract = Join-Path $stageRoot "7zip-msi"
            Write-Log "7-Zip not found locally, downloading MSI: $msiUrl"
            Invoke-WebRequest -Uri $msiUrl -OutFile $msiArchive -UseBasicParsing
            New-Item -ItemType Directory -Force -Path $msiExtract | Out-Null
            $process = Start-Process msiexec.exe -ArgumentList @("/a", $msiArchive, "/qn", "TARGETDIR=$msiExtract") -Wait -PassThru
            if ($process.ExitCode -ne 0) {
                throw "Unable to extract downloaded 7-Zip MSI package. msiexec exit code: $($process.ExitCode)"
            }
            $downloaded = Get-ChildItem -LiteralPath $msiExtract -Recurse -File |
                Where-Object { $_.Name -in @("7z.exe", "7za.exe", "7zz.exe") } |
                Select-Object -First 1
            if (-not $downloaded) {
                throw "Downloaded 7-Zip MSI package did not contain a supported executable."
            }
            $sevenZip = $downloaded.FullName
        }

        Write-Log "Using 7-Zip executable: $sevenZip"
        Copy-Item -LiteralPath $sevenZip -Destination (Join-Path $zipStage (Split-Path -Leaf $sevenZip)) -Force
        $sevenZipDir = Split-Path -Parent $sevenZip
        foreach ($dll in @("7z.dll", "7-zip.dll")) {
            $candidate = Join-Path $sevenZipDir $dll
            if (Test-Path -LiteralPath $candidate) {
                Copy-Item -LiteralPath $candidate -Destination (Join-Path $zipStage $dll) -Force
            }
        }
        $stagedExecutable = Get-ChildItem -LiteralPath $zipStage -Recurse -File |
            Where-Object { $_.Name -in @("7z.exe", "7za.exe", "7zz.exe") } |
            Select-Object -First 1
        if (-not $stagedExecutable) {
            throw "7-Zip runtime stage does not contain a supported executable."
        }
        New-ZipFromDirectoryStored -SourceDirectory $zipStage -DestinationZip $sevenZipZip
        Write-Log "7-Zip runtime bundle created: $sevenZipZip"
    }
} catch {
    Write-Log "Failed to prepare 7-Zip runtime bundle: $($_.Exception.Message)" -Level "Error"
    throw
}

Write-Log "Runtime bundle preparation completed successfully"

[PSCustomObject]@{
    PythonBundle = $pythonZip
    SevenZipBundle = $sevenZipZip
}
