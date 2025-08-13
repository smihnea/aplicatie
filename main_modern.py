#!/usr/bin/env python3
"""Modern Excel Processor & Web Scraper - Main Entry Point."""

import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    """Main entry point with modern UI."""
    try:
        # Import after path setup
        from utils.config import load_configuration
        from gui.modern_window import ModernExcelProcessorApp
        
        # Load configuration
        config = load_configuration()
        
        # Create and run modern application
        app = ModernExcelProcessorApp(config)
        app.run()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure all dependencies are installed:")
        print("pip install -r requirements-minimal.txt")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 Starting Modern Excel Processor & Web Scraper...")
    main()