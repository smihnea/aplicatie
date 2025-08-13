"""Web scraping strategy implementations."""

import re
import asyncio
import aiohttp
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, urljoin
from datetime import datetime
import json

from bs4 import BeautifulSoup
from models.product_data import ProductData
from utils.logger import get_logger


class ScrapingStrategy(ABC):
    """Abstract base class for web scraping strategies."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"scraping.{name}")
    
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Check if this strategy can handle the given URL."""
        pass
    
    @abstractmethod
    async def extract_data(self, url: str, session: aiohttp.ClientSession) -> Optional[ProductData]:
        """Extract product data from the given URL."""
        pass
    
    @abstractmethod
    def get_confidence_score(self) -> float:
        """Get the confidence score for this strategy (0.0 to 1.0)."""
        pass
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text by removing extra whitespace and special characters."""
        if not text:
            return ""
        
        # Remove multiple whitespaces, newlines, tabs
        cleaned = re.sub(r'\s+', ' ', text)
        return cleaned.strip()
    
    def _extract_numeric(self, text: str) -> Optional[float]:
        """Extract numeric value from text."""
        if not text:
            return None
        
        # Look for numeric patterns
        matches = re.findall(r'\d+\.?\d*', text.replace(',', '.'))
        if matches:
            try:
                return float(matches[0])
            except ValueError:
                pass
        
        return None
    
    def _extract_ean(self, text: str) -> Optional[str]:
        """Extract EAN code from text."""
        if not text:
            return None
        
        # EAN codes are typically 8, 13, or 14 digits
        ean_patterns = [
            r'\b\d{14}\b',  # EAN-14
            r'\b\d{13}\b',  # EAN-13
            r'\b\d{8}\b'    # EAN-8
        ]
        
        for pattern in ean_patterns:
            matches = re.findall(pattern, text)
            if matches:
                return matches[0]
        
        return None
    
    def _extract_ral_number(self, text: str) -> Optional[str]:
        """Extract RAL color number from text with comprehensive pattern matching."""
        if not text:
            return None
        
        # Enhanced RAL patterns to catch various formats
        ral_patterns = [
            # "RAL 7035 - Light Grey" (your actual format)
            r'RAL\s*[-\s]?\s*(\d{4})\s*[-–—]\s*([A-Za-z\s]+)',
            # "RAL 7035 Light Grey" (without dash)
            r'RAL\s*[-\s]?\s*(\d{4})\s+([A-Za-z\s]+)',
            # "RAL Number: 7035"
            r'RAL\s*(?:Number|Code|Colour|Color)?\s*[:=]?\s*[-\s]?\s*(\d{4})',
            # "Color: RAL 7035"
            r'(?:Color|Colour)\s*[:=]\s*RAL\s*[-\s]?\s*(\d{4})',
            # Basic "RAL 7035" or "RAL-7035"
            r'RAL\s*[-\s]?\s*(\d{4})',
            # In table cells or structured data
            r'(\d{4})\s*[-–—]\s*RAL',  # "7035 - RAL"
            # HTML attributes or data-ral patterns
            r'(?:data-ral|ral-code|ral_number)\s*[:=]\s*["\']?(\d{4})["\']?'
        ]
        
        # Try each pattern in order of specificity
        for pattern in ral_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                if isinstance(matches[0], tuple):
                    # Return the first capturing group (the number)
                    ral_number = matches[0][0] if matches[0][0].isdigit() else matches[0][1]
                else:
                    ral_number = matches[0]
                
                if ral_number.isdigit() and len(ral_number) == 4:
                    return f"RAL {ral_number}"
        
        # Expanded color to RAL mapping for comprehensive coverage
        color_mappings = {
            # Standard greys
            'grey': 'RAL 7035',
            'gray': 'RAL 7035', 
            'light grey': 'RAL 7035',
            'light gray': 'RAL 7035',
            'silver': 'RAL 9006',
            'anthracite': 'RAL 7016',
            'dark grey': 'RAL 7012',
            'dark gray': 'RAL 7012',
            
            # Basic colors
            'white': 'RAL 9003',
            'pure white': 'RAL 9010',
            'black': 'RAL 9005',
            'red': 'RAL 3020',
            'signal red': 'RAL 3001',
            'blue': 'RAL 5015',
            'signal blue': 'RAL 5005',
            'green': 'RAL 6029',
            'yellow': 'RAL 1023',
            'orange': 'RAL 2004',
            
            # Industrial colors common in electrical equipment
            'beige': 'RAL 1001',
            'cream': 'RAL 9001',
            'ivory': 'RAL 1015',
            'brown': 'RAL 8017',
            'violet': 'RAL 4008',
            'pink': 'RAL 3015',
            
            # Metal finishes
            'stainless steel': 'RAL 9006',
            'aluminum': 'RAL 9006',
            'chrome': 'RAL 9006',
            'brass': 'RAL 1036',
            'copper': 'RAL 8004'
        }
        
        # Search for color names in text
        text_lower = text.lower()
        # Sort by length (longest first) to match "light grey" before "grey"
        sorted_colors = sorted(color_mappings.items(), key=lambda x: len(x[0]), reverse=True)
        
        for color, ral in sorted_colors:
            if color in text_lower:
                # Make sure it's a word boundary match to avoid partial matches
                if re.search(r'\b' + re.escape(color) + r'\b', text_lower):
                    return ral
        
        return None
    

    def _extract_ral_from_elements(self, soup: BeautifulSoup) -> Optional[str]:
        """Comprehensive RAL extraction from specific HTML elements."""
        # Priority search order for RAL numbers
        ral_search_targets = [
            # Design/Color sections
            {'elements': soup.find_all(['div', 'section', 'span'], class_=re.compile(r'design|color|colour|ral', re.I))},
            {'elements': soup.find_all(['div', 'section', 'span'], id=re.compile(r'design|color|colour|ral', re.I))},
            
            # Data attributes and custom attributes
            {'elements': soup.find_all(attrs={'data-ral': True})},
            {'elements': soup.find_all(attrs={'data-color': True})},
            {'elements': soup.find_all(attrs={'data-colour': True})},
            
            # Specification sections
            {'elements': soup.find_all(['div', 'section'], class_=re.compile(r'spec|technical|details', re.I))},
            
            # Product details
            {'elements': soup.find_all(['div', 'section'], class_=re.compile(r'product|item', re.I))},
            
            # Any element with text containing "RAL"
            {'elements': soup.find_all(text=re.compile(r'RAL\s*\d{4}', re.I))},
        ]
        
        for target_group in ral_search_targets:
            elements = target_group.get('elements', [])
            
            for element in elements:
                if hasattr(element, 'get_text'):
                    text = element.get_text(separator=' ')
                elif isinstance(element, str):
                    # This handles text nodes
                    text = element
                else:
                    continue
                    
                ral = self._extract_ral_number(text)
                if ral:
                    return ral
                
                # Check attributes for RAL data
                if hasattr(element, 'attrs'):
                    for attr_name, attr_value in element.attrs.items():
                        if isinstance(attr_value, str):
                            attr_ral = self._extract_ral_number(attr_value)
                            if attr_ral:
                                return attr_ral
        
        return None

    def _extract_ral_from_nested_json(self, data: dict, product_data: ProductData):
        """Extract RAL numbers from nested JSON structures."""
        def search_nested(obj, depth=0):
            if depth > 5:  # Prevent infinite recursion
                return None
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    key_lower = str(key).lower()
                    if any(term in key_lower for term in ['color', 'colour', 'ral', 'finish', 'paint']):
                        if isinstance(value, (str, int)):
                            ral = self._extract_ral_number(str(value))
                            if ral:
                                return ral
                    
                    # Recursively search nested objects
                    nested_result = search_nested(value, depth + 1)
                    if nested_result:
                        return nested_result
                        
            elif isinstance(obj, list):
                for item in obj:
                    nested_result = search_nested(item, depth + 1)
                    if nested_result:
                        return nested_result
            
            elif isinstance(obj, str):
                ral = self._extract_ral_number(obj)
                if ral:
                    return ral
            
            return None
        
        ral = search_nested(data)
        if ral and not product_data.ral_number:
            product_data.ral_number = ral


class BeautifulSoupStrategy(ScrapingStrategy):
    """Strategy using BeautifulSoup for HTML parsing."""
    
    def __init__(self):
        super().__init__("BeautifulSoup")
        self.timeout = 30
        self.max_retries = 3
    
    def can_handle(self, url: str) -> bool:
        """BeautifulSoup can handle most HTML pages."""
        try:
            parsed = urlparse(url)
            return parsed.scheme in ['http', 'https'] and parsed.netloc
        except:
            return False
    
    async def extract_data(self, url: str, session: aiohttp.ClientSession) -> Optional[ProductData]:
        """Extract data using BeautifulSoup."""
        self.logger.debug(f"Extracting data from {url}")
        
        try:
            # Fetch the webpage
            html_content = await self._fetch_html(url, session)
            if not html_content:
                return None
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract product data using various strategies
            product_data = ProductData(
                source_url=url,
                extracted_at=datetime.now(),
                extraction_method="BeautifulSoup"
            )
            
            # Try different extraction approaches
            self._extract_from_tables(soup, product_data)
            self._extract_from_lists(soup, product_data)
            self._extract_from_text(soup, product_data)
            self._extract_from_json_ld(soup, product_data)
            self._extract_from_javascript(soup, product_data)
            
            # Set default package units if not found (most products are sold individually)
            if not product_data.package_units:
                product_data.package_units = 1
                self.logger.debug("Set default package units to 1")
            
            # Calculate confidence based on extracted data
            product_data.extraction_confidence = self._calculate_confidence(product_data)
            
            self.logger.debug(f"Extracted data with confidence {product_data.extraction_confidence:.2f}")
            return product_data
            
        except Exception as e:
            self.logger.error(f"Failed to extract data from {url}: {str(e)}")
            return None
    
    async def _fetch_html(self, url: str, session: aiohttp.ClientSession) -> Optional[str]:
        """Fetch HTML content from URL."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        for attempt in range(self.max_retries):
            try:
                async with session.get(url, headers=headers, timeout=self.timeout) as response:
                    if response.status == 200:
                        content = await response.text()
                        return content
                    else:
                        self.logger.warning(f"HTTP {response.status} for {url}")
                        
            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{self.max_retries})")
            except Exception as e:
                self.logger.warning(f"Error fetching {url}: {str(e)} (attempt {attempt + 1}/{self.max_retries})")
            
            if attempt < self.max_retries - 1:
                await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
        
        return None
    
    def _extract_from_tables(self, soup: BeautifulSoup, product_data: ProductData):
        """Extract data from HTML tables."""
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = self._clean_text(cells[0].get_text())
                    value = self._clean_text(cells[1].get_text())
                    
                    self._match_and_extract(key, value, product_data)
    
    def _extract_from_lists(self, soup: BeautifulSoup, product_data: ProductData):
        """Extract data from HTML lists."""
        lists = soup.find_all(['ul', 'ol', 'dl'])
        
        for list_elem in lists:
            items = list_elem.find_all(['li', 'dt', 'dd'])
            
            for i, item in enumerate(items):
                text = self._clean_text(item.get_text())
                
                # Try to extract key-value pairs
                if ':' in text:
                    parts = text.split(':', 1)
                    if len(parts) == 2:
                        key, value = parts[0].strip(), parts[1].strip()
                        self._match_and_extract(key, value, product_data)
                else:
                    # Try to extract individual values
                    self._match_and_extract("", text, product_data)
    
    def _extract_from_text(self, soup: BeautifulSoup, product_data: ProductData):
        """Extract data from general text content with enhanced RAL detection."""
        # Get all text content
        text = soup.get_text(separator=' ')
        
        # Extract EAN codes
        if not product_data.ean:
            product_data.ean = self._extract_ean(text)
        
        # Extract RAL numbers from all text content
        if not product_data.ral_number:
            product_data.ral_number = self._extract_ral_number(text)
        
        # Additional comprehensive RAL extraction from specific elements
        if not product_data.ral_number:
            product_data.ral_number = self._extract_ral_from_elements(soup)
        
        # Look for dimension patterns
        dimension_patterns = [
            r'(\d+\.?\d*)\s*[x×]\s*(\d+\.?\d*)\s*[x×]\s*(\d+\.?\d*)\s*mm',
            r'(\d+\.?\d*)\s*mm\s*[x×]\s*(\d+\.?\d*)\s*mm\s*[x×]\s*(\d+\.?\d*)\s*mm',
            r'width[:\s]*(\d+\.?\d*)',
            r'height[:\s]*(\d+\.?\d*)',
            r'depth[:\s]*(\d+\.?\d*)'
        ]
        
        for pattern in dimension_patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                if len(matches[0]) == 3:  # W x H x D format
                    if not product_data.net_width:
                        product_data.net_width = float(matches[0][0])
                    if not product_data.net_height:
                        product_data.net_height = float(matches[0][1])
                    if not product_data.net_depth:
                        product_data.net_depth = float(matches[0][2])
    
    def _extract_from_json_ld(self, soup: BeautifulSoup, product_data: ProductData):
        """Extract data from JSON-LD structured data."""
        json_scripts = soup.find_all('script', type='application/ld+json')
        
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                
                if isinstance(data, dict) and data.get('@type') == 'Product':
                    self.logger.debug(f"Found JSON-LD Product data: {list(data.keys())}")
                    
                    # Extract EAN/Product code - prefer 'name' over 'sku' for ABB
                    if 'name' in data and not product_data.ean:
                        product_data.ean = str(data['name'])
                        self.logger.debug(f"Extracted EAN from JSON-LD name: {product_data.ean}")
                    elif 'sku' in data and not product_data.ean:
                        product_data.ean = str(data['sku'])
                        self.logger.debug(f"Extracted EAN from JSON-LD sku: {product_data.ean}")
                    
                    # Extract dimensions from JSON-LD
                    if 'width' in data and not product_data.net_width:
                        width_str = str(data['width'])
                        width_value = self._extract_numeric(width_str)
                        if width_value:
                            product_data.net_width = width_value
                            self.logger.debug(f"Extracted width: {width_value}")
                    
                    if 'height' in data and not product_data.net_height:
                        height_str = str(data['height'])
                        height_value = self._extract_numeric(height_str)
                        if height_value:
                            product_data.net_height = height_value
                            self.logger.debug(f"Extracted height: {height_value}")
                    
                    if 'depth' in data and not product_data.net_depth:
                        depth_str = str(data['depth'])
                        depth_value = self._extract_numeric(depth_str)
                        if depth_value:
                            product_data.net_depth = depth_value
                            self.logger.debug(f"Extracted depth: {depth_value}")
                    
                    # Extract weight from JSON-LD
                    if 'weight' in data and not product_data.package_weight:
                        weight_str = str(data['weight'])
                        weight_value = self._extract_numeric(weight_str)
                        if weight_value:
                            product_data.package_weight = weight_value
                            self.logger.debug(f"Extracted weight: {weight_value}")
                    
                    # Enhanced RAL extraction from all possible JSON-LD fields
                    ral_fields = ['description', 'color', 'colour', 'finish', 'paint', 'material', 'surface']
                    for field in ral_fields:
                        if field in data and not product_data.ral_number:
                            field_value = str(data[field])
                            ral = self._extract_ral_number(field_value)
                            if ral:
                                product_data.ral_number = ral
                                self.logger.debug(f"Extracted RAL from JSON-LD {field}: {ral}")
                                break
                    
                    # Check nested objects and arrays for RAL data
                    if not product_data.ral_number:
                        self._extract_ral_from_nested_json(data, product_data)
                    
                    # Check offers for additional data
                    if 'offers' in data and isinstance(data['offers'], dict):
                        offers = data['offers']
                        if 'sku' in offers and not product_data.ean:
                            product_data.ean = str(offers['sku'])
                    
                    # Look for additional properties
                    if 'additionalProperty' in data:
                        props = data['additionalProperty']
                        if isinstance(props, list):
                            for prop in props:
                                if isinstance(prop, dict):
                                    name = prop.get('name', '').lower()
                                    value = str(prop.get('value', ''))
                                    self._match_and_extract(name, value, product_data)
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON-LD: {e}")
                continue
    
    def _extract_from_javascript(self, soup: BeautifulSoup, product_data: ProductData):
        """Extract data from JavaScript variables that might contain package information."""
        script_tags = soup.find_all('script', string=True)
        
        for script in script_tags:
            script_content = script.string
            if not script_content:
                continue
            
            # Look for common JavaScript patterns that might contain package units
            patterns = [
                r'package["\']?\s*:\s*["\']?(\d+)',
                r'packageSize["\']?\s*:\s*["\']?(\d+)',
                r'unitsPerPackage["\']?\s*:\s*["\']?(\d+)',
                r'quantity["\']?\s*:\s*["\']?(\d+)',
                r'packSize["\']?\s*:\s*["\']?(\d+)',
                r'pieces["\']?\s*:\s*["\']?(\d+)'
            ]
            
            for pattern in patterns:
                import re
                matches = re.findall(pattern, script_content, re.IGNORECASE)
                if matches and not product_data.package_units:
                    try:
                        units = int(matches[0])
                        if 1 <= units <= 1000:  # Reasonable range for package units
                            product_data.package_units = units
                            self.logger.debug(f"Extracted package units from JavaScript: {units}")
                            break
                    except ValueError:
                        continue
    
    def _match_and_extract(self, key: str, value: str, product_data: ProductData):
        """Match key-value pairs and extract relevant data."""
        key_lower = key.lower()
        value_clean = self._clean_text(value)
        
        # EAN codes
        if any(term in key_lower for term in ['ean', 'barcode', 'gtin']) and not product_data.ean:
            ean = self._extract_ean(value_clean)
            if ean:
                product_data.ean = ean
        
        # RAL numbers - enhanced detection
        if any(term in key_lower for term in ['ral', 'color', 'colour', 'finish', 'paint']) and not product_data.ral_number:
            ral = self._extract_ral_number(value_clean)
            if ral:
                product_data.ral_number = ral
        
        # Also check if the value itself contains RAL info even without specific key
        if not product_data.ral_number:
            ral = self._extract_ral_number(value_clean)
            if ral:
                product_data.ral_number = ral
        
        # Dimensions
        if any(term in key_lower for term in ['width', 'larg']) and not product_data.net_width:
            width = self._extract_numeric(value_clean)
            if width:
                product_data.net_width = width
        
        if any(term in key_lower for term in ['height', 'înălţime', 'inaltime']) and not product_data.net_height:
            height = self._extract_numeric(value_clean)
            if height:
                product_data.net_height = height
        
        if any(term in key_lower for term in ['depth', 'adânc', 'adanc']) and not product_data.net_depth:
            depth = self._extract_numeric(value_clean)
            if depth:
                product_data.net_depth = depth
        
        # Package information - expanded search terms
        package_terms = [
            'units', 'bucăți', 'bucati', 'buc', 'pieces', 'pcs', 'qty', 'quantity',
            'pack', 'package', 'per package', 'per pack', 'unit pack', 'package size'
        ]
        if any(term in key_lower for term in package_terms) and not product_data.package_units:
            units = self._extract_numeric(value_clean)
            if units:
                product_data.package_units = int(units)
        
        if any(term in key_lower for term in ['weight', 'greutate', 'kg']) and not product_data.package_weight:
            weight = self._extract_numeric(value_clean)
            if weight:
                product_data.package_weight = weight
    
    def _calculate_confidence(self, product_data: ProductData) -> float:
        """Calculate confidence score based on extracted data."""
        fields = [
            product_data.ean,
            product_data.ral_number,
            product_data.net_width,
            product_data.net_height,
            product_data.net_depth,
            product_data.package_units,
            product_data.package_weight
        ]
        
        filled_fields = sum(1 for field in fields if field is not None)
        base_confidence = filled_fields / len(fields)
        
        # Boost confidence for critical fields
        if product_data.ean:
            base_confidence += 0.1
        if product_data.net_width and product_data.net_height and product_data.net_depth:
            base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def get_confidence_score(self) -> float:
        """BeautifulSoup is moderately reliable."""
        return 0.7


