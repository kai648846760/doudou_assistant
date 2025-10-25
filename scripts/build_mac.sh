#!/bin/bash
# macOS 构建脚本 - 使用 PyInstaller 打包 .app 并压缩为 zip

set -e

echo "开始构建 macOS 应用..."

# 清理旧的构建产物
rm -rf dist build

echo "运行 PyInstaller..."

uv run pyinstaller --onedir --windowed \
    --name DouDouAssistant \
    --add-data "app/ui:app/ui" \
    --add-data "app/inject.js:app" \
    --add-data "app/scroll.js:app" \
    app/main.py

echo "使用 ditto 压缩 .app..."
cd dist
rm -f DouDouAssistant-macOS.zip
ditto -c -k --sequesterRsrc --keepParent DouDouAssistant.app DouDouAssistant-macOS.zip

echo "构建完成，产物位于 dist/DouDouAssistant-macOS.zip"
