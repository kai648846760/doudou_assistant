#!/bin/bash
# macOS 构建脚本 - 使用 PyInstaller 打包 .app 并压缩为 zip
# Build script for macOS - Package as .app using PyInstaller and compress to zip

set -e

echo "开始构建 macOS 应用..."

# 清理旧的构建产物
rm -rf dist build

echo "运行 PyInstaller..."

# 运行 PyInstaller
# --onedir: 打包成目录形式（macOS .app 需要）
# --windowed: 创建 .app bundle（GUI 应用）
# --name: 输出应用名称
# --add-data: 添加 UI 静态资源（格式：源:目标）
# --add-data: 添加 inject.js 和 scroll.js
uv run pyinstaller --onedir --windowed \
    --name DouDouAssistant \
    --add-data "app/ui:app/ui" \
    --add-data "app/inject.js:app" \
    --add-data "app/scroll.js:app" \
    app/main.py

echo "压缩 .app 为 zip..."
cd dist
zip -r DouDouAssistant.zip DouDouAssistant.app

echo "构建成功！应用位于: dist/DouDouAssistant.zip"
