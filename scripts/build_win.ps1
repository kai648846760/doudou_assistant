# Windows 构建脚本 - 使用 PyInstaller 打包单文件 .exe
# Build script for Windows - Package as single-file .exe using PyInstaller

Write-Host "开始构建 Windows 可执行文件..." -ForegroundColor Green

# 确保 dist 目录存在
if (Test-Path dist) {
    Remove-Item -Recurse -Force dist
}
New-Item -ItemType Directory -Force -Path dist | Out-Null

# 确保 build 目录存在
if (Test-Path build) {
    Remove-Item -Recurse -Force build
}

Write-Host "运行 PyInstaller..." -ForegroundColor Cyan

# 运行 PyInstaller
# --onefile: 打包成单个可执行文件
# --windowed: 无控制台窗口（GUI 应用）
# --name: 输出文件名
# --add-data: 添加 UI 静态资源（格式：源;目标）
# --add-data: 添加 inject.js 和 scroll.js
uv run pyinstaller --onefile --windowed `
    --name DouDouAssistant `
    --add-data "app/ui;app/ui" `
    --add-data "app/inject.js;app" `
    --add-data "app/scroll.js;app" `
    app/main.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "构建失败！" -ForegroundColor Red
    exit 1
}

Write-Host "构建成功！可执行文件位于: dist\DouDouAssistant.exe" -ForegroundColor Green
