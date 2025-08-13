# Excel Product Data Extractor

A Python application that extracts product data from ABB websites using Excel hyperlinks.

## Features

- Modern GUI interface using CustomTkinter
- Processes Excel files with ABB product hyperlinks
- Extracts product data: EAN Code, RAL Number, Dimensions, Weight
- Creates clean output Excel with only extracted data
- Concurrent web scraping with SSL verification disabled
- Testing limit of 100 items for development

## Usage

1. Install dependencies: `pip install -r requirements.txt`
2. Run the application: `python main_modern.py`
3. Select your Excel file containing "FISA TEHNICA" hyperlinks
4. Wait for processing to complete
5. Open the generated output Excel file

## Output Columns

The application creates an Excel file with these columns only:
- Product Code
- EAN Code  
- RAL Number
- Net Width (mm)
- Net Height (mm)
- Net Depth (mm)
- Package Weight (kg)

## Configuration

Edit `config/settings.yaml` to modify:
- Concurrent request limits
- Timeout settings
- Output preferences
- UI theme and size