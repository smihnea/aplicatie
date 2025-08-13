"""Processing result models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from .product_data import ProductData


class ProcessingStatus(Enum):
    """Status of processing operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScrapingResult:
    """Result of a single web scraping operation."""
    
    url: str
    status: ProcessingStatus
    data: Optional[ProductData] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0  # in seconds
    attempts: int = 0
    extraction_method: str = "unknown"
    created_at: datetime = field(default_factory=datetime.now)
    
    def is_successful(self) -> bool:
        """Check if scraping was successful."""
        return self.status == ProcessingStatus.COMPLETED and self.data is not None
    
    def get_confidence_score(self) -> float:
        """Get confidence score of extracted data."""
        if self.data:
            return self.data.extraction_confidence
        return 0.0


@dataclass
class ProcessingResult:
    """Overall processing result for an Excel file."""
    
    file_path: str
    status: ProcessingStatus
    total_links: int = 0
    processed_links: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    
    # Timing information
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    processing_time: float = 0.0
    
    # Results storage
    scraping_results: List[ScrapingResult] = field(default_factory=list)
    output_file_path: Optional[str] = None
    
    # Error tracking
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_scraping_result(self, result: ScrapingResult):
        """Add a scraping result and update counters."""
        self.scraping_results.append(result)
        self.processed_links += 1
        
        if result.is_successful():
            self.successful_extractions += 1
        else:
            self.failed_extractions += 1
    
    def get_success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.processed_links == 0:
            return 0.0
        return (self.successful_extractions / self.processed_links) * 100
    
    def get_progress_percentage(self) -> float:
        """Get processing progress as a percentage."""
        if self.total_links == 0:
            return 0.0
        return (self.processed_links / self.total_links) * 100
    
    def is_completed(self) -> bool:
        """Check if processing is completed."""
        return self.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED, ProcessingStatus.CANCELLED]
    
    def mark_completed(self):
        """Mark processing as completed and calculate timing."""
        self.completed_at = datetime.now()
        self.status = ProcessingStatus.COMPLETED
        if self.completed_at:
            self.processing_time = (self.completed_at - self.started_at).total_seconds()
    
    def mark_failed(self, error_message: str):
        """Mark processing as failed."""
        self.completed_at = datetime.now()
        self.status = ProcessingStatus.FAILED
        self.errors.append(error_message)
        if self.completed_at:
            self.processing_time = (self.completed_at - self.started_at).total_seconds()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of processing results."""
        return {
            "file_path": self.file_path,
            "status": self.status.value,
            "total_links": self.total_links,
            "processed_links": self.processed_links,
            "successful_extractions": self.successful_extractions,
            "failed_extractions": self.failed_extractions,
            "success_rate": f"{self.get_success_rate():.1f}%",
            "processing_time": f"{self.processing_time:.2f}s",
            "output_file": self.output_file_path,
            "errors": len(self.errors),
            "warnings": len(self.warnings)
        }