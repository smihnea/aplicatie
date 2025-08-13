# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Excel Product Data Extractor
Builds a Windows executable that includes all dependencies and resources.
"""

import sys
import os
from pathlib import Path

# Define application metadata
APP_NAME = 'ExcelProductExtractor'
APP_VERSION = '1.0.0'
APP_AUTHOR = 'Excel Data Processing Tool'

# Get the application directory
app_dir = Path.cwd()

block_cipher = None

a = Analysis(
    # Entry point - use start_app.py as main entry
    ['start_app.py'],
    
    # Additional paths to search for modules
    pathex=[
        str(app_dir),
        str(app_dir / 'src'),
    ],
    
    # Binary files (none needed for this app)
    binaries=[],
    
    # Data files to include
    datas=[
        # Include configuration files (only if they exist)
        ('config', 'config') if os.path.exists('config') else [],
    ],
    
    # Hidden imports (modules PyInstaller might miss)
    hiddenimports=[
        # GUI framework
        'customtkinter',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        
        # Excel processing
        'openpyxl',
        'openpyxl.utils',
        'openpyxl.styles',
        'openpyxl.workbook',
        'openpyxl.worksheet',
        'pandas',
        'xlrd',
        
        # Web scraping
        'aiohttp',
        'aiohttp.client',
        'aiohttp.connector',
        'beautifulsoup4',
        'bs4',
        'requests',
        'requests.adapters',
        'urllib3',
        
        # HTML parsing
        'lxml',
        'lxml.html',
        'html5lib',
        
        # Data processing
        'pydantic',
        'pydantic.dataclasses',
        'yaml',
        'json',
        
        # Async processing
        'asyncio',
        'concurrent.futures',
        
        # Logging
        'structlog',
        'colorama',
        
        # Application modules
        'src.gui.modern_window',
        'src.models.config_models',
        'src.models.product_data',
        'src.models.processing_result',
        'src.processing.excel_processor',
        'src.processing.excel_hyperlink_extractor',
        'src.processing.integration_processor',
        'src.scraping.scraping_engine',
        'src.scraping.strategies',
        'src.scraping.strategy_manager',
        'src.utils.config',
        'src.utils.logger',
        'src.utils.cache_manager',
        'src.utils.validators',
    ],
    
    # Hook directories
    hookspath=[],
    
    # Runtime hooks
    hooksconfig={},
    
    # Analysis options
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'matplotlib',
        'scipy',
        'numpy.testing',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'black',
        'flake8',
        'mypy',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Create PYZ archive
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Create the executable
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
    upx=True,  # Use UPX compression to reduce file size
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Hide console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Windows-specific options
    # version='version_info.txt',  # Will create this separately
    # icon='app_icon.ico',  # Will create this if needed
)

# Create a COLLECT for directory distribution (alternative to single exe)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME + '_dist'
)