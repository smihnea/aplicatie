"""Web scraping modules."""

from .scraping_engine import ScrapingEngine
from .strategies import (
    ScrapingStrategy, 
    BeautifulSoupStrategy, 
    PlaywrightStrategy,
    AzureAIStrategy
)
from .strategy_manager import StrategyManager

__all__ = [
    "ScrapingEngine",
    "ScrapingStrategy",
    "BeautifulSoupStrategy", 
    "PlaywrightStrategy",
    "AzureAIStrategy",
    "StrategyManager"
]