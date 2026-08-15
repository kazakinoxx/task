# -*- mode: python ; coding: utf-8 -*-


import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--debug", action="store_true")
options = parser.parse_args()

# Setup binaries for windows
import sys
binaries = [('dlls', 'dlls')] if sys.platform == 'win32' else []

# Setup name
name = 'versasens-gui'

if options.debug:
    name += "_DEBUG"


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name=name,
    debug=options.debug,
    bootloader_ignore_signals=False,
    strip=False,
    upx=not options.debug,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=options.debug,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=not options.debug,
    upx_exclude=[],
    name=name,
)