# 检查 Windows 非法路径的脚本（PowerShell 版本）
# 此脚本扫描仓库中所有文件和目录名，找出在 Windows 上不合法的路径

$ErrorActionPreference = "Stop"

Write-Host "🔍 开始检查 Windows 非法路径..." -ForegroundColor Cyan
Write-Host ""

# Windows 非法字符: < > : " / \ | ? *
$invalidChars = '[<>:"|\\\/\?\*]'

# Windows 保留名称
$reservedNames = @(
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
)

$violations = @()
$violationCount = 0

# 获取 git 仓库根目录
try {
    $repoRoot = git rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -ne 0) {
        $repoRoot = Get-Location
    }
    Set-Location $repoRoot
} catch {
    $repoRoot = Get-Location
}

# 获取所有被 git 追踪的文件
try {
    $files = git ls-files 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "警告: 无法获取 git 文件列表，将扫描当前目录" -ForegroundColor Yellow
        $files = Get-ChildItem -Recurse -File | ForEach-Object { $_.FullName.Replace("$repoRoot\", "").Replace("$repoRoot/", "") }
    }
} catch {
    Write-Host "警告: 无法获取 git 文件列表，将扫描当前目录" -ForegroundColor Yellow
    $files = Get-ChildItem -Recurse -File | ForEach-Object { $_.FullName.Replace("$repoRoot\", "").Replace("$repoRoot/", "") }
}

foreach ($file in $files) {
    if ([string]::IsNullOrWhiteSpace($file)) { continue }
    
    # 标准化路径分隔符
    $file = $file -replace '\\', '/'
    
    $filename = Split-Path -Leaf $file
    $dirname = Split-Path -Parent $file
    
    # 检查非法字符
    if ($filename -match $invalidChars) {
        $violations += "❌ 非法字符: $file"
        $violationCount++
        continue
    }
    
    # 检查尾随空格或点
    if ($filename -match '[\s\.]+$') {
        $violations += "❌ 尾随空格或点: $file"
        $violationCount++
        continue
    }
    
    # 检查保留名称
    $filenameUpper = $filename.ToUpper()
    $basenameNoExt = [System.IO.Path]::GetFileNameWithoutExtension($filename).ToUpper()
    
    $isReserved = $false
    foreach ($reserved in $reservedNames) {
        if ($filenameUpper -eq $reserved -or $filenameUpper -eq "$reserved." -or $basenameNoExt -eq $reserved) {
            $violations += "❌ Windows 保留名称: $file"
            $violationCount++
            $isReserved = $true
            break
        }
    }
    if ($isReserved) { continue }
    
    # 检查路径中的所有目录组件
    if ($dirname) {
        $pathParts = $dirname -split '/'
        $dirViolation = $false
        foreach ($part in $pathParts) {
            if ([string]::IsNullOrWhiteSpace($part)) { continue }
            
            # 检查目录名非法字符
            if ($part -match $invalidChars) {
                $violations += "❌ 目录名含非法字符: $file"
                $violationCount++
                $dirViolation = $true
                break
            }
            
            # 检查目录名尾随空格或点
            if ($part -match '[\s\.]+$') {
                $violations += "❌ 目录名尾随空格或点: $file"
                $violationCount++
                $dirViolation = $true
                break
            }
            
            # 检查目录保留名称
            $partUpper = $part.ToUpper()
            foreach ($reserved in $reservedNames) {
                if ($partUpper -eq $reserved) {
                    $violations += "❌ 目录是 Windows 保留名称: $file"
                    $violationCount++
                    $dirViolation = $true
                    break
                }
            }
            if ($dirViolation) { break }
        }
    }
}

# 输出结果
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

if ($violationCount -eq 0) {
    Write-Host "✅ 太好了！未发现 Windows 非法路径。" -ForegroundColor Green
    Write-Host ""
    Write-Host "所有文件名都符合 Windows 文件系统要求。"
    exit 0
} else {
    Write-Host "❌ 发现 $violationCount 个 Windows 非法路径：" -ForegroundColor Red
    Write-Host ""
    foreach ($violation in $violations) {
        Write-Host $violation -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "📋 Windows 文件名限制说明：" -ForegroundColor Yellow
    Write-Host "• 不能包含字符: < > : `" / \ | ? *"
    Write-Host "• 不能以空格或点结尾"
    Write-Host "• 不能使用保留名称: CON, PRN, AUX, NUL, COM1-9, LPT1-9"
    Write-Host ""
    Write-Host "请重命名或删除上述文件后再提交代码。"
    exit 1
}
