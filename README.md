# EPUB2Text - EPUB to Plain Text Extractor

A Python script that converts EPUB files into clean, readable plain text files with proper paragraph preservation and chapter organization. Designed for ESP32 and other embedded systems that need clean text input.

## Features

- **Multiple HTML Conversion Methods**: Automatically uses the best available converter (html2text > BeautifulSoup > regex)
- **Proper Paragraph Preservation**: Maintains text structure and readability
- **Chapter Organization**: Extracts chapters in correct order with meaningful filenames
- **Image Extraction**: Optional image extraction alongside text
- **Metadata Preservation**: Saves book title and author information
- **Clean Output**: Removes HTML artifacts while preserving content structure

## Installation

### Basic Installation
```bash
pip install -r requirements.txt
```

### Optional Dependencies for Better Conversion
For the best text conversion quality, install these additional packages:
```bash
pip install beautifulsoup4 html2text
```

## Usage

### Basic Usage
```bash
python epub2text.py -i book.epub -o output_folder
```

### Extract with Images
```bash
python epub2text.py -i book.epub -o output_folder --images
```

### Choose Specific Converter
```bash
# Use html2text (best quality)
python epub2text.py -i book.epub -o output_folder --converter html2text

# Use BeautifulSoup (good quality)
python epub2text.py -i book.epub -o output_folder --converter beautifulsoup

# Use regex (fallback)
python epub2text.py -i book.epub -o output_folder --converter regex

# Auto-select best available (default)
python epub2text.py -i book.epub -o output_folder --converter auto
```

## Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `-i, --input` | Path to the EPUB file | Required |
| `-o, --output` | Output folder for text/images | `epub_output` |
| `--images` | Extract images as well | False |
| `--converter` | Choose HTML to text converter | `auto` |

## How It Works

### 1. EPUB Processing
The script uses the `EbookLib` library to:
- Parse the EPUB file structure
- Extract metadata (title, author)
- Process chapters in the correct reading order
- Handle images if requested

### 2. HTML to Text Conversion
The script employs a three-tier conversion system:

#### **html2text (Best Quality)**
- Uses the professional `html2text` library
- Excellent paragraph preservation
- Handles complex HTML structures
- Converts markdown-style headings to custom format

#### **BeautifulSoup (Good Quality)**
- Enhanced HTML parsing with semantic understanding
- Better handling of nested structures
- Improved list and table processing
- Preserves content hierarchy

#### **Regex (Fallback)**
- Original regex-based approach
- Works without external dependencies
- Handles basic HTML structures
- Token-based spacing system

### 3. Text Processing Pipeline

1. **HTML Cleaning**: Remove scripts, styles, and navigation elements
2. **Structure Recognition**: Identify headings, paragraphs, lists, and tables
3. **Content Extraction**: Convert HTML elements to readable text
4. **Formatting**: Apply consistent spacing and paragraph breaks
5. **Heading Conversion**: Transform HTML headings to custom markers:
   - `h1` → `=== Title ===`
   - `h2` → `== Title ==`
   - `h3-h6` → `-- Title --`

### 4. Output Organization

The script creates a structured output:
```
output_folder/
├── book_name/
│   ├── text/
│   │   ├── 001_Chapter_One.txt
│   │   ├── 002_Chapter_Two.txt
│   │   └── ...
│   ├── images/ (if --images used)
│   │   ├── image1.jpg
│   │   └── ...
│   └── metadata.txt
```

## Output Format

### Text Files
- Clean plain text with proper paragraph breaks
- Custom heading markers for easy identification
- Preserved list formatting (bullets and numbers)
- Table data converted to pipe-separated format

### Metadata File
```
Title: Book Title
Author: Author Name
```

## Examples

### Example 1: Basic Extraction
```bash
python epub2text.py -i "Gone Tomorrow.epub" -o books
```
Output:
```
Processing 'Gone Tomorrow.epub' ...
Available HTML converters: html2text, BeautifulSoup, regex

✅ Extraction complete!
Base folder: books/Gone_Tomorrow
Text files in: books/Gone_Tomorrow/text
Metadata in: books/Gone_Tomorrow/metadata.txt
```

### Example 2: With Images
```bash
python epub2text.py -i "Illustrated Book.epub" -o output --images
```

## Dependencies

### Required
- `EbookLib==0.19` - EPUB file processing
- `lxml==6.0.2` - XML parsing
- `six==1.17.0` - Python 2/3 compatibility

### Optional (for better conversion)
- `beautifulsoup4==4.13.5` - Enhanced HTML parsing
- `html2text==2025.4.15` - Professional HTML to text conversion
- `soupsieve==2.8` - CSS selector support for BeautifulSoup
- `typing_extensions==4.15.0` - Type hints support

## Troubleshooting

### Common Issues

1. **"EPUB file not found"**
   - Check the file path is correct
   - Ensure the file has `.epub` extension

2. **Poor text quality**
   - Install optional dependencies: `pip install beautifulsoup4 html2text`
   - Try different converters: `--converter html2text`

3. **Missing paragraphs**
   - The script automatically uses the best available converter
   - Check if the EPUB has proper HTML structure

### Converter Selection

The script automatically selects the best available converter:
1. **html2text** - Best quality, handles complex HTML
2. **BeautifulSoup** - Good quality, better than regex
3. **regex** - Fallback, works without dependencies

## Technical Details

### HTML Processing
- Removes `<script>`, `<style>`, `<nav>`, `<header>`, `<footer>` tags
- Preserves content structure and hierarchy
- Handles nested elements and complex layouts
- Converts tables to readable text format

### Text Normalization
- Normalizes whitespace and line breaks
- Preserves paragraph structure
- Removes excessive blank lines
- Maintains proper spacing between elements

### File Naming
- Uses chapter numbers for ordering (001_, 002_, etc.)
- Extracts meaningful titles from content
- Handles duplicate filenames automatically
- Creates safe filenames for all operating systems

## License

This project is open source. Feel free to modify and distribute according to your needs.

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests to improve the script.