class PlaywrightStrategy(ScrapingStrategy):
    """Strategy using Playwright for JavaScript-heavy sites."""
    
    def __init__(self):
        super().__init__("Playwright")
        self.timeout = 30000  # 30 seconds in milliseconds
    
    def can_handle(self, url: str) -> bool:
        """Playwright can handle JavaScript-heavy sites."""
        try:
            parsed = urlparse(url)
            
            # Common domains that require JavaScript
            js_heavy_domains = [
                'angular', 'react', 'vue', 'spa',
                'shopify', 'wix', 'squarespace'
            ]
            
            domain_lower = parsed.netloc.lower()
            return any(indicator in domain_lower for indicator in js_heavy_domains)
            
        except:
            return False
    
    async def extract_data(self, url: str, session: aiohttp.ClientSession) -> Optional[ProductData]:
        """Extract data using Playwright."""
        try:
            # Import playwright here to avoid dependency issues if not installed
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Set user agent
                await page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                })
                
                # Navigate to page and wait for load
                await page.goto(url, timeout=self.timeout)
                await page.wait_for_load_state('networkidle', timeout=self.timeout)
                
                # Get page content
                content = await page.content()
                await browser.close()
                
                # Use BeautifulSoup to parse the rendered content
                soup = BeautifulSoup(content, 'html.parser')
                
                # Create product data
                product_data = ProductData(
                    source_url=url,
                    extracted_at=datetime.now(),
                    extraction_method="Playwright"
                )
                
                # Use similar extraction logic as BeautifulSoup
                self._extract_data_from_soup(soup, product_data)
                
                # Calculate confidence
                product_data.extraction_confidence = self._calculate_confidence(product_data)
                
                return product_data
                
        except ImportError:
            self.logger.error("Playwright not installed. Install with: pip install playwright")
            return None
        except Exception as e:
            self.logger.error(f"Playwright extraction failed for {url}: {str(e)}")
            return None
    
    def _extract_data_from_soup(self, soup: BeautifulSoup, product_data: ProductData):
        """Extract data from parsed HTML (similar to BeautifulSoup strategy)."""
        # Reuse BeautifulSoup extraction logic
        bs_strategy = BeautifulSoupStrategy()
        bs_strategy._extract_from_tables(soup, product_data)
        bs_strategy._extract_from_lists(soup, product_data)
        bs_strategy._extract_from_text(soup, product_data)
        bs_strategy._extract_from_json_ld(soup, product_data)
    
    def _calculate_confidence(self, product_data: ProductData) -> float:
        """Calculate confidence for Playwright extraction."""
        bs_strategy = BeautifulSoupStrategy()
        return bs_strategy._calculate_confidence(product_data)
    
    def get_confidence_score(self) -> float:
        """Playwright is highly reliable for JavaScript sites."""
        return 0.9


