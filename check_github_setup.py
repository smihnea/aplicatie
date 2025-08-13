#!/usr/bin/env python3
"""
Check GitHub Setup for Excel Product Extractor
Verifies all required files are present and properly configured.
"""

import os
import sys
from pathlib import Path

def check_file(filepath, description):
    """Check if a file exists and print status."""
    if Path(filepath).exists():
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} (MISSING)")
        return False

def check_github_setup():
    """Check if all required files are present for GitHub Actions."""
    print("🔍 Checking GitHub Actions Setup")
    print("=" * 50)
    
    required_files = [
        ("requirements.txt", "Python dependencies"),
        ("excel_processor.spec", "PyInstaller configuration"),
        ("start_app.py", "Application entry point"),
        ("main_modern.py", "Main application file"),
        (".github/workflows/build-executables.yml", "GitHub Actions workflow"),
        ("src/gui/modern_window.py", "GUI module"),
        ("src/utils/config.py", "Configuration module"),
        ("config/settings.yaml", "Application settings"),
    ]
    
    all_present = True
    for filepath, description in required_files:
        if not check_file(filepath, description):
            all_present = False
    
    print("\n" + "=" * 50)
    
    if all_present:
        print("🎉 All required files are present!")
        print("\n📋 Next steps:")
        print("1. Make sure all files are committed to git")
        print("2. Push to GitHub: git push origin main")
        print("3. Check GitHub Actions tab for build status")
        return True
    else:
        print("⚠️  Some required files are missing!")
        print("\n🔧 To fix this:")
        print("1. Make sure you're in the correct directory")
        print("2. Create any missing files")
        print("3. Commit and push to GitHub")
        return False

def check_git_status():
    """Check git status and suggest next steps."""
    print("\n🔄 Git Status Check")
    print("=" * 30)
    
    if not Path(".git").exists():
        print("❌ Not a git repository!")
        print("Initialize with: git init")
        return False
    
    # Check if there are uncommitted changes
    import subprocess
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        if result.stdout.strip():
            print("📝 Uncommitted changes found:")
            print(result.stdout)
            print("\n💡 Commit with:")
            print("   git add .")
            print("   git commit -m 'Fix GitHub Actions setup'")
            print("   git push origin main")
        else:
            print("✅ All changes committed!")
            print("\n📤 Push to GitHub:")
            print("   git push origin main")
        return True
    except FileNotFoundError:
        print("❌ Git not found in PATH")
        return False

if __name__ == "__main__":
    print("🚀 Excel Product Extractor - GitHub Setup Checker")
    print("=" * 60)
    
    setup_ok = check_github_setup()
    git_ok = check_git_status()
    
    print("\n" + "=" * 60)
    if setup_ok and git_ok:
        print("🎯 Ready for GitHub Actions!")
    else:
        print("🔧 Please fix the issues above and try again")
    
    sys.exit(0 if setup_ok and git_ok else 1)