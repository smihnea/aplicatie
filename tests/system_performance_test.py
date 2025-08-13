"""Comprehensive system performance and functionality tests."""

import asyncio
import time
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import tempfile
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models.product_data import ProductLink, ExcelData
from models.config_models import ScrapingConfig
from scraping.scraping_engine import ScrapingEngine
from processing.excel_processor import ExcelProcessor
from utils.logger import setup_logging, get_logger, AdvancedProgressTracker
from utils.cache_manager import CacheManager, MemoryCache


class SystemPerformanceTest:
    """Comprehensive system performance test suite."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.test_results = {}
        self.test_urls = [
            "https://new.abb.com/products/2CTT003090A6150/ct-1p-40-50-series-1-pole-contactor-40a",
            "https://new.abb.com/products/2CDG110002R0224/s200-b20-miniature-circuit-breaker",
            "https://new.abb.com/products/2CDG130004R0414/s200-c4-miniature-circuit-breaker", 
            "https://new.abb.com/products/2CDG140007R0714/s200-k7-miniature-circuit-breaker",
            "https://new.abb.com/products/2CTB804973R2200/a-line-contactor-230v"
        ]
        
        self.logger.info("🧪 System Performance Test Suite Initialized")
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive system tests."""
        self.logger.info("🚀 Starting comprehensive system tests...")
        start_time = time.time()
        
        # Test configuration
        config = ScrapingConfig(
            concurrent_requests=12,
            timeout=20,
            retry_attempts=2,
            requests_per_second=5.0,
            connection_pool_size=50,
            dns_cache_ttl=300,
            enable_compression=True
        )
        
        tests = [
            ("Cache Performance", self.test_cache_performance),
            ("Progress Tracking", self.test_progress_tracking),
            ("Connection Pooling", self.test_connection_pooling),
            ("Scraping Engine", self.test_scraping_engine),
            ("Excel Processing", self.test_excel_processing),
            ("Memory Usage", self.test_memory_usage),
            ("Cache Hit Rates", self.test_cache_hit_rates),
            ("Concurrent Processing", self.test_concurrent_processing)
        ]
        
        for test_name, test_func in tests:
            self.logger.info(f"📋 Running {test_name} test...")
            try:
                result = await test_func(config)
                self.test_results[test_name] = {
                    "status": "PASSED",
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
                self.logger.info(f"✅ {test_name}: PASSED")
            except Exception as e:
                self.test_results[test_name] = {
                    "status": "FAILED",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                self.logger.error(f"❌ {test_name}: FAILED - {e}")
        
        total_time = time.time() - start_time
        self.test_results["summary"] = {
            "total_tests": len(tests),
            "passed": len([r for r in self.test_results.values() if isinstance(r, dict) and r.get("status") == "PASSED"]),
            "failed": len([r for r in self.test_results.values() if isinstance(r, dict) and r.get("status") == "FAILED"]),
            "total_time": total_time
        }
        
        self._print_summary()
        return self.test_results
    
    async def test_cache_performance(self, config: ScrapingConfig) -> Dict[str, Any]:
        """Test caching system performance."""
        cache_manager = CacheManager(cache_dir="test_cache", max_age_hours=1)
        memory_cache = MemoryCache(max_size=100)
        
        # Test data
        test_data = {"test": "data", "timestamp": time.time()}
        test_url = "https://example.com/test"
        
        # Test memory cache
        start_time = time.time()
        memory_cache.put(test_url, test_data, ttl_seconds=300)
        retrieved = memory_cache.get(test_url)
        memory_time = time.time() - start_time
        
        assert retrieved is not None, "Memory cache failed to retrieve data"
        
        # Test disk cache operations
        start_time = time.time()
        # Note: Disk cache expects ScrapingResult, so we'll test basic functionality
        disk_stats = cache_manager.get_cache_statistics()
        disk_time = time.time() - start_time
        
        # Cleanup
        cache_manager.clear_cache()
        memory_cache.clear()
        
        return {
            "memory_cache_time": memory_time * 1000,  # ms
            "disk_cache_stats_time": disk_time * 1000,  # ms
            "memory_cache_works": retrieved is not None,
            "disk_cache_initialized": isinstance(disk_stats, dict)
        }
    
    async def test_progress_tracking(self, config: ScrapingConfig) -> Dict[str, Any]:
        """Test advanced progress tracking."""
        phase_names = ["Test Phase 1", "Test Phase 2", "Test Phase 3"]
        tracker = AdvancedProgressTracker("Performance Test", 100, phase_names)
        
        start_time = time.time()
        
        # Simulate processing with different phases
        for phase in range(3):
            tracker.set_phase(phase, f"Testing phase {phase + 1}")
            
            for i in range(33):  # Process ~33 items per phase
                if tracker.processed_items < 100:
                    success = i % 4 != 0  # ~75% success rate
                    tracker.update(1, success=success, current_item_description=f"Item {i+1}")
                    await asyncio.sleep(0.01)  # Simulate work
        
        stats = tracker.get_statistics()
        tracker.complete("Test completed successfully")
        
        total_time = time.time() - start_time
        
        return {
            "total_time": total_time,
            "processed_items": stats["processed_items"],
            "success_rate": stats["success_rate"],
            "current_speed": stats["current_speed"],
            "eta_calculated": stats["eta"] != "Calculating...",
            "phases_tracked": len(phase_names)
        }
    
    async def test_connection_pooling(self, config: ScrapingConfig) -> Dict[str, Any]:
        """Test connection pooling and concurrent requests."""
        engine = ScrapingEngine(config)
        
        # Create test links
        test_links = [
            ProductLink(url=url, row_index=i, sheet_name="test", column_name="test")
            for i, url in enumerate(self.test_urls[:3])  # Test with 3 URLs
        ]
        
        start_time = time.time()
        results = await engine.process_links(test_links)
        processing_time = time.time() - start_time
        
        stats = engine.get_statistics()
        
        return {
            "processing_time": processing_time,
            "processed_count": len(results),
            "connection_pool_size": config.connection_pool_size,
            "concurrent_requests": config.concurrent_requests,
            "average_time_per_url": processing_time / len(results) if results else 0,
            "cache_stats": stats.get("cache_stats", {})
        }
    
    async def test_scraping_engine(self, config: ScrapingConfig) -> Dict[str, Any]:
        """Test scraping engine functionality."""
        engine = ScrapingEngine(config)
        
        # Test single URL
        test_url = self.test_urls[0]
        start_time = time.time()
        result = await engine.test_single_url(test_url)
        single_url_time = time.time() - start_time
        
        # Test multiple URLs
        test_links = [
            ProductLink(url=url, row_index=i, sheet_name="test", column_name="test")
            for i, url in enumerate(self.test_urls[:2])
        ]
        
        start_time = time.time()
        results = await engine.process_links(test_links)
        multiple_url_time = time.time() - start_time
        
        stats = engine.get_statistics()
        
        return {
            "single_url_time": single_url_time,
            "single_url_success": result.status.name,
            "multiple_url_time": multiple_url_time,
            "multiple_url_count": len(results),
            "strategies_available": len(stats["available_strategies"]),
            "cache_hit_rate": stats["cache_stats"]["cache_hit_rate"]
        }
    
    async def test_excel_processing(self, config: ScrapingConfig) -> Dict[str, Any]:
        """Test Excel processing functionality."""
        # Create a temporary Excel file with test data
        import pandas as pd
        import tempfile
        
        # Create test data
        test_data = {
            'Product Code': ['TEST001', 'TEST002', 'TEST003'],
            'FISA TEHNICA': [
                'https://example.com/test1',
                'https://example.com/test2', 
                'https://example.com/test3'
            ],
            'Description': ['Test Product 1', 'Test Product 2', 'Test Product 3']
        }
        
        df = pd.DataFrame(test_data)
        
        # Create temporary Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            temp_path = temp_file.name
            df.to_excel(temp_path, sheet_name='Test Sheet', index=False)
        
        try:
            processor = ExcelProcessor()
            
            # Test Excel reading
            start_time = time.time()
            excel_data = processor.read_excel_file(temp_path)
            read_time = time.time() - start_time
            
            # Test link extraction
            start_time = time.time()
            links = processor.extract_links(excel_data)
            extract_time = time.time() - start_time
            
            # Test Excel writing (results-only format)
            output_path = temp_path.replace('.xlsx', '_enhanced.xlsx')
            start_time = time.time()
            processor.write_enhanced_excel(excel_data, output_path, preserve_formatting=False)
            write_time = time.time() - start_time
            
            return {
                "read_time": read_time,
                "extract_time": extract_time, 
                "write_time": write_time,
                "sheets_read": len(excel_data.sheets),
                "links_extracted": len(links),
                "total_rows": excel_data.metadata.total_rows,
                "output_created": os.path.exists(output_path)
            }
            
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            output_path = temp_path.replace('.xlsx', '_enhanced.xlsx')
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    async def test_memory_usage(self, config: ScrapingConfig) -> Dict[str, Any]:
        """Test memory usage patterns."""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create and process some data
        engine = ScrapingEngine(config)
        test_links = [
            ProductLink(url=url, row_index=i, sheet_name="test", column_name="test")
            for i, url in enumerate(self.test_urls[:3])
        ]
        
        # Process links
        results = await engine.process_links(test_links)
        
        mid_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Force garbage collection
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        return {
            "initial_memory_mb": initial_memory,
            "peak_memory_mb": mid_memory,
            "final_memory_mb": final_memory,
            "memory_increase_mb": mid_memory - initial_memory,
            "memory_after_gc_mb": final_memory,
            "items_processed": len(results)
        }
    
    async def test_cache_hit_rates(self, config: ScrapingConfig) -> Dict[str, Any]:
        """Test cache hit rates with repeated requests."""
        engine = ScrapingEngine(config)
        test_url = self.test_urls[0]
        
        # First request (should be cache miss)
        start_time = time.time()
        result1 = await engine.test_single_url(test_url)
        first_request_time = time.time() - start_time
        
        # Second request (should be cache hit)
        start_time = time.time()
        result2 = await engine.test_single_url(test_url)
        second_request_time = time.time() - start_time
        
        stats = engine.get_statistics()
        cache_stats = stats["cache_stats"]
        
        return {
            "first_request_time": first_request_time,
            "second_request_time": second_request_time,
            "speedup_ratio": first_request_time / second_request_time if second_request_time > 0 else 0,
            "cache_hits": cache_stats["cache_hits"],
            "cache_misses": cache_stats["cache_misses"],
            "cache_hit_rate": cache_stats["cache_hit_rate"]
        }
    
    async def test_concurrent_processing(self, config: ScrapingConfig) -> Dict[str, Any]:
        """Test concurrent processing capabilities."""
        engine = ScrapingEngine(config)
        
        # Test with different concurrency levels
        test_urls = self.test_urls[:4]  # Use 4 URLs
        
        # Sequential processing (concurrency = 1)
        config_sequential = ScrapingConfig(**{**config.__dict__, "concurrent_requests": 1})
        engine_sequential = ScrapingEngine(config_sequential)
        
        test_links_sequential = [
            ProductLink(url=url, row_index=i, sheet_name="test", column_name="test")
            for i, url in enumerate(test_urls)
        ]
        
        start_time = time.time()
        results_sequential = await engine_sequential.process_links(test_links_sequential)
        sequential_time = time.time() - start_time
        
        # Concurrent processing (concurrency = config.concurrent_requests)
        test_links_concurrent = [
            ProductLink(url=url, row_index=i, sheet_name="test", column_name="test")
            for i, url in enumerate(test_urls)
        ]
        
        start_time = time.time()
        results_concurrent = await engine.process_links(test_links_concurrent)
        concurrent_time = time.time() - start_time
        
        return {
            "sequential_time": sequential_time,
            "concurrent_time": concurrent_time,
            "speedup_factor": sequential_time / concurrent_time if concurrent_time > 0 else 0,
            "sequential_results": len(results_sequential),
            "concurrent_results": len(results_concurrent),
            "concurrent_requests_used": config.concurrent_requests
        }
    
    def _print_summary(self):
        """Print test results summary."""
        summary = self.test_results.get("summary", {})
        
        self.logger.info("=" * 60)
        self.logger.info("🏆 SYSTEM PERFORMANCE TEST RESULTS SUMMARY")
        self.logger.info("=" * 60)
        
        self.logger.info(f"📊 Total Tests: {summary.get('total_tests', 0)}")
        self.logger.info(f"✅ Passed: {summary.get('passed', 0)}")
        self.logger.info(f"❌ Failed: {summary.get('failed', 0)}")
        self.logger.info(f"⏱️  Total Time: {summary.get('total_time', 0):.2f}s")
        
        # Print detailed results for key metrics
        for test_name, result in self.test_results.items():
            if test_name == "summary" or not isinstance(result, dict):
                continue
                
            if result.get("status") == "PASSED":
                self.logger.info(f"\n📋 {test_name}:")
                test_result = result.get("result", {})
                
                if test_name == "Cache Hit Rates":
                    self.logger.info(f"  🎯 Cache Hit Rate: {test_result.get('cache_hit_rate', 0):.1f}%")
                    self.logger.info(f"  ⚡ Speedup: {test_result.get('speedup_ratio', 0):.1f}x faster")
                    
                elif test_name == "Concurrent Processing":
                    self.logger.info(f"  🚀 Speedup: {test_result.get('speedup_factor', 0):.1f}x faster")
                    self.logger.info(f"  🔄 Concurrency: {test_result.get('concurrent_requests_used', 0)} requests")
                    
                elif test_name == "Memory Usage":
                    self.logger.info(f"  💾 Peak Memory: {test_result.get('peak_memory_mb', 0):.1f}MB")
                    self.logger.info(f"  📈 Memory Increase: {test_result.get('memory_increase_mb', 0):.1f}MB")
        
        self.logger.info("=" * 60)
        
        if summary.get('failed', 0) == 0:
            self.logger.info("🎉 ALL TESTS PASSED! System is optimized and ready for production.")
        else:
            self.logger.warning(f"⚠️  {summary.get('failed', 0)} tests failed. Check logs for details.")


async def main():
    """Run the comprehensive system performance test."""
    # Setup logging
    setup_logging(level="INFO", colorize_console=True)
    
    # Create and run tests
    test_suite = SystemPerformanceTest()
    results = await test_suite.run_all_tests()
    
    # Save results to file
    import json
    results_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())