class AzureAIStrategy(ScrapingStrategy):
    """Strategy using Azure AI Form Recognizer for data extraction."""
    
    def __init__(self, endpoint: str, api_key: str):
        super().__init__("AzureAI")
        self.endpoint = endpoint
        self.api_key = api_key
        self.confidence_threshold = 0.8
    
    def can_handle(self, url: str) -> bool:
        """Azure AI can handle any URL if credentials are configured."""
        return bool(self.endpoint and self.api_key)
    
    async def extract_data(self, url: str, session: aiohttp.ClientSession) -> Optional[ProductData]:
        """Extract data using Azure AI Form Recognizer."""
        try:
            from azure.ai.formrecognizer import DocumentAnalysisClient
            from azure.core.credentials import AzureKeyCredential
            
            # Create Azure client
            client = DocumentAnalysisClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key)
            )
            
            # Analyze the webpage URL
            poller = await client.begin_analyze_document_from_url(
                "prebuilt-document", url
            )
            result = await poller.result()
            
            # Extract data from Azure AI results
            product_data = ProductData(
                source_url=url,
                extracted_at=datetime.now(),
                extraction_method="Azure AI"
            )
            
            # Process key-value pairs
            if result.key_value_pairs:
                for kv_pair in result.key_value_pairs:
                    if kv_pair.key and kv_pair.value:
                        key_text = kv_pair.key.content.lower()
                        value_text = kv_pair.value.content
                        confidence = kv_pair.confidence
                        
                        if confidence >= self.confidence_threshold:
                            self._extract_from_azure_kv(key_text, value_text, product_data)
            
            # Process tables
            if result.tables:
                for table in result.tables:
                    self._extract_from_azure_table(table, product_data)
            
            # Calculate overall confidence
            product_data.extraction_confidence = self._calculate_azure_confidence(result)
            
            return product_data
            
        except ImportError:
            self.logger.error("Azure Form Recognizer SDK not installed. Install with: pip install azure-ai-formrecognizer")
            return None
        except Exception as e:
            self.logger.error(f"Azure AI extraction failed for {url}: {str(e)}")
            return None
    
    def _extract_from_azure_kv(self, key: str, value: str, product_data: ProductData):
        """Extract data from Azure AI key-value pairs."""
        # Reuse the matching logic from BeautifulSoup strategy
        bs_strategy = BeautifulSoupStrategy()
        bs_strategy._match_and_extract(key, value, product_data)
    
    def _extract_from_azure_table(self, table, product_data: ProductData):
        """Extract data from Azure AI table results."""
        # Process table cells to find key-value pairs
        for cell in table.cells:
            if cell.row_index == 0:  # Skip header row
                continue
            
            # Try to find corresponding key in the same row
            row_cells = [c for c in table.cells if c.row_index == cell.row_index]
            
            if len(row_cells) >= 2:
                key_text = row_cells[0].content.lower()
                value_text = row_cells[1].content
                
                if cell.confidence >= self.confidence_threshold:
                    self._extract_from_azure_kv(key_text, value_text, product_data)
    
    def _calculate_azure_confidence(self, result) -> float:
        """Calculate confidence based on Azure AI results."""
        if not result.key_value_pairs and not result.tables:
            return 0.0
        
        total_confidence = 0.0
        item_count = 0
        
        # Average confidence from key-value pairs
        if result.key_value_pairs:
            for kv_pair in result.key_value_pairs:
                total_confidence += kv_pair.confidence
                item_count += 1
        
        # Average confidence from tables
        if result.tables:
            for table in result.tables:
                for cell in table.cells:
                    total_confidence += cell.confidence
                    item_count += 1
        
        return total_confidence / item_count if item_count > 0 else 0.0
    
    def get_confidence_score(self) -> float:
        """Azure AI is highly reliable."""
        return 0.95