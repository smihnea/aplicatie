"""Strategy manager for selecting appropriate scraping strategies."""

from typing import List, Optional
from urllib.parse import urlparse

from .strategies import ScrapingStrategy, BeautifulSoupStrategy, PlaywrightStrategy, AzureAIStrategy
from utils.logger import get_logger


class StrategyManager:
    """Manages scraping strategies and selects the best one for each URL."""
    
    def __init__(self, azure_endpoint: str = "", azure_api_key: str = ""):
        self.logger = get_logger(__name__)
        self.strategies: List[ScrapingStrategy] = []
        
        # Initialize available strategies
        self._initialize_strategies(azure_endpoint, azure_api_key)
        
        self.logger.info(f"Initialized {len(self.strategies)} scraping strategies")
    
    def _initialize_strategies(self, azure_endpoint: str, azure_api_key: str):
        """Initialize all available scraping strategies."""
        
        # Azure AI Strategy (highest priority if configured)
        if azure_endpoint and azure_api_key:
            try:
                azure_strategy = AzureAIStrategy(azure_endpoint, azure_api_key)
                self.strategies.append(azure_strategy)
                self.logger.info("Azure AI strategy initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Azure AI strategy: {str(e)}")
        
        # Playwright Strategy (for JavaScript-heavy sites)
        try:
            playwright_strategy = PlaywrightStrategy()
            self.strategies.append(playwright_strategy)
            self.logger.info("Playwright strategy initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Playwright strategy: {str(e)}")
        
        # BeautifulSoup Strategy (fallback, always available)
        try:
            bs_strategy = BeautifulSoupStrategy()
            self.strategies.append(bs_strategy)
            self.logger.info("BeautifulSoup strategy initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize BeautifulSoup strategy: {str(e)}")
    
    def select_strategy(self, url: str, prefer_azure: bool = True) -> Optional[ScrapingStrategy]:
        """
        Select the best scraping strategy for a given URL.
        
        Args:
            url: The URL to scrape
            prefer_azure: Whether to prefer Azure AI when available
            
        Returns:
            The best strategy for the URL, or None if no strategy can handle it
        """
        if not self.strategies:
            self.logger.error("No scraping strategies available")
            return None
        
        # Filter strategies that can handle this URL
        compatible_strategies = [s for s in self.strategies if s.can_handle(url)]
        
        if not compatible_strategies:
            # If no specific strategy can handle it, use the last one (usually BeautifulSoup)
            self.logger.info(f"No specific strategy for {url}, using fallback")
            return self.strategies[-1] if self.strategies else None
        
        # Sort by preference and confidence
        if prefer_azure:
            # Prioritize Azure AI if available
            for strategy in compatible_strategies:
                if isinstance(strategy, AzureAIStrategy):
                    self.logger.debug(f"Selected Azure AI strategy for {url}")
                    return strategy
        
        # Select strategy with highest confidence score
        best_strategy = max(compatible_strategies, key=lambda s: s.get_confidence_score())
        self.logger.debug(f"Selected {best_strategy.name} strategy for {url}")
        return best_strategy
    
    def get_strategy_by_name(self, name: str) -> Optional[ScrapingStrategy]:
        """Get a strategy by its name."""
        for strategy in self.strategies:
            if strategy.name.lower() == name.lower():
                return strategy
        return None
    
    def get_available_strategies(self) -> List[str]:
        """Get list of available strategy names."""
        return [strategy.name for strategy in self.strategies]
    
    def is_azure_available(self) -> bool:
        """Check if Azure AI strategy is available."""
        return any(isinstance(s, AzureAIStrategy) for s in self.strategies)
    
    def is_playwright_available(self) -> bool:
        """Check if Playwright strategy is available."""
        return any(isinstance(s, PlaywrightStrategy) for s in self.strategies)
    
    def get_strategy_info(self) -> dict:
        """Get information about all available strategies."""
        return {
            strategy.name: {
                "confidence_score": strategy.get_confidence_score(),
                "class": strategy.__class__.__name__
            }
            for strategy in self.strategies
        }
    
    def test_strategy_compatibility(self, urls: List[str]) -> dict:
        """Test which strategies can handle which URLs."""
        results = {}
        
        for url in urls:
            results[url] = {
                strategy.name: strategy.can_handle(url) 
                for strategy in self.strategies
            }
        
        return results