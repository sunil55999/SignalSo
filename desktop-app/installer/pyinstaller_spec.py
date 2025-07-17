#!/usr/bin/env python3
"""
PyInstaller Specification for SignalOS
Creates standalone executable for cross-platform distribution
"""

import sys
import os
from pathlib import Path

# Application details
APP_NAME = "SignalOS"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Trading Signal Automation Platform"

# Get the directory containing this script
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Data files to include
datas = [
    (str(PROJECT_ROOT / "config"), "config"),
    (str(PROJECT_ROOT / "parser" / "lang"), "parser/lang"),
    (str(PROJECT_ROOT / "reports"), "reports"),
    (str(PROJECT_ROOT / "logs"), "logs"),
]

# Hidden imports (modules that PyInstaller might miss)
hiddenimports = [
    'fastapi',
    'uvicorn',
    'aiohttp',
    'websockets',
    'jwt',
    'langdetect',
    'cv2',
    'PIL',
    'easyocr',
    'telethon',
    'telegram',
    'reportlab',
    'matplotlib',
    'numpy',
    'pandas',
    'psutil',
    'requests',
    'asyncio',
    'sqlite3',
    'json',
    'pathlib',
    'logging'
]

# Platform-specific configurations
if sys.platform == "win32":
    icon_file = str(PROJECT_ROOT / "installer" / "icons" / "icon.ico")
    console = False  # Hide console window on Windows
elif sys.platform == "darwin":
    icon_file = str(PROJECT_ROOT / "installer" / "icons" / "icon.icns")
    console = False
else:  # Linux
    icon_file = str(PROJECT_ROOT / "installer" / "icons" / "icon.png")
    console = True

# Exclusions (modules to exclude from bundle)
excludes = [
    'tkinter',
    'matplotlib.backends._tkagg',
    'PyQt5',
    'PyQt6',
    'PySide2',
    'PySide6'
]

# Analysis configuration
a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Remove duplicate files
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Executable configuration
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress executable
    upx_exclude=[],
    runtime_tmpdir=None,
    console=console,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file if os.path.exists(icon_file) else None,
    version=f"installer/version_info.txt"
)

# macOS app bundle configuration
if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name=f"{APP_NAME}.app",
        icon=icon_file,
        bundle_identifier=f"com.signalojs.{APP_NAME.lower()}",
        version=APP_VERSION,
        info_plist={
            'CFBundleShortVersionString': APP_VERSION,
            'CFBundleVersion': APP_VERSION,
            'CFBundleDisplayName': APP_NAME,
            'CFBundleName': APP_NAME,
            'CFBundleIdentifier': f"com.signalojs.{APP_NAME.lower()}",
            'CFBundleExecutable': APP_NAME,
            'CFBundlePackageType': 'APPL',
            'LSMinimumSystemVersion': '10.13.0',
            'NSHighResolutionCapable': True,
            'LSApplicationCategoryType': 'public.app-category.finance',
            'CFBundleDocumentTypes': [],
            'NSPrincipalClass': 'NSApplication',
            'NSSupportsAutomaticGraphicsSwitching': True,
        }
    )


def create_version_info():
    """Create version info file for Windows executable"""
    version_info_content = f"""# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [StringStruct(u'CompanyName', u'SignalOS Team'),
           StringStruct(u'FileDescription', u'{APP_DESCRIPTION}'),
           StringStruct(u'FileVersion', u'{APP_VERSION}'),
           StringStruct(u'InternalName', u'{APP_NAME}'),
           StringStruct(u'LegalCopyright', u'Copyright © 2025 SignalOS Team'),
           StringStruct(u'OriginalFilename', u'{APP_NAME}.exe'),
           StringStruct(u'ProductName', u'{APP_NAME}'),
           StringStruct(u'ProductVersion', u'{APP_VERSION}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    
    version_file = PROJECT_ROOT / "installer" / "version_info.txt"
    version_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(version_file, 'w') as f:
        f.write(version_info_content)
    
    print(f"Created version info file: {version_file}")


def create_build_script():
    """Create platform-specific build script"""
    if sys.platform == "win32":
        script_content = f"""@echo off
echo Building {APP_NAME} for Windows...

REM Clean previous build
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

REM Create version info
python installer/pyinstaller_spec.py

REM Build executable
pyinstaller installer/pyinstaller_spec.py --clean --noconfirm

REM Create installer with NSIS (if available)
if exist "C:\\Program Files (x86)\\NSIS\\makensis.exe" (
    echo Creating Windows installer...
    "C:\\Program Files (x86)\\NSIS\\makensis.exe" installer/windows_installer.nsi
) else (
    echo NSIS not found. Skipping installer creation.
)

echo Build complete! Check the dist/ folder.
pause
"""
        script_name = "build.bat"
        
    else:  # Unix-like systems
        script_content = f"""#!/bin/bash

echo "Building {APP_NAME} for $(uname -s)..."

# Clean previous build
rm -rf dist build

# Create version info
python3 installer/pyinstaller_spec.py

# Build executable
pyinstaller installer/pyinstaller_spec.py --clean --noconfirm

# Create distribution package
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Creating macOS DMG..."
    # Create DMG (requires create-dmg: brew install create-dmg)
    if command -v create-dmg &> /dev/null; then
        create-dmg \\
            --volname "{APP_NAME}" \\
            --window-pos 200 120 \\
            --window-size 800 400 \\
            --icon-size 100 \\
            --icon "{APP_NAME}.app" 200 190 \\
            --hide-extension "{APP_NAME}.app" \\
            --app-drop-link 600 185 \\
            "dist/{APP_NAME}-{APP_VERSION}.dmg" \\
            "dist/"
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Creating Linux AppImage..."
    # Note: AppImage creation would require additional tools
    cd dist
    tar -czf {APP_NAME}-{APP_VERSION}-linux.tar.gz {APP_NAME}
    cd ..
fi

echo "Build complete! Check the dist/ folder."
"""
        script_name = "build.sh"
    
    script_file = PROJECT_ROOT / script_name
    with open(script_file, 'w') as f:
        f.write(script_content)
    
    # Make executable on Unix systems
    if sys.platform != "win32":
        os.chmod(script_file, 0o755)
    
    print(f"Created build script: {script_file}")


def main():
    """Main function to set up PyInstaller build"""
    print(f"Setting up PyInstaller build for {APP_NAME} v{APP_VERSION}")
    
    # Create necessary files
    create_version_info()
    create_build_script()
    
    # Create icons directory if it doesn't exist
    icons_dir = PROJECT_ROOT / "installer" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"""
PyInstaller setup complete!

To build the executable:
  Windows: run build.bat
  macOS/Linux: run ./build.sh

The executable will be created in the dist/ folder.

Required dependencies:
  pip install pyinstaller

Optional (for installers):
  Windows: NSIS (Nullsoft Scriptable Install System)
  macOS: create-dmg (brew install create-dmg)
  Linux: AppImage tools
""")


if __name__ == "__main__":
    # This allows the script to be run directly for setup
    main()
else:
    # This is when PyInstaller imports this as a spec file
    create_version_info()