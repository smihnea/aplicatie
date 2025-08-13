"""Configuration management utilities."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from models.config_models import AppConfig
from utils.logger import get_logger


def load_configuration(config_path: Optional[str] = None) -> AppConfig:
    """
    Load application configuration from file or create default.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        AppConfig object with loaded or default settings
    """
    logger = get_logger(__name__)
    
    if config_path is None:
        config_path = _get_default_config_path()
    
    try:
        if os.path.exists(config_path):
            logger.info(f"Loading configuration from: {config_path}")
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                return _dict_to_config(config_data)
        else:
            logger.info("Configuration file not found, creating default configuration")
            config = AppConfig()
            save_configuration(config, config_path)
            return config
            
    except Exception as e:
        logger.warning(f"Failed to load configuration from {config_path}: {str(e)}")
        logger.info("Using default configuration")
        return AppConfig()


def save_configuration(config: AppConfig, config_path: Optional[str] = None) -> None:
    """
    Save application configuration to file.
    
    Args:
        config: AppConfig object to save
        config_path: Optional path to save configuration file
    """
    logger = get_logger(__name__)
    
    if config_path is None:
        config_path = _get_default_config_path()
    
    try:
        # Ensure config directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        config_dict = config.to_dict()
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)
        
        logger.info(f"Configuration saved to: {config_path}")
        
    except Exception as e:
        logger.error(f"Failed to save configuration to {config_path}: {str(e)}")


def _get_default_config_path() -> str:
    """Get the default configuration file path."""
    return os.path.join("config", "settings.yaml")


def _dict_to_config(config_dict: Dict[str, Any]) -> AppConfig:
    """Convert dictionary to AppConfig object."""
    from models.config_models import (
        ScrapingConfig, AzureConfig, OutputConfig, 
        UIConfig, LoggingConfig
    )
    
    # Create config objects from dictionaries
    scraping_config = ScrapingConfig()
    if 'scraping' in config_dict:
        for key, value in config_dict['scraping'].items():
            if hasattr(scraping_config, key):
                setattr(scraping_config, key, value)
    
    azure_config = AzureConfig()
    if 'azure' in config_dict:
        for key, value in config_dict['azure'].items():
            if hasattr(azure_config, key):
                setattr(azure_config, key, value)
    
    output_config = OutputConfig()
    if 'output' in config_dict:
        for key, value in config_dict['output'].items():
            if hasattr(output_config, key):
                setattr(output_config, key, value)
    
    ui_config = UIConfig()
    if 'ui' in config_dict:
        for key, value in config_dict['ui'].items():
            if hasattr(ui_config, key):
                setattr(ui_config, key, value)
    
    logging_config = LoggingConfig()
    if 'logging' in config_dict:
        for key, value in config_dict['logging'].items():
            if hasattr(logging_config, key):
                setattr(logging_config, key, value)
    
    # Create main config object
    config = AppConfig(
        scraping=scraping_config,
        azure=azure_config,
        output=output_config,
        ui=ui_config,
        logging=logging_config
    )
    
    # Set application metadata if present
    if 'app_name' in config_dict:
        config.app_name = config_dict['app_name']
    if 'app_version' in config_dict:
        config.app_version = config_dict['app_version']
    if 'developer' in config_dict:
        config.developer = config_dict['developer']
    
    return config


def get_azure_credentials() -> tuple[Optional[str], Optional[str]]:
    """
    Get Azure credentials from environment variables or config.
    
    Returns:
        Tuple of (endpoint, api_key) or (None, None) if not found
    """
    # Try environment variables first
    endpoint = os.getenv('AZURE_FORM_RECOGNIZER_ENDPOINT')
    api_key = os.getenv('AZURE_FORM_RECOGNIZER_KEY')
    
    if endpoint and api_key:
        return endpoint, api_key
    
    # Try from config file
    try:
        config = load_configuration()
        if config.azure.endpoint and config.azure.api_key:
            return config.azure.endpoint, config.azure.api_key
    except:
        pass
    
    return None, None


def create_default_config_file() -> None:
    """Create a default configuration file with comprehensive settings."""
    config_path = _get_default_config_path()
    
    # Create the configuration directory
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    default_config = {
        'app_name': 'Excel Processor & Web Scraper',
        'app_version': '1.0.0',
        'developer': 'James - Full Stack Developer',
        
        'scraping': {
            'concurrent_requests': 5,
            'timeout': 30,
            'retry_attempts': 3,
            'retry_delay': 1.0,
            'user_agents': [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            ],
            'default_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            },
            'requests_per_second': 2.0,
            'respect_robots_txt': True
        },
        
        'azure': {
            'endpoint': '',
            'api_key': '',
            'confidence_threshold': 0.8,
            'enabled': False,
            'use_fallback_on_failure': True,
            'cost_optimization': True
        },
        
        'output': {
            'preserve_formatting': False,
            'add_metadata': True,
            'backup_originals': True,
            'output_suffix': '_enhanced',
            'output_columns': {
                'ean': 'EAN Code',
                'ral_number': 'RAL Number',
                'net_width': 'Net Width (mm)',
                'net_height': 'Net Height (mm)',
                'net_depth': 'Net Depth (mm)',
                'package_units': 'Package Units',
                'package_weight': 'Package Weight (kg)',
                'extraction_confidence': 'Data Confidence',
                'extraction_method': 'Extraction Method'
            }
        },
        
        'ui': {
            'theme': 'dark',
            'window_width': 1200,
            'window_height': 800,
            'max_file_size_mb': 100,
            'supported_extensions': ['.xlsx', '.xls'],
            'show_detailed_progress': True,
            'auto_scroll_logs': True
        },
        
        'logging': {
            'level': 'INFO',
            'log_to_file': True,
            'log_file_path': 'logs/excel_processor.log',
            'max_log_size_mb': 10,
            'backup_count': 5,
            'colorize_console': True,
            'show_timestamps': True
        }
    }
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(default_config, f, default_flow_style=False, indent=2)
    
    print(f"Default configuration file created at: {config_path}")


if __name__ == "__main__":
    # Create default config file when run directly
    create_default_config_file()