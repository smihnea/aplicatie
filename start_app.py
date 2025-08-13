#!/usr/bin/env python3
"""
Excel Processor & Web Scraper - Easy Startup Script

This script will:
1. Create necessary directories
2. Start the optimized application
3. Show helpful information
"""

import os
import sys
from pathlib import Path

def ensure_directories():
    """Create necessary directories."""
    dirs_to_create = [
        "cache/scraping/data",
        "logs",
        "output"
    ]
    
    for dir_path in dirs_to_create:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ Directory ready: {dir_path}")

def main():
    """Start the application with proper setup."""
    print("🚀 Excel Processor & Web Scraper - Starting Up...")
    print("=" * 60)
    
    # Ensure we're in the right directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Create necessary directories
    print("\n📂 Creating directories...")
    ensure_directories()
    
    print("\n🎯 Key Features Enabled:")
    print("✅ Unlimited processing (no 100-item limit)")
    print("✅ Advanced caching (24h disk cache + memory cache)")
    print("✅ Real-time progress tracking with ETA")
    print("✅ Connection pooling (12 concurrent requests)")
    print("✅ Results-only Excel output")
    print("✅ Enhanced error handling")
    
    print("\n🏃 Starting application...")
    print("=" * 60)
    
    try:
        # Import and run the main application
        import main_modern
        main_modern.main()
        
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Make sure you have activated your virtual environment")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Check that you're in the correct directory")

if __name__ == "__main__":
    main()