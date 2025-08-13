"""Main scraping engine with async processing capabilities."""

import asyncio
import aiohttp
import random
from typing import List, Optional, Dict, Callable, Any
from datetime import datetime
import time

from models.product_data import ProductLink, ProductData
from models.processing_result import ScrapingResult, ProcessingStatus
from models.config_models import ScrapingConfig
from .strategy_manager import StrategyManager
from utils.logger import get_logger, ProgressLogger, AdvancedProgressTracker
from utils.cache_manager import CacheManager, MemoryCache


class ScrapingEngine:
    """Main engine for web scraping with concurrent processing."""
    
    def __init__(self, config: ScrapingConfig, azure_endpoint: str = "", azure_api_key: str = ""):
        self.config = config
        self.logger = get_logger(__name__)
        
        # Initialize strategy manager
        self.strategy_manager = StrategyManager(azure_endpoint, azure_api_key)
        
        # Initialize caching systems
        self.disk_cache = CacheManager(cache_dir="cache/scraping", max_age_hours=24)
        self.memory_cache = MemoryCache(max_size=1000)  # Cache for frequently accessed URLs
        
        # Processing state
        self.is_processing = False
        self.processed_count = 0
        self.total_count = 0
        
        # Cache statistics
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0 / config.requests_per_second
        
        # User agent rotation
        self.user_agent_index = 0
        
        self.logger.info(f"Scraping engine initialized with {len(config.user_agents)} user agents")
        self.logger.info(f"Performance settings: {config.concurrent_requests} concurrent, "
                        f"{config.connection_pool_size} pool size, {config.dns_cache_ttl}s DNS TTL")
        self.logger.info("Cache systems initialized: disk cache (24h TTL) + memory cache (1000 items)")
    
    async def process_links(
        self,
        links: List[ProductLink],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        result_callback: Optional[Callable[[ScrapingResult], None]] = None
    ) -> List[ScrapingResult]:
        """
        Process multiple product links concurrently.
        
        Args:
            links: List of ProductLink objects to process
            progress_callback: Optional callback for progress updates (processed, total, current_url)
            result_callback: Optional callback for each completed result
            
        Returns:
            List of ScrapingResult objects
        """
        if self.is_processing:
            raise RuntimeError("Scraping engine is already processing")
        
        self.is_processing = True
        self.total_count = len(links)
        self.processed_count = 0
        
        self.logger.info(f"Starting to process {len(links)} links")
        phase_names = ["Link Extraction", "Web Scraping", "Data Processing"]
        progress_tracker = AdvancedProgressTracker("Advanced Web Scraping", len(links), phase_names)
        progress_tracker.set_phase(1, f"Processing {len(links)} product URLs")
        
        try:
            # Create semaphore to limit concurrent requests
            semaphore = asyncio.Semaphore(self.config.concurrent_requests)
            
            # Create aiohttp session with optimized configuration
            import ssl
            connector = aiohttp.TCPConnector(
                limit=self.config.connection_pool_size,
                limit_per_host=self.config.concurrent_requests,
                ttl_dns_cache=self.config.dns_cache_ttl,
                use_dns_cache=True,
                enable_cleanup_closed=True,  # Enable connection cleanup
                keepalive_timeout=60,  # Keep connections alive longer
                ssl=False  # Disable SSL verification for internal tool
            )
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            
            # Configure headers with compression and user agent rotation
            session_headers = self.config.default_headers.copy()
            session_headers['User-Agent'] = self._get_next_user_agent()
            if self.config.enable_compression and 'Accept-Encoding' in session_headers:
                # Ensure compression is enabled
                session_headers['Accept-Encoding'] = 'gzip, deflate, br'
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=session_headers
            ) as session:
                
                # Create tasks for concurrent processing
                tasks = [
                    self._process_single_link(
                        link, 
                        session, 
                        semaphore,
                        progress_callback,
                        result_callback,
                        progress_tracker
                    )
                    for link in links
                ]
                
                # Execute all tasks concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results and handle exceptions
                scraping_results = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Task failed for {links[i].url}: {str(result)}")
                        # Create failed result
                        failed_result = ScrapingResult(
                            url=links[i].url,
                            status=ProcessingStatus.FAILED,
                            error_message=str(result),
                            attempts=self.config.retry_attempts
                        )
                        scraping_results.append(failed_result)
                    else:
                        scraping_results.append(result)
                
                progress_tracker.complete(f"{len(scraping_results)} links processed")
                self.logger.info(f"Completed processing {len(scraping_results)} links")
                
                return scraping_results
                
        except Exception as e:
            self.logger.error(f"Scraping engine failed: {str(e)}")
            raise
        
        finally:
            self.is_processing = False
    
    async def _process_single_link(
        self,
        link: ProductLink,
        session: aiohttp.ClientSession,
        semaphore: asyncio.Semaphore,
        progress_callback: Optional[Callable[[int, int, str], None]],
        result_callback: Optional[Callable[[ScrapingResult], None]],
        progress_tracker: AdvancedProgressTracker
    ) -> ScrapingResult:
        """Process a single product link."""
        
        async with semaphore:  # Limit concurrent requests
            start_time = time.time()
            
            # Rate limiting
            await self._rate_limit()
            
            result = ScrapingResult(
                url=link.url,
                status=ProcessingStatus.IN_PROGRESS,
                attempts=0
            )
            
            try:
                self.logger.debug(f"Processing link: {link.url}")
                
                # Check caches first (memory cache -> disk cache -> actual scraping)
                cached_result = self._check_caches(link.url)
                if cached_result:
                    self.cache_hits += 1
                    self.logger.debug(f"Cache hit for {link.url}")
                    
                    # Update the link with cached data
                    if cached_result.data:
                        link.extracted_data = cached_result.data
                        link.processed = True
                    else:
                        link.processing_error = cached_result.error_message
                    
                    return cached_result
                
                self.cache_misses += 1
                
                # Select appropriate scraping strategy
                strategy = self.strategy_manager.select_strategy(link.url)
                if not strategy:
                    raise Exception("No suitable scraping strategy found")
                
                result.extraction_method = strategy.name
                
                # Attempt extraction with retries
                extracted_data = None
                last_error = None
                
                for attempt in range(self.config.retry_attempts):
                    result.attempts = attempt + 1
                    
                    try:
                        extracted_data = await strategy.extract_data(link.url, session)
                        if extracted_data and extracted_data.is_valid():
                            break
                        else:
                            last_error = "No valid data extracted"
                            
                    except Exception as e:
                        last_error = str(e)
                        self.logger.warning(f"Attempt {attempt + 1} failed for {link.url}: {str(e)}")
                        
                        if attempt < self.config.retry_attempts - 1:
                            await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                
                # Finalize result
                if extracted_data and extracted_data.is_valid():
                    result.status = ProcessingStatus.COMPLETED
                    result.data = extracted_data
                    link.extracted_data = extracted_data
                    link.processed = True
                else:
                    result.status = ProcessingStatus.FAILED
                    result.error_message = last_error or "Failed to extract valid data"
                    link.processing_error = result.error_message
                
                # Cache the result (both successful and failed results)
                self._cache_result(link.url, result)
                
            except Exception as e:
                result.status = ProcessingStatus.FAILED
                result.error_message = str(e)
                link.processing_error = result.error_message
                self.logger.error(f"Failed to process {link.url}: {str(e)}")
            
            # Calculate processing time
            result.processing_time = time.time() - start_time
            
            # Update counters and progress tracking
            self.processed_count += 1
            success = (result.status == ProcessingStatus.COMPLETED)
            
            # Update progress callback with current count
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback(self.processed_count, self.total_count, link.url)
                else:
                    progress_callback(self.processed_count, self.total_count, link.url)
            
            # Extract domain for better tracking
            try:
                from urllib.parse import urlparse
                domain = urlparse(link.url).netloc
                item_description = f"{domain} - {link.url.split('/')[-1][:30]}"
            except:
                item_description = link.url[:50]
            
            progress_tracker.update(
                items_processed=1, 
                success=success, 
                current_item_description=item_description
            )
            
            if result_callback:
                result_callback(result)
            
            return result
    
    async def _rate_limit(self):
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _check_caches(self, url: str) -> Optional[ScrapingResult]:
        """Check memory and disk caches for existing result."""
        # Check memory cache first (fastest)
        memory_result = self.memory_cache.get(url)
        if memory_result:
            return memory_result
        
        # Check disk cache
        disk_result = self.disk_cache.get_cached_result(url)
        if disk_result:
            # Store in memory cache for faster future access
            self.memory_cache.put(url, disk_result, ttl_seconds=300)  # 5 minutes in memory
            return disk_result
        
        return None
    
    def _cache_result(self, url: str, result: ScrapingResult):
        """Cache the scraping result in both memory and disk caches."""
        try:
            # Cache in memory (short-term, fast access)
            self.memory_cache.put(url, result, ttl_seconds=300)  # 5 minutes
            
            # Cache on disk (long-term, persistent)
            self.disk_cache.cache_result(url, result)
            
        except Exception as e:
            self.logger.warning(f"Failed to cache result for {url}: {e}")
    
    def _get_next_user_agent(self) -> str:
        """Get the next user agent for rotation."""
        if not self.config.user_agents:
            return "Mozilla/5.0 (compatible; ScrapingBot/1.0)"
        
        user_agent = self.config.user_agents[self.user_agent_index]
        self.user_agent_index = (self.user_agent_index + 1) % len(self.config.user_agents)
        return user_agent
    
    async def test_single_url(self, url: str) -> ScrapingResult:
        """Test scraping a single URL for debugging purposes."""
        self.logger.info(f"Testing single URL: {url}")
        
        # Create a temporary link object
        test_link = ProductLink(url=url, row_index=0, sheet_name="test")
        
        # Process with a temporary session using optimized configuration
        connector = aiohttp.TCPConnector(
            limit=1,
            ttl_dns_cache=self.config.dns_cache_ttl,
            use_dns_cache=True,
            ssl=False
        )
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        
        # Configure headers with compression and user agent rotation
        session_headers = self.config.default_headers.copy()
        session_headers['User-Agent'] = self._get_next_user_agent()
        if self.config.enable_compression and 'Accept-Encoding' in session_headers:
            session_headers['Accept-Encoding'] = 'gzip, deflate, br'
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=session_headers
        ) as session:
            
            semaphore = asyncio.Semaphore(1)
            progress_tracker = AdvancedProgressTracker("URL Test", 1, ["Testing"])
            progress_tracker.set_phase(0, f"Testing URL: {url}")
            
            result = await self._process_single_link(
                test_link, 
                session, 
                semaphore,
                None,  # No progress callback
                None,  # No result callback
                progress_tracker
            )
            
            progress_tracker.complete("URL test completed")
            return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get scraping engine statistics including cache performance."""
        cache_hit_rate = (self.cache_hits / (self.cache_hits + self.cache_misses) * 100) if (self.cache_hits + self.cache_misses) > 0 else 0
        
        return {
            "is_processing": self.is_processing,
            "processed_count": self.processed_count,
            "total_count": self.total_count,
            "available_strategies": self.strategy_manager.get_available_strategies(),
            "strategy_info": self.strategy_manager.get_strategy_info(),
            "cache_stats": {
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "cache_hit_rate": cache_hit_rate,
                "memory_cache": self.memory_cache.get_stats(),
                "disk_cache": self.disk_cache.get_cache_statistics()
            },
            "config": {
                "concurrent_requests": self.config.concurrent_requests,
                "timeout": self.config.timeout,
                "retry_attempts": self.config.retry_attempts,
                "requests_per_second": self.config.requests_per_second,
                "connection_pool_size": self.config.connection_pool_size,
                "dns_cache_ttl": self.config.dns_cache_ttl,
                "enable_compression": self.config.enable_compression
            }
        }
    
    def clear_cache(self, older_than_hours: Optional[int] = None):
        """Clear cache entries."""
        self.memory_cache.clear()
        removed_count = self.disk_cache.clear_cache(older_than_hours)
        self.logger.info(f"Cache cleared: {removed_count} entries removed")
        
        # Reset cache statistics
        self.cache_hits = 0
        self.cache_misses = 0
        
        return removed_count
    
    def cleanup_expired_cache(self) -> int:
        """Clean up expired cache entries."""
        return self.disk_cache.cleanup_expired()
    
    def stop_processing(self):
        """Stop current processing (graceful shutdown)."""
        if self.is_processing:
            self.logger.info("Stopping scraping engine...")
            # Note: This is a flag - actual stopping depends on task cancellation
            # in the calling code
            self.is_processing = False