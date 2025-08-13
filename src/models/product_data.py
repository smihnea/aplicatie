"""Product data models and structures."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
import pandas as pd


@dataclass
class ProductData:
    """Represents extracted product information."""
    
    # Core product identifiers
    ean: Optional[str] = None
    ral_number: Optional[str] = None
    
    # Physical dimensions (in mm)
    net_width: Optional[float] = None
    net_height: Optional[float] = None
    net_depth: Optional[float] = None
    
    # Package information
    package_units: Optional[int] = None
    package_weight: Optional[float] = None  # in kg
    
    # Extraction metadata
    extraction_confidence: float = 0.0
    source_url: str = ""
    extracted_at: datetime = field(default_factory=datetime.now)
    extraction_method: str = "unknown"
    
    # Additional extracted data (flexible)
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def is_valid(self) -> bool:
        """Check if the extracted data contains meaningful information."""
        return any([
            self.ean,
            self.ral_number,
            self.net_width,
            self.net_height, 
            self.net_depth,
            self.package_units,
            self.package_weight
        ])
    
    def get_completeness_score(self) -> float:
        """Calculate how complete the extracted data is (0-1 scale)."""
        fields = [
            self.ean, self.ral_number, self.net_width, 
            self.net_height, self.net_depth, self.package_units, 
            self.package_weight
        ]
        filled_fields = sum(1 for field in fields if field is not None)
        return filled_fields / len(fields)


@dataclass
class ProductLink:
    """Represents a product link found in Excel data."""
    
    url: str
    row_index: int
    sheet_name: str
    column_name: str = "Fisa Technica"
    
    # Processing status
    processed: bool = False
    processing_error: Optional[str] = None
    extracted_data: Optional[ProductData] = None
    
    def __post_init__(self):
        """Validate and clean the URL."""
        if self.url:
            self.url = self.url.strip()
            if not (self.url.startswith('http://') or self.url.startswith('https://')):
                if self.url.startswith('www.'):
                    self.url = f'https://{self.url}'
                elif '.' in self.url:
                    self.url = f'https://{self.url}'


@dataclass
class ExcelMetadata:
    """Metadata about an Excel file."""
    
    filename: str
    file_path: str
    file_size: int  # in bytes
    created_at: datetime
    modified_at: datetime
    sheet_names: List[str] = field(default_factory=list)
    total_rows: int = 0
    total_columns: int = 0
    links_found: int = 0


@dataclass  
class ExcelData:
    """Represents Excel file data and structure."""
    
    metadata: ExcelMetadata
    sheets: Dict[str, pd.DataFrame] = field(default_factory=dict)
    links: List[ProductLink] = field(default_factory=list)
    original_file_path: str = ""
    
    def get_sheet_data(self, sheet_name: str) -> Optional[pd.DataFrame]:
        """Get data for a specific sheet."""
        return self.sheets.get(sheet_name)
    
    def get_all_links(self) -> List[ProductLink]:
        """Get all product links from all sheets."""
        return self.links
    
    def get_links_by_sheet(self, sheet_name: str) -> List[ProductLink]:
        """Get links from a specific sheet."""
        return [link for link in self.links if link.sheet_name == sheet_name]
    
    def add_extracted_data(self, row_index: int, sheet_name: str, data: ProductData):
        """Add extracted data to the corresponding link."""
        for link in self.links:
            if link.row_index == row_index and link.sheet_name == sheet_name:
                link.extracted_data = data
                link.processed = True
                break