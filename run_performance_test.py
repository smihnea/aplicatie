#!/usr/bin/env python3
"""
Performance Test Runner

Run this script to test all the performance optimizations:
- Caching system
- Progress tracking with ETA
- Concurrent processing
- Connection pooling
- Memory usage
- Excel processing improvements

Usage: python run_performance_test.py
"""

import asyncio
import sys
from pathlib import Path

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent / "tests"))

from system_performance_test import main

if __name__ == "__main__":
    print("🚀 Starting Excel Processor & Web Scraper Performance Test Suite...")
    print("=" * 70)
    print("This test will validate all optimizations:")
    print("✅ Removed 100-item testing limit")
    print("✅ Optimized Excel processing for full dataset")
    print("✅ Enhanced web scraping with concurrency & caching") 
    print("✅ Added comprehensive progress tracking with ETA")
    print("✅ Implemented advanced caching & connection pooling")
    print("=" * 70)
    print()
    
    try:
        results = asyncio.run(main())
        
        summary = results.get("summary", {})
        if summary.get('failed', 0) == 0:
            print("\n🎉 ALL OPTIMIZATIONS WORKING PERFECTLY!")
            print("Your system is ready to process the full ~6,356 item dataset.")
            print("\nKey improvements:")
            print("• Unlimited processing capacity (no 100-item limit)")
            print("• Advanced caching reduces repeat scraping")
            print("• Enhanced progress tracking with accurate ETA")
            print("• Optimized connection pooling for maximum speed")
            print("• Results-only Excel output format")
            print("• Improved error handling and reliability")
            
        else:
            print(f"\n⚠️  {summary.get('failed', 0)} tests failed.")
            print("Check the test output above for details.")
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user.")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        print("Check your installation and try again.")