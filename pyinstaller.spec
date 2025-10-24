# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# Paths to static assets
# SPECPATH is a built-in variable provided by PyInstaller
project_root = Path(SPECPATH)
app_dir = project_root / "app"

# Data files to include: UI assets and JavaScript injectors
datas = [
    (str(app_dir / "ui"), "app/ui"),
    (str(app_dir / "inject.js"), "app"),
    (str(app_dir / "scroll.js"), "app"),
]

a = Analysis(
    [str(app_dir / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

is_mac = sys.platform == "darwin"

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="doudou_assistant",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=is_mac,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

if is_mac:
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="doudou_assistant",
    )
    app = BUNDLE(
        coll,
        name="doudou_assistant.app",
        icon=None,
        bundle_identifier="com.doudou.assistant",
        info_plist={
            "NSHighResolutionCapable": "True",
            "LSMinimumSystemVersion": "10.10.0",
        },
    )
