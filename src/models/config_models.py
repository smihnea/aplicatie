"""Configuration data models."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ScrapingConfig:
    """Web scraping configuration settings."""
    
    concurrent_requests: int = 5
    timeout: int = 30  # seconds
    retry_attempts: int = 3
    retry_delay: float = 1.0  # seconds
    
    # Performance optimizations
    connection_pool_size: int = 25  # Maximum number of connections in pool
    dns_cache_ttl: int = 300  # DNS cache TTL in seconds
    enable_compression: bool = True  # Enable gzip/deflate compression
    
    # User agents for rotation
    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    ])
    
    # Request headers
    default_headers: Dict[str, str] = field(default_factory=lambda: {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive"
    })
    
    # Rate limiting
    requests_per_second: float = 2.0
    respect_robots_txt: bool = True


@dataclass
class AzureConfig:
    """Azure AI service configuration."""
    
    endpoint: str = ""
    api_key: str = ""
    confidence_threshold: float = 0.8
    enabled: bool = False
    
    # Fallback settings
    use_fallback_on_failure: bool = True
    cost_optimization: bool = True  # Use traditional methods for simple cases


@dataclass
class OutputConfig:
    """Output generation configuration."""
    
    preserve_formatting: bool = False
    add_metadata: bool = True
    backup_originals: bool = True
    output_suffix: str = "_enhanced"
    
    # Columns to add for extracted data
    output_columns: Dict[str, str] = field(default_factory=lambda: {
        "ean": "EAN Code",
        "ral_number": "RAL Number", 
        "net_width": "Net Width (mm)",
        "net_height": "Net Height (mm)",
        "net_depth": "Net Depth (mm)",
        "package_units": "Package Units",
        "package_weight": "Package Weight (kg)",
        "extraction_confidence": "Data Confidence",
        "extraction_method": "Extraction Method"
    })


@dataclass
class UIConfig:
    """User interface configuration."""
    
    theme: str = "dark"  # "dark" or "light"
    window_width: int = 1200
    window_height: int = 800
    
    # File upload settings
    max_file_size_mb: int = 100
    supported_extensions: List[str] = field(default_factory=lambda: [".xlsx", ".xls"])
    
    # Progress and feedback
    show_detailed_progress: bool = True
    auto_scroll_logs: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration."""
    
    level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_to_file: bool = True
    log_file_path: str = "logs/excel_processor.log"
    max_log_size_mb: int = 10
    backup_count: int = 5
    
    # Console output
    colorize_console: bool = True
    show_timestamps: bool = True


@dataclass
class AppConfig:
    """Main application configuration."""
    
    scraping: ScrapingConfig = field(default_factory=ScrapingConfig)
    azure: AzureConfig = field(default_factory=AzureConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Application metadata
    app_name: str = "Excel Processor & Web Scraper"
    app_version: str = "1.0.0"
    developer: str = "James - Full Stack Developer"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        return {
            "scraping": self.scraping.__dict__,
            "azure": self.azure.__dict__,
            "output": self.output.__dict__,
            "ui": self.ui.__dict__,
            "logging": self.logging.__dict__,
            "app_name": self.app_name,
            "app_version": self.app_version,
            "developer": self.developer
        }