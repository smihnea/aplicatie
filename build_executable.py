#!/usr/bin/env python3
"""
Windows Executable Builder for Excel Product Data Extractor

This script creates a Windows .exe file that can be double-clicked to run.
The executable includes all dependencies and can run on any Windows machine.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import time

def print_banner():
    """Print a nice banner."""
    print("=" * 70)
    print("🏗️  Excel Product Data Extractor - Windows Executable Builder")
    print("=" * 70)
    print()

def check_requirements():
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller
        print("✅ PyInstaller is installed")
        return True
    except ImportError:
        print("❌ PyInstaller not found!")
        print("Installing PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("✅ PyInstaller installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install PyInstaller")
            return False

def create_version_info():
    """Create version info file for Windows executable."""
    version_content = '''# UTF-8
#
# Version information for Excel Product Data Extractor
#

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
        [StringStruct(u'CompanyName', u'Excel Data Processing Tool'),
        StringStruct(u'FileDescription', u'Excel Product Data Extractor'),
        StringStruct(u'FileVersion', u'1.0.0.0'),
        StringStruct(u'InternalName', u'ExcelProductExtractor'),
        StringStruct(u'LegalCopyright', u'© 2024'),
        StringStruct(u'OriginalFilename', u'ExcelProductExtractor.exe'),
        StringStruct(u'ProductName', u'Excel Product Data Extractor'),
        StringStruct(u'ProductVersion', u'1.0.0.0')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)'''
    
    with open('version_info.txt', 'w', encoding='utf-8') as f:
        f.write(version_content)
    print("✅ Created version info file")

def create_simple_icon():
    """Create a simple icon file if none exists."""
    icon_path = Path('app_icon.ico')
    if not icon_path.exists():
        print("ℹ️  No icon file found, executable will use default icon")
        print("   You can add 'app_icon.ico' for a custom icon")

def clean_build_dirs():
    """Clean previous build directories."""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"🧹 Cleaned {dir_name}")

def build_executable():
    """Build the Windows executable."""
    print("\n🔨 Building Windows executable...")
    print("This may take several minutes...")
    
    try:
        # Run PyInstaller with the spec file
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--clean",  # Clean cache
            "excel_processor.spec"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Build completed successfully!")
            return True
        else:
            print("❌ Build failed!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Build error: {e}")
        return False

def check_executable():
    """Check if the executable was created and provide usage instructions."""
    # Check for single file executable (macOS/Linux builds don't use .exe)
    exe_paths = [
        Path("dist/ExcelProductExtractor.exe"),  # Windows
        Path("dist/ExcelProductExtractor"),      # macOS/Linux
        Path("dist/ExcelProductExtractor_dist/ExcelProductExtractor.exe"),  # Windows directory dist
        Path("dist/ExcelProductExtractor_dist/ExcelProductExtractor"),      # macOS/Linux directory dist
    ]
    
    found_exe = None
    for exe_path in exe_paths:
        if exe_path.exists():
            found_exe = exe_path
            break
    
    if found_exe:
        size_mb = found_exe.stat().st_size / (1024 * 1024)
        print(f"\n🎉 SUCCESS! Executable created:")
        print(f"📁 Location: {found_exe.absolute()}")
        print(f"📏 Size: {size_mb:.1f} MB")
        
        if found_exe.name.endswith('.exe'):
            print("\n📋 How to use:")
            print("1. Copy the .exe file to any Windows computer")
            print("2. Double-click the .exe file to run the application")
            print("3. No Python installation required on target machine!")
        else:
            print("\n📋 How to use:")
            print("1. Copy this executable to any compatible computer")
            print("2. Double-click or run from terminal to start the application")
            print("3. No Python installation required on target machine!")
        
        print("\n💡 Tips:")
        print("- The executable includes all dependencies")
        print("- First launch may take a few seconds to extract files")
        print("- You can rename the executable if desired")
        print("- Create a desktop shortcut for easy access")
        
        # If directory distribution exists, mention it
        dir_dist = Path("dist/ExcelProductExtractor_dist")
        if dir_dist.exists():
            print(f"\n📦 Directory distribution also available at:")
            print(f"   {dir_dist.absolute()}")
            print("   This contains the executable plus all dependencies as separate files")
        
        return True
    else:
        print("\n❌ Executable not found! Build may have failed.")
        print("Checked locations:")
        for path in exe_paths:
            print(f"  - {path}")
        print("Check the error messages above.")
        return False

def main():
    """Main build process."""
    print_banner()
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Check requirements
    if not check_requirements():
        return False
    
    # Create necessary files
    create_version_info()
    create_simple_icon()
    
    # Clean previous builds
    print("\n🧹 Cleaning previous builds...")
    clean_build_dirs()
    
    # Build the executable
    start_time = time.time()
    success = build_executable()
    build_time = time.time() - start_time
    
    if success:
        print(f"\n⏱️  Build completed in {build_time:.1f} seconds")
        check_executable()
    else:
        print("\n❌ Build failed. Check the errors above.")
        print("\n🔧 Troubleshooting tips:")
        print("1. Make sure all dependencies are installed: pip install -r requirements.txt")
        print("2. Check that you're in the correct directory")
        print("3. Try running: python start_app.py (to test the app works)")
        print("4. Check Python version (should be 3.8+)")
    
    return success

if __name__ == "__main__":
    success = main()
    
    # Keep window open if run by double-clicking
    if len(sys.argv) == 1:
        input("\nPress Enter to exit...")
    
    sys.exit(0 if success else 1)