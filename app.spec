# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all necessary data files and modules
datas = []
datas += collect_data_files('streamlit')
datas += collect_data_files('pandas')

# Add your app files
datas += [
    ('your_main_app.py', '.'),
    ('.env', '.')
]

# All required imports
hiddenimports = [
    'streamlit',
    'pandas',
    'numpy',
    'google.oauth2',
    'google.oauth2.service_account',
    'googleapiclient',
    'googleapiclient.discovery',
    'googleapiclient.http',
    'dotenv',
    'streamlit.web.bootstrap',
    'zipfile',
    'io',
    're',
    'json',
    'datetime'
]

# Collect all submodules
hiddenimports += collect_submodules('streamlit')
hiddenimports += collect_submodules('google')
hiddenimports += collect_submodules('pandas')

a = Analysis(
    ['app_launcher.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LogProcessor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None
)