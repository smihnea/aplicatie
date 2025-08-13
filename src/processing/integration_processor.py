"""Integration processor that combines Excel processing and web scraping."""

import asyncio
import os
from pathlib import Path
from typing import List, Optional, Callable
from datetime import datetime

from models.product_data import ExcelData, ProductLink
from models.processing_result import ProcessingResult, ProcessingStatus
from models.config_models import AppConfig
from processing.excel_processor import ExcelProcessor
from scraping.scraping_engine import ScrapingEngine
from utils.logger import get_logger


class IntegrationProcessor:
    """Main processor that integrates Excel processing and web scraping."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = get_logger(__name__)
        
        # Initialize components
        self.excel_processor = ExcelProcessor()
        
        # Initialize scraping engine
        azure_endpoint = ""
        azure_api_key = ""
        if self.config.azure.enabled:
            azure_endpoint = self.config.azure.endpoint
            azure_api_key = self.config.azure.api_key
        
        self.scraping_engine = ScrapingEngine(
            self.config.scraping,
            azure_endpoint,
            azure_api_key
        )
        
        self.logger.info("Integration processor initialized")
    
    async def process_excel_file(
        self,
        file_path: str,
        output_directory: Optional[str] = None,
        progress_callback: Optional[Callable[[str, float, int, int], None]] = None
    ) -> ProcessingResult:
        """
        Process a complete Excel file with web scraping.
        
        Args:
            file_path: Path to the Excel file
            output_directory: Directory to save output files (optional)
            progress_callback: Callback for progress updates (message, progress_percentage)
            
        Returns:
            ProcessingResult with complete processing information
        """
        result = ProcessingResult(
            file_path=file_path,
            status=ProcessingStatus.IN_PROGRESS,
            started_at=datetime.now()
        )
        
        try:
            self.logger.info(f"Starting to process Excel file: {file_path}")
            
            # Step 1: Read Excel file
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback(f"Reading Excel file: {os.path.basename(file_path)}", 0.1, 1, 1)
                else:
                    progress_callback(f"Reading Excel file: {os.path.basename(file_path)}", 0.1, 1, 1)
            
            excel_data = self.excel_processor.read_excel_file(file_path)
            self.logger.info(f"Read Excel file with {len(excel_data.sheets)} sheets")
            
            # Step 2: Extract links
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback("Extracting product links...", 0.2, 1, 1)
                else:
                    progress_callback("Extracting product links...", 0.2, 1, 1)
            
            links = self.excel_processor.extract_links(excel_data)
            result.total_links = len(links)
            
            self.logger.info(f"Extracted {len(links)} product links")
            
            if not links:
                result.warnings.append("No product links found in Excel file")
                self.logger.warning("No links found to process")
            else:
                # Step 3: Process web scraping
                if progress_callback:
                    if asyncio.iscoroutinefunction(progress_callback):
                        await progress_callback("Starting web scraping...", 0.3, 1, 1)
                    else:
                        progress_callback("Starting web scraping...", 0.3, 1, 1)
                
                scraping_results = await self.scraping_engine.process_links(
                    links,
                    progress_callback=self._create_scraping_progress_callback(progress_callback),
                    result_callback=lambda sr: result.add_scraping_result(sr)
                )
                
                self.logger.info(f"Completed web scraping: {len(scraping_results)} results")
            
            # Step 4: Generate output file
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback("Generating output file...", 0.9, 1, 1)
                else:
                    progress_callback("Generating output file...", 0.9, 1, 1)
            
            output_path = self._generate_output_path(file_path, output_directory)
            
            enhanced_file = self.excel_processor.write_enhanced_excel(
                excel_data,
                output_path,
                self.config.output.preserve_formatting
            )
            
            result.output_file_path = enhanced_file
            
            # Step 5: Complete processing
            result.mark_completed()
            
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback("Processing completed", 1.0, 1, 1)
                else:
                    progress_callback("Processing completed", 1.0, 1, 1)
            
            self.logger.info(f"Successfully processed Excel file: {file_path}")
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to process Excel file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            result.mark_failed(error_msg)
            
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback(f"Processing failed: {str(e)}", 0.0, 1, 1)
                else:
                    progress_callback(f"Processing failed: {str(e)}", 0.0, 1, 1)
            
            return result
    
    async def process_multiple_files(
        self,
        file_paths: List[str],
        output_directory: Optional[str] = None,
        progress_callback: Optional[Callable[[str, float, int, int], None]] = None
    ) -> List[ProcessingResult]:
        """
        Process multiple Excel files.
        
        Args:
            file_paths: List of Excel file paths
            output_directory: Directory to save output files
            progress_callback: Callback for progress (message, file_progress, current_file, total_files)
            
        Returns:
            List of ProcessingResult objects
        """
        self.logger.info(f"Starting to process {len(file_paths)} Excel files")
        
        results = []
        total_files = len(file_paths)
        
        for i, file_path in enumerate(file_paths):
            current_file = i + 1
            
            try:
                # Create progress callback for single file
                single_file_progress = None
                if progress_callback:
                    async def single_file_progress(message: str, progress: float, cf: int, tf: int):
                        if asyncio.iscoroutinefunction(progress_callback):
                            await progress_callback(message, progress, current_file, total_files)
                        else:
                            progress_callback(message, progress, current_file, total_files)
                
                # Process single file
                result = await self.process_excel_file(
                    file_path,
                    output_directory,
                    single_file_progress
                )
                
                results.append(result)
                
                self.logger.info(f"Completed file {current_file}/{total_files}: {os.path.basename(file_path)}")
                
            except Exception as e:
                self.logger.error(f"Failed to process file {file_path}: {str(e)}")
                
                # Create failed result
                failed_result = ProcessingResult(
                    file_path=file_path,
                    status=ProcessingStatus.FAILED
                )
                failed_result.mark_failed(str(e))
                results.append(failed_result)
        
        self.logger.info(f"Completed processing {len(file_paths)} files")
        return results
    
    def _create_scraping_progress_callback(self, main_progress_callback):
        """Create a progress callback for scraping that maps to main progress."""
        if not main_progress_callback:
            return None
        
        async def scraping_progress(processed: int, total: int, current_url: str):
            if total > 0:
                scraping_progress_pct = processed / total
                # Map scraping progress to 30%-80% of total progress
                overall_progress = 0.3 + (scraping_progress_pct * 0.5)
                
                if asyncio.iscoroutinefunction(main_progress_callback):
                    await main_progress_callback(
                        f"Scraping {processed}/{total}: {os.path.basename(current_url)}",
                        overall_progress,
                        1, 1  # current_file and total_files for single file processing
                    )
                else:
                    main_progress_callback(
                        f"Scraping {processed}/{total}: {os.path.basename(current_url)}",
                        overall_progress,
                        1, 1  # current_file and total_files for single file processing
                    )
        
        return scraping_progress
    
    def _generate_output_path(self, input_path: str, output_directory: Optional[str]) -> str:
        """Generate output file path."""
        input_file = Path(input_path)
        
        if output_directory:
            output_dir = Path(output_directory)
        else:
            output_dir = input_file.parent / "processed"
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename
        output_filename = f"{input_file.stem}{self.config.output.output_suffix}{input_file.suffix}"
        output_path = output_dir / output_filename
        
        return str(output_path)
    
    def get_supported_extensions(self) -> List[str]:
        """Get supported file extensions."""
        return self.config.ui.supported_extensions
    
    def validate_file(self, file_path: str) -> tuple[bool, Optional[str]]:
        """Validate if a file can be processed."""
        from utils.validators import validate_excel_file
        return validate_excel_file(file_path)
    
    async def test_scraping(self, url: str):
        """Test scraping a single URL for debugging."""
        return await self.scraping_engine.test_single_url(url)
    
    def get_statistics(self) -> dict:
        """Get processing statistics."""
        return {
            "scraping_engine": self.scraping_engine.get_statistics(),
            "config": {
                "azure_enabled": self.config.azure.enabled,
                "preserve_formatting": self.config.output.preserve_formatting,
                "supported_extensions": self.config.ui.supported_extensions
            }
        }