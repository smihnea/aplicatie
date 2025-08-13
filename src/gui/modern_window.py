"""Modern, feature-rich Excel processor GUI with advanced progress tracking."""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import threading
import asyncio
import json
from typing import List, Optional
from pathlib import Path
from datetime import datetime

from models.config_models import AppConfig
from models.processing_result import ProcessingStatus
from utils.logger import get_logger, AdvancedProgressTracker
from utils.validators import validate_excel_file
from processing.integration_processor import IntegrationProcessor


class ModernExcelProcessorApp:
    """Modern, clean Excel processor application."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = get_logger(__name__)
        self.integration_processor = IntegrationProcessor(config)
        
        # App state
        self.selected_files: List[str] = []
        self.processing_active = False
        self.processing_paused = False
        self.current_progress_tracker: Optional[AdvancedProgressTracker] = None
        
        # Processing state persistence
        self.processing_state_file = "cache/processing_state.json"
        self.resume_data: Optional[dict] = None
        
        # Setup modern UI
        self._setup_appearance()
        self._create_window()
        self._create_interface()
        
        self.logger.info("Modern Excel Processor initialized")
    
    def _setup_appearance(self):
        """Setup modern appearance."""
        ctk.set_appearance_mode("dark")  # Force dark theme
        ctk.set_default_color_theme("blue")
    
    def _create_window(self):
        """Create main window."""
        self.root = ctk.CTk()
        self.root.title("Excel Processor & Web Scraper")
        self.root.geometry("1000x750")  # Slightly larger default
        self.root.minsize(900, 650)   # Increased minimum size for better layout
        
        # Configure grid
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Bind resize event for responsive behavior
        self.root.bind('<Configure>', self._on_window_resize)
    
    def _create_interface(self):
        """Create modern, clean interface."""
        
        # Main container with padding
        self.main_container = ctk.CTkFrame(self.root, corner_radius=0)
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)
        
        # Header section
        self._create_header()
        
        # Content area
        self.content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=30, pady=20)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=0)  # Upload area
        self.content_frame.grid_rowconfigure(1, weight=1)  # Results area
        
        # Create sections
        self._create_upload_section()
        self._create_results_section()
        
        # Footer with action buttons
        self._create_footer()
    
    def _create_header(self):
        """Create enhanced header with progress information."""
        header_frame = ctk.CTkFrame(self.main_container, height=120, corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        
        # Configure responsive grid weights
        header_frame.grid_columnconfigure(0, weight=0, minsize=250)  # Title - minimum width
        header_frame.grid_columnconfigure(1, weight=2)  # Progress - flexible
        header_frame.grid_columnconfigure(2, weight=0, minsize=100)  # Status - minimum width
        header_frame.grid_rowconfigure(0, weight=1)
        header_frame.grid_propagate(False)
        
        # App title - responsive sizing
        self.title_label = ctk.CTkLabel(
            header_frame,
            text="Excel Processor & Web Scraper",
            font=ctk.CTkFont(size=22, weight="bold")  # Slightly smaller for better fit
        )
        self.title_label.grid(row=0, column=0, sticky="w", padx=20, pady=25)  # Less padding
        
        # Progress container (hidden initially) - responsive design
        self.progress_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        self.progress_container.grid(row=0, column=1, sticky="nsew", padx=20)
        self.progress_container.grid_columnconfigure(0, weight=1)  # Make progress bar expand
        
        # Progress bar - responsive width
        self.progress_bar = ctk.CTkProgressBar(self.progress_container, height=8)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(15, 5))
        self.progress_bar.set(0)
        
        # Progress text with ETA
        self.progress_text = ctk.CTkLabel(
            self.progress_container,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=("gray70", "gray30")
        )
        self.progress_text.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        
        # Statistics display
        self.stats_text = ctk.CTkLabel(
            self.progress_container,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=("gray60", "gray40")
        )
        self.stats_text.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        
        # Initially hide progress container
        self.progress_container.grid_remove()
        
        # Status indicator removed to clean up interface
    
    def _create_upload_section(self):
        """Create modern file upload area."""
        # Upload container - responsive height
        upload_container = ctk.CTkFrame(self.content_frame, height=220)
        upload_container.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        upload_container.grid_columnconfigure(0, weight=1)
        upload_container.grid_rowconfigure(1, weight=0)  # Drop area
        upload_container.grid_rowconfigure(2, weight=1)  # Files display - expandable
        upload_container.grid_propagate(False)
        
        # Upload area title
        upload_title = ctk.CTkLabel(
            upload_container,
            text="Select Excel Files",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        upload_title.grid(row=0, column=0, sticky="w", padx=25, pady=(20, 10))
        
        # Drag & drop area
        self.drop_area = ctk.CTkFrame(upload_container, height=100, corner_radius=12)
        self.drop_area.grid(row=1, column=0, sticky="ew", padx=25, pady=(0, 10))
        self.drop_area.grid_columnconfigure(0, weight=1)
        self.drop_area.grid_rowconfigure(0, weight=1)
        
        # Drop area content
        drop_content = ctk.CTkFrame(self.drop_area, fg_color="transparent")
        drop_content.grid(row=0, column=0)
        
        # Upload icon/text
        upload_icon = ctk.CTkLabel(
            drop_content,
            text="📁",
            font=ctk.CTkFont(size=32)
        )
        upload_icon.grid(row=0, column=0, pady=(10, 5))
        
        upload_text = ctk.CTkLabel(
            drop_content,
            text="Drag & drop Excel files here",
            font=ctk.CTkFont(size=16),
            text_color=("gray60", "gray40")
        )
        upload_text.grid(row=1, column=0, pady=(0, 5))
        
        # Browse button
        self.browse_button = ctk.CTkButton(
            drop_content,
            text="Browse Files",
            command=self._browse_files,
            width=140,
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.browse_button.grid(row=2, column=0, pady=(5, 10))
        
        # Selected files display with visual indicators
        self.files_display = ctk.CTkFrame(upload_container)
        self.files_display.grid(row=2, column=0, sticky="ew", padx=25, pady=(0, 20))
        self.files_display.grid_columnconfigure(0, weight=1)
        
        # Scrollable frame for multiple files
        self.files_scroll = ctk.CTkScrollableFrame(
            self.files_display,
            height=80,
            corner_radius=8
        )
        self.files_scroll.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        # Initial empty state
        self.no_files_label = ctk.CTkLabel(
            self.files_scroll,
            text="No files selected",
            font=ctk.CTkFont(size=14),
            text_color=("gray60", "gray40")
        )
        self.no_files_label.pack(pady=20)
    
    def _create_results_section(self):
        """Create results display area."""
        # Results container
        results_container = ctk.CTkFrame(self.content_frame)
        results_container.grid(row=1, column=0, sticky="nsew", pady=(0, 20))
        results_container.grid_columnconfigure(0, weight=1)
        results_container.grid_rowconfigure(1, weight=1)
        
        # Results title
        results_title = ctk.CTkLabel(
            results_container,
            text="Processing Results",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        results_title.grid(row=0, column=0, sticky="w", padx=25, pady=(20, 10))
        
        # Results table/scrollable area
        self.results_scroll = ctk.CTkScrollableFrame(
            results_container,
            corner_radius=8
        )
        self.results_scroll.grid(row=1, column=0, sticky="nsew", padx=25, pady=(0, 20))
        
        # Placeholder for no results
        self.no_results_label = ctk.CTkLabel(
            self.results_scroll,
            text="No results yet. Select Excel files and click Process to begin.",
            font=ctk.CTkFont(size=14),
            text_color=("gray60", "gray40")
        )
        self.no_results_label.pack(pady=50)
    
    def _create_footer(self):
        """Create action buttons footer."""
        footer_frame = ctk.CTkFrame(self.main_container, height=80, corner_radius=0)
        footer_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        footer_frame.grid_columnconfigure(1, weight=1)
        footer_frame.grid_propagate(False)
        
        # Action buttons
        button_container = ctk.CTkFrame(footer_frame, fg_color="transparent")
        button_container.grid(row=0, column=0, columnspan=2, pady=20)
        
        # Process button (main action)
        self.process_button = ctk.CTkButton(
            button_container,
            text="Process Files",
            command=self._process_files,
            width=160,
            height=44,
            corner_radius=8,
            font=ctk.CTkFont(size=16, weight="bold"),
            state="disabled"
        )
        self.process_button.pack(side="right", padx=(10, 0))
        
        # Pause/Resume button (hidden initially)
        self.pause_button = ctk.CTkButton(
            button_container,
            text="⏸️ Pause",
            command=self._toggle_pause,
            width=120,
            height=44,
            corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#ff6b35",
            hover_color="#e55a2b"
        )
        # Initially hidden
        
        # Export Current Results button (hidden initially)
        self.export_button = ctk.CTkButton(
            button_container,
            text="💾 Export Current",
            command=self._export_current_results,
            width=150,
            height=44,
            corner_radius=8,
            font=ctk.CTkFont(size=14),
            fg_color="#28a745",
            hover_color="#218838"
        )
        # Initially hidden
        
        # Resume Processing button (hidden initially) 
        self.resume_button = ctk.CTkButton(
            button_container,
            text="▶️ Resume Processing",
            command=self._resume_processing,
            width=180,
            height=44,
            corner_radius=8,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#007bff",
            hover_color="#0056b3"
        )
        # Initially hidden
        
        # Clear button
        self.clear_button = ctk.CTkButton(
            button_container,
            text="Clear",
            command=self._clear_files,
            width=100,
            height=44,
            corner_radius=8,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            border_width=2,
            state="disabled"
        )
        self.clear_button.pack(side="right")
    
    def _browse_files(self):
        """Open file browser."""
        try:
            filetypes = [
                ("Excel files", "*.xlsx *.xls *.xlsm"),
                ("All files", "*.*")
            ]
            
            file_paths = filedialog.askopenfilenames(
                title="Select Excel Files",
                filetypes=filetypes,
                multiple=True
            )
            
            self.logger.info(f"🔍 DEBUG: File dialog returned {len(file_paths)} files: {list(file_paths)}")
            
            if file_paths:
                self._add_files(list(file_paths))
            else:
                self.logger.info("🔍 DEBUG: No files selected in dialog")
                
        except Exception as e:
            self.logger.error(f"File browser error: {e}")
            messagebox.showerror("Error", f"Failed to open file browser: {e}")
    
    def _add_files(self, file_paths: List[str]):
        """Add files to selection."""
        self.logger.info(f"🔍 DEBUG: _add_files called with {len(file_paths)} paths")
        valid_files = []
        invalid_files = []
        
        for file_path in file_paths:
            self.logger.info(f"🔍 DEBUG: Validating file: {file_path}")
            if file_path not in self.selected_files:
                is_valid, error_msg = validate_excel_file(file_path)
                self.logger.info(f"🔍 DEBUG: File validation result - Valid: {is_valid}, Error: {error_msg}")
                if is_valid:
                    valid_files.append(file_path)
                    self.selected_files.append(file_path)
                    self.logger.info(f"✅ DEBUG: Added valid file: {Path(file_path).name}")
                else:
                    invalid_files.append((file_path, error_msg))
                    self.logger.warning(f"❌ DEBUG: Rejected file: {Path(file_path).name} - {error_msg}")
            else:
                self.logger.info(f"🔍 DEBUG: File already selected: {Path(file_path).name}")
        
        self.logger.info(f"🔍 DEBUG: Final counts - Valid: {len(valid_files)}, Invalid: {len(invalid_files)}, Total selected: {len(self.selected_files)}")
        
        # Show errors for invalid files
        if invalid_files:
            error_text = "\n".join([f"• {Path(f[0]).name}: {f[1]}" for f in invalid_files])
            messagebox.showerror("Invalid Files", f"Some files could not be added:\n\n{error_text}")
        
        # Update UI
        if valid_files:
            self.logger.info(f"🔄 DEBUG: Updating files display and buttons")
            self._update_files_display()
            self._update_buttons()
        else:
            self.logger.warning(f"⚠️ DEBUG: No valid files to update display")
    
    def _update_files_display(self):
        """Update files display with visual indicators."""
        self.logger.info(f"🔄 DEBUG: _update_files_display called with {len(self.selected_files)} files")
        
        # Clear existing file widgets
        for widget in self.files_scroll.winfo_children():
            widget.destroy()
        
        if not self.selected_files:
            self.logger.info(f"🔄 DEBUG: No files selected, showing empty state")
            # Show empty state
            self.no_files_label = ctk.CTkLabel(
                self.files_scroll,
                text="No files selected",
                font=ctk.CTkFont(size=14),
                text_color=("gray60", "gray40")
            )
            self.no_files_label.pack(pady=20)
            return
        
        self.logger.info(f"🔄 DEBUG: Creating file widgets for {len(self.selected_files)} files")
        
        # Show selected files with icons
        for i, file_path in enumerate(self.selected_files):
            file_frame = ctk.CTkFrame(self.files_scroll, corner_radius=6)
            file_frame.pack(fill="x", padx=5, pady=2)
            
            # File icon and name
            file_info = ctk.CTkLabel(
                file_frame,
                text=f"📊 {Path(file_path).name}",
                font=ctk.CTkFont(size=13),
                anchor="w"
            )
            file_info.grid(row=0, column=0, sticky="w", padx=10, pady=8)
            
            # File size
            try:
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                size_text = f"{size_mb:.1f} MB"
            except:
                size_text = "Unknown size"
            
            size_label = ctk.CTkLabel(
                file_frame,
                text=size_text,
                font=ctk.CTkFont(size=11),
                text_color=("gray60", "gray40")
            )
            size_label.grid(row=0, column=1, sticky="e", padx=10, pady=8)
            
            # Remove button
            remove_btn = ctk.CTkButton(
                file_frame,
                text="✕",
                command=lambda idx=i: self._remove_file(idx),
                width=30,
                height=24,
                corner_radius=4,
                font=ctk.CTkFont(size=12),
                fg_color="transparent",
                hover_color=("gray80", "gray20")
            )
            remove_btn.grid(row=0, column=2, padx=(5, 10), pady=8)
            
            file_frame.grid_columnconfigure(0, weight=1)
    
    def _remove_file(self, index: int):
        """Remove a file from selection."""
        if 0 <= index < len(self.selected_files):
            removed_file = self.selected_files.pop(index)
            self.logger.info(f"Removed file: {Path(removed_file).name}")
            self._update_files_display()
            self._update_buttons()
    
    def _update_buttons(self):
        """Update button states."""
        has_files = len(self.selected_files) > 0
        
        self.process_button.configure(
            state="normal" if has_files and not self.processing_active else "disabled"
        )
        self.clear_button.configure(
            state="normal" if has_files else "disabled"
        )
        
        # Check for resume data
        if self._has_resume_data() and not self.processing_active:
            self.resume_button.pack(side="right", padx=(10, 0))
        else:
            self.resume_button.pack_forget()
    
    def _clear_files(self):
        """Clear selected files."""
        self.selected_files.clear()
        self._update_files_display()
        self._update_buttons()
        self._clear_results()
        self._update_status("Ready")
    
    def _clear_results(self):
        """Clear results display."""
        # Clear all result widgets
        for widget in self.results_scroll.winfo_children():
            widget.destroy()
        
        # Show placeholder
        self.no_results_label = ctk.CTkLabel(
            self.results_scroll,
            text="No results yet. Select Excel files and click Process to begin.",
            font=ctk.CTkFont(size=14),
            text_color=("gray60", "gray40")
        )
        self.no_results_label.pack(pady=50)
    
    def _process_files(self):
        """Start file processing with enhanced progress tracking."""
        if not self.selected_files or self.processing_active:
            return
        
        self.processing_active = True
        self.processing_paused = False
        self._update_buttons()
        self._clear_results()
        self._show_processing_controls()
        
        # Start processing thread
        thread = threading.Thread(target=self._process_thread)
        thread.daemon = True
        thread.start()
    
    def _process_thread(self):
        """Enhanced processing thread with advanced progress tracking."""
        try:
            # Update UI
            self.root.after(0, lambda: self._update_status("Initializing processing..."))
            
            # Run async processing
            asyncio.run(self._process_files_async_enhanced())
            
        except Exception as e:
            error_msg = f"Processing failed: {str(e)}"
            self.logger.error(error_msg)
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
        
        finally:
            self.processing_active = False
            self.processing_paused = False
            self.root.after(0, lambda: [
                self._hide_processing_controls(),
                self._hide_progress_display(),
                self._update_buttons(),
                self._update_status("Ready")
            ])
    
    async def _process_files_async_enhanced(self):
        """Enhanced async file processing with advanced progress tracking and pause/resume."""
        total_files = len(self.selected_files)
        self.current_results = []
        
        # Initialize advanced progress tracker
        phase_names = ["File Analysis", "Link Extraction", "Web Scraping", "Data Processing", "Output Generation"]
        self.current_progress_tracker = AdvancedProgressTracker(
            "Excel Processing", 
            total_files, 
            phase_names
        )
        
        # Add GUI progress callback
        self.current_progress_tracker.add_progress_callback(self._gui_progress_callback)
        
        # Simple working callback - restore original functionality  
        async def enhanced_progress_callback(message: str, progress: float, current_file: int, total_files: int):
            # Check for pause
            while self.processing_paused and self.processing_active:
                await asyncio.sleep(0.1)
            
            # Check if still processing (not cancelled)
            if not self.processing_active:
                return
                
            # Use the original working approach with file progress
            file_progress = (progress * 100)
            
            # Update progress display with original logic
            self.root.after(0, lambda: self._update_progress_display(
                current_file, total_files, file_progress, "", message, {}
            ))
        
        try:
            # Process files with enhanced callback
            results = await self.integration_processor.process_multiple_files(
                self.selected_files,
                progress_callback=enhanced_progress_callback
            )
            
            self.current_results = results
            
            # Complete progress tracking
            if self.current_progress_tracker:
                self.current_progress_tracker.complete("All files processed successfully!")
            
            # Update results display
            self.root.after(0, lambda: self._display_results(results))
            
        except Exception as e:
            if self.current_progress_tracker:
                self.current_progress_tracker.complete(f"Processing failed: {e}")
            raise
    
    def _gui_progress_callback(self, processed: int, total: int, percent: float, eta: str, current_item: str):
        """Callback to update GUI progress from AdvancedProgressTracker."""
        # Get statistics from current progress tracker
        stats = {}
        if self.current_progress_tracker:
            tracker_stats = self.current_progress_tracker.get_statistics()
            stats = {
                'success_rate': tracker_stats['success_rate'],
                'current_speed': tracker_stats['current_speed'],
                'cache_hits': 0,  # We'll get this from scraping engine if available
                'cache_misses': 0
            }
        
        # Update GUI on main thread
        self.root.after(0, lambda: self._update_progress_display(
            processed, total, percent, eta, current_item or "Processing...", stats
        ))
    
    def _display_results(self, results):
        """Display processing results."""
        # Clear placeholder
        for widget in self.results_scroll.winfo_children():
            widget.destroy()
        
        if not results:
            self._clear_results()
            return
        
        # Create result entries
        for i, result in enumerate(results):
            self._create_result_entry(i, result)
    
    def _create_result_entry(self, index: int, result):
        """Create a result entry widget."""
        # Result container
        result_frame = ctk.CTkFrame(self.results_scroll, corner_radius=8)
        result_frame.pack(fill="x", padx=10, pady=5)
        
        # File name
        filename = Path(result.file_path).name
        name_label = ctk.CTkLabel(
            result_frame,
            text=filename,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        name_label.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
        
        # Status and stats
        if result.status == ProcessingStatus.COMPLETED:
            status_text = f"✅ Completed • {result.successful_extractions}/{result.total_links} successful"
            status_color = ("green", "lightgreen")
        else:
            status_text = f"❌ Failed • {result.errors[0] if result.errors else 'Unknown error'}"
            status_color = ("red", "lightcoral")
        
        status_label = ctk.CTkLabel(
            result_frame,
            text=status_text,
            font=ctk.CTkFont(size=12),
            text_color=status_color,
            anchor="w"
        )
        status_label.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 15))
        
        # Open button for successful results
        if result.output_file_path and Path(result.output_file_path).exists():
            open_button = ctk.CTkButton(
                result_frame,
                text="Open Result",
                command=lambda: self._open_file(result.output_file_path),
                width=100,
                height=32,
                corner_radius=6
            )
            open_button.grid(row=0, column=1, rowspan=2, padx=15, pady=10)
        
        result_frame.grid_columnconfigure(0, weight=1)
    
    def _open_file(self, file_path: str):
        """Open file with system default application."""
        try:
            import subprocess
            import platform
            
            system = platform.system()
            if system == "Darwin":  # macOS
                subprocess.run(["open", file_path])
            elif system == "Windows":
                os.startfile(file_path)
            else:  # Linux
                subprocess.run(["xdg-open", file_path])
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {e}")
    
    def _has_resume_data(self) -> bool:
        """Check if resume data exists."""
        return Path(self.processing_state_file).exists()
    
    def _save_processing_state(self, current_file_index: int, completed_files: list):
        """Save current processing state for resume functionality."""
        try:
            state = {
                "timestamp": datetime.now().isoformat(),
                "selected_files": self.selected_files,
                "current_file_index": current_file_index,
                "completed_files": completed_files,
                "processing_paused": True
            }
            
            os.makedirs(os.path.dirname(self.processing_state_file), exist_ok=True)
            with open(self.processing_state_file, 'w') as f:
                json.dump(state, f, indent=2)
                
            self.logger.info("Processing state saved for resume")
        except Exception as e:
            self.logger.error(f"Failed to save processing state: {e}")
    
    def _load_processing_state(self) -> Optional[dict]:
        """Load saved processing state."""
        try:
            if Path(self.processing_state_file).exists():
                with open(self.processing_state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load processing state: {e}")
        return None
    
    def _clear_processing_state(self):
        """Clear saved processing state."""
        try:
            if Path(self.processing_state_file).exists():
                os.unlink(self.processing_state_file)
        except Exception as e:
            self.logger.error(f"Failed to clear processing state: {e}")
    
    def _toggle_pause(self):
        """Toggle pause/resume processing."""
        if self.processing_active:
            self.processing_paused = not self.processing_paused
            
            if self.processing_paused:
                self.pause_button.configure(text="▶️ Resume", fg_color="#28a745", hover_color="#218838")
                self.export_button.pack(side="right", padx=(10, 0))
                self._update_status("Processing paused")
            else:
                self.pause_button.configure(text="⏸️ Pause", fg_color="#ff6b35", hover_color="#e55a2b")
                self.export_button.pack_forget()
                self._update_status("Processing resumed")
    
    def _export_current_results(self):
        """Export current processing results."""
        try:
            if hasattr(self, 'current_results') and self.current_results:
                # Find the most recent output file
                for result in reversed(self.current_results):
                    if result.output_file_path and Path(result.output_file_path).exists():
                        # Copy to a new file with timestamp
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        original_path = Path(result.output_file_path)
                        export_path = original_path.parent / f"{original_path.stem}_partial_{timestamp}{original_path.suffix}"
                        
                        import shutil
                        shutil.copy2(result.output_file_path, export_path)
                        
                        messagebox.showinfo("Export Success", f"Current results exported to:\n{export_path.name}")
                        self.logger.info(f"Exported partial results to: {export_path}")
                        return
                
            messagebox.showwarning("No Results", "No results available to export yet.")
            
        except Exception as e:
            error_msg = f"Failed to export results: {e}"
            self.logger.error(error_msg)
            messagebox.showerror("Export Error", error_msg)
    
    def _resume_processing(self):
        """Resume processing from saved state."""
        try:
            state = self._load_processing_state()
            if state:
                self.selected_files = state["selected_files"]
                self.resume_data = state
                self._update_files_display()
                self._process_files()
                self._clear_processing_state()
        except Exception as e:
            error_msg = f"Failed to resume processing: {e}"
            self.logger.error(error_msg)
            messagebox.showerror("Resume Error", error_msg)
    
    def _update_progress_display(self, processed: int, total: int, percent: float, eta: str, current_item: str, stats: dict = None):
        """Update the progress display with detailed information."""
        # Show progress container if hidden
        self.progress_container.grid()
        
        # Update progress bar
        self.progress_bar.set(percent / 100)
        
        # Update main progress text - show scraping progress if available in current_item
        if "scraping" in current_item.lower():
            self.progress_text.configure(text=current_item)
        else:
            self.progress_text.configure(
                text=f"Processing {processed:,}/{total:,} files ({percent:.1f}%)"
            )
        
        # Update detailed statistics if available
        if stats:
            success_rate = stats.get('success_rate', 0)
            current_speed = stats.get('current_speed', 0)
            cache_hits = stats.get('cache_hits', 0)
            cache_misses = stats.get('cache_misses', 0)
            
            # Only show cache stats if we have actual data
            if cache_hits > 0 or cache_misses > 0:
                cache_rate = (cache_hits / (cache_hits + cache_misses) * 100)
                stats_text = f"✅ {success_rate:.1f}% success • ⚡ {current_speed:.1f} items/sec • 💾 {cache_rate:.1f}% cache hits"
            else:
                stats_text = f"✅ {success_rate:.1f}% success • ⚡ {current_speed:.1f} items/sec • Currently: {current_item[:40]}..."
            
            self.stats_text.configure(text=stats_text)
        else:
            # Fallback when no statistics available
            self.stats_text.configure(text=f"Currently processing: {current_item[:50]}...")
    
    def _hide_progress_display(self):
        """Hide the progress display."""
        self.progress_container.grid_remove()
    
    def _show_processing_controls(self):
        """Show pause/resume controls during processing."""
        self.pause_button.pack(side="right", padx=(10, 0))
        self.process_button.configure(state="disabled")
    
    def _hide_processing_controls(self):
        """Hide processing controls when not processing."""
        self.pause_button.pack_forget()
        self.export_button.pack_forget()
        self.process_button.configure(state="normal" if self.selected_files else "disabled")
    
    def _update_status(self, message: str):
        """Update status display - now disabled to clean up interface."""
        pass  # Status label removed
    
    def _on_window_resize(self, event):
        """Handle window resize events for responsive behavior."""
        # Only handle resize events for the main window
        if event.widget != self.root:
            return
            
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        
        # Adjust title font size based on window width
        if hasattr(self, 'title_label'):
            if width < 900:
                # Smaller font for narrow windows
                font_size = 18
                title_text = "Excel Processor"
            elif width < 1100:
                # Medium font for medium windows
                font_size = 20
                title_text = "Excel Processor & Scraper"
            else:
                # Full font for wide windows
                font_size = 22
                title_text = "Excel Processor & Web Scraper"
            
            # Update only if needed to prevent constant updates
            current_text = self.title_label.cget('text')
            if current_text != title_text:
                self.title_label.configure(
                    text=title_text,
                    font=ctk.CTkFont(size=font_size, weight="bold")
                )
    
    def run(self):
        """Start the application."""
        self.logger.info("Starting modern Excel processor")
        self.root.mainloop()