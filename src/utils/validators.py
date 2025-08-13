"""Input validation utilities."""

import re
import os
from urllib.parse import urlparse
from typing import Optional, List, Tuple
from pathlib import Path


def is_likely_url(text: str) -> bool:
    """
    Check if text is likely a URL vs product name/description.
    
    Args:
        text: String to check
        
    Returns:
        True if likely a URL, False if likely product name/description
    """
    if not text or not isinstance(text, str):
        return False
    
    text = text.strip().lower()
    
    # Already has protocol - likely URL
    if text.startswith(('http://', 'https://', 'ftp://')):
        return True
    
    # Starts with www - likely URL
    if text.startswith('www.') and '.' in text[4:]:
        return True
    
    # Product codes that should be converted to URLs (like 1SZE430800B0100)
    # These are alphanumeric codes that represent products
    if len(text) > 5 and text.replace(' ', '').replace('-', '').replace('_', '').isalnum():
        # If it's mostly alphanumeric and reasonable length, treat as product code
        if 6 <= len(text) <= 50:
            return True
    
    # Contains obvious non-URL patterns - likely product description
    if any(pattern in text for pattern in [
        'mm', 'cm', 'inch', 'pieces', 'galvaniz', 'sheet', 'crosspieces',
        'corners', 'plinth', 'w=', 'd=', 'h=', 'w/', 'd/', 'h/'
    ]):
        return False
    
    # Has domain-like structure with valid TLD
    if '.' in text and not text.startswith('.') and not text.endswith('.'):
        parts = text.split('.')
        if len(parts) >= 2:
            tld = parts[-1]
            # Common TLDs
            if tld in ['com', 'org', 'net', 'edu', 'gov', 'ro', 'co', 'io', 'ai']:
                return True
    
    return False


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate and clean a URL.
    
    Args:
        url: URL string to validate
        
    Returns:
        Tuple of (is_valid, cleaned_url) or (False, error_message)
    """
    if not url or not isinstance(url, str):
        return False, "URL is empty or not a string"
    
    url = url.strip()
    
    if not url:
        return False, "URL is empty after stripping whitespace"
    
    # Check if this looks like a URL vs product description
    if not is_likely_url(url):
        return False, "Text appears to be a product description, not a URL"
    
    # Handle Excel HYPERLINK formulas and product codes
    original_url = url
    
    # Check if it's an Excel HYPERLINK formula
    if url.startswith('=HYPERLINK'):
        # Extract URL from Excel HYPERLINK formula
        # Example: =HYPERLINK(_xlfn.CONCAT("https://new.abb.com/products/",C2),C2)
        import re
        match = re.search(r'"(https?://[^"]+)"', url)
        if match:
            base_url = match.group(1)
            # The actual product code would be in the referenced cell
            # For now, we'll construct the URL pattern
            url = base_url  # This might need adjustment based on actual data
        else:
            return False, f"Could not parse HYPERLINK formula: {original_url}"
    
    elif not url.startswith(('http://', 'https://', 'www.')):
        # If it's a product code, convert to ABB URL
        if url.replace(' ', '').replace('-', '').replace('_', '').isalnum():
            # Convert to ABB product URL format
            url = f"https://new.abb.com/products/{url}"
    
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        if url.startswith('www.'):
            url = f'https://{url}'
        elif '.' in url and not url.startswith('//'):
            url = f'https://{url}'
        else:
            return False, f"Cannot convert '{original_url}' to a valid URL"
    
    try:
        parsed = urlparse(url)
        
        # Check if we have a valid scheme
        if parsed.scheme not in ['http', 'https']:
            return False, f"Invalid URL scheme: {parsed.scheme}"
        
        # Check if we have a netloc (domain)
        if not parsed.netloc:
            return False, "URL missing domain name"
        
        # Basic domain validation
        domain_parts = parsed.netloc.split('.')
        if len(domain_parts) < 2:
            return False, "URL domain appears to be invalid"
        
        # Check for valid TLD (top level domain)
        tld = domain_parts[-1].lower()
        if len(tld) < 2 or not tld.isalpha():
            return False, "URL has invalid top-level domain"
        
        return True, url
        
    except Exception as e:
        return False, f"URL parsing error: {str(e)}"


def validate_file_path(file_path: str, must_exist: bool = True, 
                      allowed_extensions: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate a file path.
    
    Args:
        file_path: File path to validate
        must_exist: Whether the file must exist
        allowed_extensions: List of allowed file extensions (e.g., ['.xlsx', '.xls'])
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file_path or not isinstance(file_path, str):
        return False, "File path is empty or not a string"
    
    file_path = file_path.strip()
    
    if not file_path:
        return False, "File path is empty after stripping whitespace"
    
    try:
        path_obj = Path(file_path)
        
        # Check if file exists (if required)
        if must_exist and not path_obj.exists():
            return False, f"File does not exist: {file_path}"
        
        # Check if it's a file (not a directory)
        if must_exist and path_obj.exists() and not path_obj.is_file():
            return False, f"Path is not a file: {file_path}"
        
        # Check file extension
        if allowed_extensions:
            file_ext = path_obj.suffix.lower()
            if file_ext not in [ext.lower() for ext in allowed_extensions]:
                return False, f"File extension {file_ext} not allowed. Allowed: {', '.join(allowed_extensions)}"
        
        # Check if parent directory exists (for new files)
        if not must_exist:
            parent_dir = path_obj.parent
            if not parent_dir.exists():
                return False, f"Parent directory does not exist: {parent_dir}"
        
        # Check file size (if exists)
        if path_obj.exists():
            file_size = path_obj.stat().st_size
            max_size = 100 * 1024 * 1024  # 100MB default limit
            
            if file_size > max_size:
                return False, f"File is too large: {file_size / (1024*1024):.1f}MB (max: {max_size / (1024*1024):.1f}MB)"
        
        return True, None
        
    except Exception as e:
        return False, f"File path validation error: {str(e)}"


def validate_excel_file(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that a file is a valid Excel file.
    
    Args:
        file_path: Path to Excel file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # First, basic file validation
    is_valid, error_msg = validate_file_path(
        file_path, 
        must_exist=True, 
        allowed_extensions=['.xlsx', '.xls', '.xlsm']
    )
    
    if not is_valid:
        return False, error_msg
    
    # Try to verify it's actually an Excel file by attempting to read it
    try:
        import pandas as pd
        
        # Try to read the file (just get sheet names, don't load data)
        with pd.ExcelFile(file_path) as excel_file:
            sheet_names = excel_file.sheet_names
            
            if not sheet_names:
                return False, "Excel file contains no sheets"
            
            # Check if we can read at least one sheet
            df = pd.read_excel(excel_file, sheet_name=sheet_names[0], nrows=1)
            
        return True, None
        
    except ImportError:
        return False, "pandas is not available for Excel validation"
    except Exception as e:
        return False, f"Excel file validation failed: {str(e)}"


def validate_output_directory(directory_path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that a directory exists and is writable.
    
    Args:
        directory_path: Path to directory
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not directory_path or not isinstance(directory_path, str):
        return False, "Directory path is empty or not a string"
    
    directory_path = directory_path.strip()
    
    if not directory_path:
        return False, "Directory path is empty after stripping whitespace"
    
    try:
        path_obj = Path(directory_path)
        
        # Create directory if it doesn't exist
        if not path_obj.exists():
            try:
                path_obj.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return False, f"Cannot create directory: {str(e)}"
        
        # Check if it's actually a directory
        if not path_obj.is_dir():
            return False, f"Path is not a directory: {directory_path}"
        
        # Test write permissions by trying to create a temporary file
        test_file = path_obj / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()  # Delete the test file
        except Exception as e:
            return False, f"Directory is not writable: {str(e)}"
        
        return True, None
        
    except Exception as e:
        return False, f"Directory validation error: {str(e)}"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem use
    """
    if not filename:
        return "untitled"
    
    # Remove or replace invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    filename = re.sub(invalid_chars, '_', filename)
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Ensure it's not empty
    if not filename:
        filename = "untitled"
    
    # Limit length to avoid filesystem issues
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200 - len(ext)] + ext
    
    return filename


def is_safe_path(path: str, base_directory: str) -> bool:
    """
    Check if a path is safe (doesn't escape base directory).
    
    Args:
        path: Path to check
        base_directory: Base directory that should contain the path
        
    Returns:
        True if path is safe, False otherwise
    """
    try:
        base_path = Path(base_directory).resolve()
        target_path = Path(base_directory, path).resolve()
        
        # Check if target path is within base directory
        return base_path in target_path.parents or base_path == target_path
        
    except Exception:
        return False