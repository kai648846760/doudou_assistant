# Windows build script for DouDou Assistant
# Builds a PyInstaller single-file executable with embedded assets

param(
    [switch]$SkipClean
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDir "..")

Push-Location $projectRoot
try {
    if (-not $SkipClean) {
        if (Test-Path "dist") {
            Remove-Item -Recurse -Force dist
        }
        if (Test-Path "build") {
            Remove-Item -Recurse -Force build
        }
    }

    $pyInstallerArgs = @(
        "--noconfirm",
        "--clean",
        "pyinstaller.spec"
    )

    Write-Host "Running PyInstaller..." -ForegroundColor Cyan
    uv run python -m PyInstaller @pyInstallerArgs

    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed with exit code $LASTEXITCODE"
    }

    $builtExe = Join-Path $projectRoot "dist/doudou_assistant.exe"
    if (-not (Test-Path $builtExe)) {
        throw "Expected executable not found at $builtExe"
    }

    $artifactPath = Join-Path $projectRoot "dist/doudou_assistant-windows.exe"
    Copy-Item -Path $builtExe -Destination $artifactPath -Force

    $hash = Get-FileHash -Path $artifactPath -Algorithm SHA256
    $hashFile = "$artifactPath.sha256"
    "{0}  {1}" -f $hash.Hash.ToLower(), (Split-Path $artifactPath -Leaf) |
        Set-Content -Path $hashFile -Encoding ascii

    Write-Host "Artifact created at $artifactPath" -ForegroundColor Green
    Write-Host "SHA256 checksum written to $hashFile" -ForegroundColor Green
}
finally {
    Pop-Location
}
