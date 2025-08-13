"""Logging utilities and configuration."""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Callable
try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

try:
    from colorama import init, Fore, Style
    # Initialize colorama for cross-platform colored output
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    # Fallback color definitions
    class MockColor:
        CYAN = ""
        GREEN = ""
        YELLOW = ""
        RED = ""
        BRIGHT = ""
        RESET_ALL = ""
    
    Fore = MockColor()
    Style = MockColor()


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if COLORAMA_AVAILABLE:
            self.COLORS = {
                'DEBUG': Fore.CYAN,
                'INFO': Fore.GREEN,
                'WARNING': Fore.YELLOW,
                'ERROR': Fore.RED,
                'CRITICAL': Fore.RED + Style.BRIGHT,
            }
        else:
            self.COLORS = {}
    
    def format(self, record):
        if COLORAMA_AVAILABLE:
            log_color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{log_color}{record.levelname}{Style.RESET_ALL}"
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_file_path: Optional[str] = None,
    max_size_mb: int = 10,
    backup_count: int = 5,
    colorize_console: bool = True
) -> None:
    """
    Setup application logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file_path: Path to log file (optional)
        max_size_mb: Maximum log file size in MB
        backup_count: Number of backup log files to keep
        colorize_console: Whether to colorize console output
    """
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)
    
    # Create formatters
    console_format = "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s"
    file_format = "%(asctime)s | %(name)-20s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s"
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    if colorize_console:
        console_formatter = ColoredFormatter(console_format)
    else:
        console_formatter = logging.Formatter(console_format)
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file_path:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        # Rotating file handler to prevent huge log files
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=max_size_mb * 1024 * 1024,  # Convert MB to bytes
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file
        
        file_formatter = logging.Formatter(file_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Configure structlog for structured logging (if available)
    if STRUCTLOG_AVAILABLE:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    # Log startup message
    logger = get_logger("setup")
    logger.info(f"Logging initialized - Level: {level}, File: {log_file_path or 'Console only'}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the specified module.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_performance(func):
    """Decorator to log function execution time."""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = datetime.now()
        
        try:
            result = func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.debug(f"{func.__name__} executed in {execution_time:.3f}s")
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {str(e)}")
            raise
    
    return wrapper


class ProgressLogger:
    """Helper class for logging progress of long-running operations."""
    
    def __init__(self, operation_name: str, total_items: int):
        self.logger = get_logger(f"progress.{operation_name}")
        self.operation_name = operation_name
        self.total_items = total_items
        self.processed_items = 0
        self.start_time = datetime.now()
        self.last_log_time = self.start_time
        
        self.logger.info(f"Starting {operation_name}: {total_items} items to process")
    
    def update(self, items_processed: int = 1, message: Optional[str] = None):
        """Update progress and log if necessary."""
        self.processed_items += items_processed
        current_time = datetime.now()
        
        # Log every 10% or every 30 seconds, whichever comes first
        time_since_last_log = (current_time - self.last_log_time).total_seconds()
        percent_complete = (self.processed_items / self.total_items) * 100
        
        should_log = (
            time_since_last_log >= 30 or  # Every 30 seconds
            (self.total_items > 0 and percent_complete >= (self.processed_items // max(1, self.total_items // 10)) * 10) or  # Every 10%
            self.processed_items == self.total_items  # Completion
        )
        
        if should_log:
            elapsed = (current_time - self.start_time).total_seconds()
            items_per_second = self.processed_items / elapsed if elapsed > 0 else 0
            
            log_msg = (f"{self.operation_name}: {self.processed_items}/{self.total_items} "
                      f"({percent_complete:.1f}%) - {items_per_second:.1f} items/sec")
            
            if message:
                log_msg += f" - {message}"
            
            self.logger.info(log_msg)
            self.last_log_time = current_time
    
    def complete(self, message: Optional[str] = None):
        """Mark operation as complete and log final statistics."""
        total_time = (datetime.now() - self.start_time).total_seconds()
        items_per_second = self.processed_items / total_time if total_time > 0 else 0
        
        log_msg = (f"{self.operation_name} completed: {self.processed_items} items "
                  f"in {total_time:.1f}s ({items_per_second:.1f} items/sec)")
        
        if message:
            log_msg += f" - {message}"
        
        self.logger.info(log_msg)


class AdvancedProgressTracker:
    """Enhanced progress tracker with ETA calculations and detailed metrics."""
    
    def __init__(self, operation_name: str, total_items: int, phase_names: Optional[list] = None):
        self.logger = get_logger(f"progress.{operation_name}")
        self.operation_name = operation_name
        self.total_items = total_items
        self.processed_items = 0
        self.successful_items = 0
        self.failed_items = 0
        self.start_time = datetime.now()
        self.last_log_time = self.start_time
        self.current_phase = 0
        self.phase_names = phase_names or ["Processing"]
        
        # Performance metrics
        self.items_per_second_history = []
        self.last_n_items_times = []  # Track last N item processing times for ETA
        self.max_history_size = 100
        
        # Progress callbacks
        self.progress_callbacks = []
        
        self.logger.info(f"🚀 Starting {operation_name}: {total_items} items across {len(self.phase_names)} phases")
    
    def add_progress_callback(self, callback):
        """Add a callback function that gets called on progress updates."""
        self.progress_callbacks.append(callback)
    
    def set_phase(self, phase_index: int, phase_message: Optional[str] = None):
        """Set the current processing phase."""
        if 0 <= phase_index < len(self.phase_names):
            self.current_phase = phase_index
            phase_name = self.phase_names[phase_index]
            message = f"📍 Entering Phase {phase_index + 1}/{len(self.phase_names)}: {phase_name}"
            if phase_message:
                message += f" - {phase_message}"
            self.logger.info(message)
    
    def update(self, items_processed: int = 1, success: bool = True, message: Optional[str] = None, 
               current_item_description: Optional[str] = None):
        """Update progress with enhanced tracking."""
        current_time = datetime.now()
        
        # Update counters
        self.processed_items += items_processed
        if success:
            self.successful_items += items_processed
        else:
            self.failed_items += items_processed
        
        # Track processing time for this batch
        elapsed_for_batch = (current_time - self.last_log_time).total_seconds()
        if items_processed > 0 and elapsed_for_batch > 0:
            items_per_second = items_processed / elapsed_for_batch
            self.items_per_second_history.append(items_per_second)
            self.last_n_items_times.append(elapsed_for_batch / items_processed)
            
            # Keep only recent history for better ETA accuracy
            if len(self.items_per_second_history) > self.max_history_size:
                self.items_per_second_history.pop(0)
            if len(self.last_n_items_times) > self.max_history_size:
                self.last_n_items_times.pop(0)
        
        # Calculate metrics
        percent_complete = (self.processed_items / self.total_items) * 100 if self.total_items > 0 else 0
        success_rate = (self.successful_items / self.processed_items) * 100 if self.processed_items > 0 else 0
        
        # Determine if we should log
        time_since_last_log = (current_time - self.last_log_time).total_seconds()
        should_log = (
            time_since_last_log >= 15 or  # Every 15 seconds
            self.processed_items % max(1, self.total_items // 20) == 0 or  # Every 5%
            self.processed_items == self.total_items  # Completion
        )
        
        if should_log or message:
            # Calculate ETA
            eta_str = self._calculate_eta()
            current_speed = self._get_current_speed()
            
            # Phase info
            phase_name = self.phase_names[self.current_phase] if self.current_phase < len(self.phase_names) else "Processing"
            
            log_msg = (f"⏳ {phase_name}: {self.processed_items:,}/{self.total_items:,} "
                      f"({percent_complete:.1f}%) | "
                      f"✅ {success_rate:.1f}% success | "
                      f"⚡ {current_speed:.1f}/sec | "
                      f"🕐 ETA: {eta_str}")
            
            if current_item_description:
                log_msg += f" | 📄 {current_item_description}"
            
            if message:
                log_msg += f" | 💬 {message}"
            
            self.logger.info(log_msg)
            
            # Notify callbacks
            for callback in self.progress_callbacks:
                try:
                    callback(self.processed_items, self.total_items, percent_complete, eta_str, current_item_description)
                except Exception as e:
                    self.logger.warning(f"Progress callback failed: {e}")
            
            self.last_log_time = current_time
    
    def _calculate_eta(self) -> str:
        """Calculate estimated time of arrival."""
        if self.processed_items == 0 or self.processed_items >= self.total_items:
            return "Calculating..."
        
        remaining_items = self.total_items - self.processed_items
        
        # Use recent performance data for more accurate ETA
        if len(self.last_n_items_times) >= 5:
            # Use weighted average of recent times (more recent = higher weight)
            weights = [i + 1 for i in range(len(self.last_n_items_times))]
            weighted_avg_time = sum(time * weight for time, weight in zip(self.last_n_items_times, weights)) / sum(weights)
            eta_seconds = remaining_items * weighted_avg_time
        else:
            # Fallback to simple calculation
            elapsed = (datetime.now() - self.start_time).total_seconds()
            avg_time_per_item = elapsed / self.processed_items
            eta_seconds = remaining_items * avg_time_per_item
        
        return self._format_duration(eta_seconds)
    
    def _get_current_speed(self) -> float:
        """Get current processing speed (items per second)."""
        if len(self.items_per_second_history) >= 3:
            # Use recent average for more stable speed display
            recent_speeds = self.items_per_second_history[-10:]
            return sum(recent_speeds) / len(recent_speeds)
        elif self.processed_items > 0:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            return self.processed_items / elapsed if elapsed > 0 else 0
        else:
            return 0.0
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human readable format."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            return f"{minutes:.0f}m {remaining_seconds:.0f}s"
        else:
            hours = seconds // 3600
            remaining_minutes = (seconds % 3600) // 60
            return f"{hours:.0f}h {remaining_minutes:.0f}m"
    
    def complete(self, message: Optional[str] = None):
        """Mark operation as complete with comprehensive statistics."""
        total_time = (datetime.now() - self.start_time).total_seconds()
        avg_speed = self.processed_items / total_time if total_time > 0 else 0
        success_rate = (self.successful_items / self.processed_items) * 100 if self.processed_items > 0 else 0
        
        log_msg = (f"🎉 {self.operation_name} COMPLETED! | "
                  f"📊 {self.processed_items:,} items in {self._format_duration(total_time)} | "
                  f"⚡ {avg_speed:.1f} items/sec average | "
                  f"✅ {success_rate:.1f}% success rate | "
                  f"❌ {self.failed_items:,} failures")
        
        if message:
            log_msg += f" | 💬 {message}"
        
        self.logger.info(log_msg)
        
        # Final callback notification
        for callback in self.progress_callbacks:
            try:
                callback(self.processed_items, self.total_items, 100.0, "Completed", message)
            except Exception as e:
                self.logger.warning(f"Final progress callback failed: {e}")
    
    def get_statistics(self) -> dict:
        """Get current progress statistics."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        current_speed = self._get_current_speed()
        eta_str = self._calculate_eta()
        
        return {
            "operation_name": self.operation_name,
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "successful_items": self.successful_items,
            "failed_items": self.failed_items,
            "percent_complete": (self.processed_items / self.total_items) * 100 if self.total_items > 0 else 0,
            "success_rate": (self.successful_items / self.processed_items) * 100 if self.processed_items > 0 else 0,
            "elapsed_time": elapsed,
            "current_speed": current_speed,
            "eta": eta_str,
            "current_phase": self.current_phase,
            "phase_name": self.phase_names[self.current_phase] if self.current_phase < len(self.phase_names) else "Unknown"
        }