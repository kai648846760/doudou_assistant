#!/usr/bin/env bash
# macOS build script for DouDou Assistant
# Builds a PyInstaller .app bundle and zips it

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "=== Building DouDou Assistant for macOS ==="

# Clean previous builds unless --skip-clean is passed
if [[ "${1:-}" != "--skip-clean" ]]; then
    echo "Cleaning build artifacts..."
    rm -rf dist build
fi

# Run PyInstaller using the spec file
echo "Running PyInstaller..."
uv run python -m PyInstaller --noconfirm --clean pyinstaller.spec

# Verify the .app was created
APP_PATH="dist/doudou_assistant.app"
if [[ ! -d "$APP_PATH" ]]; then
    echo "ERROR: Expected .app bundle not found at $APP_PATH"
    exit 1
fi

echo "App bundle created at $APP_PATH"

# Zip the .app bundle for distribution
ZIP_NAME="doudou_assistant-mac.zip"
ZIP_PATH="dist/$ZIP_NAME"

echo "Creating zip archive..."
cd dist
rm -f "$ZIP_NAME"
ditto -c -k --sequesterRsrc --keepParent "doudou_assistant.app" "$ZIP_NAME"
cd ..

if [[ ! -f "$ZIP_PATH" ]]; then
    echo "ERROR: Failed to create zip archive"
    exit 1
fi

# Generate SHA256 checksum
echo "Generating SHA256 checksum..."
HASH=$(shasum -a 256 "$ZIP_PATH" | awk '{print $1}')
echo "$HASH  $ZIP_NAME" > "${ZIP_PATH}.sha256"

echo "Artifact created at $ZIP_PATH"
echo "SHA256 checksum written to ${ZIP_PATH}.sha256"
echo "SHA256: $HASH"
echo "=== Build complete ==="
