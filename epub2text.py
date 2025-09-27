#!/usr/bin/env python3
"""
EPUB to Text Extractor for ESP32 (EbookLib Version)
---------------------------------------------------
Converts EPUB files into plain text and optionally extracts images
with proper chapter order using EbookLib.

Usage:
    python epub_to_text_ebooklib.py -i book.epub -o output_folder --images
"""

import os
import re
import argparse
from pathlib import Path
from ebooklib import epub, ITEM_DOCUMENT, ITEM_IMAGE
import html as html_unescape

# Optional dependencies for improved HTML->text conversion
try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:  # pragma: no cover
    BeautifulSoup = None  # type: ignore

try:
    import pypandoc  # type: ignore
except Exception:  # pragma: no cover
    pypandoc = None  # type: ignore

try:
    import html2text  # type: ignore
except Exception:  # pragma: no cover
    html2text = None  # type: ignore

def clean_html(html):
    """Convert HTML to plain text preserving line breaks and marking headings without extra blanks inside paragraphs."""
    # Use html2text if available for best paragraph preservation, then BeautifulSoup, then regex
    if html2text is not None:
        return clean_html_with_html2text(html)
    elif BeautifulSoup is not None:
        return clean_html_with_beautifulsoup(html)
    else:
        return clean_html_regex(html)

def clean_html_with_html2text(html):
    """Use html2text library for optimal HTML to text conversion with paragraph preservation."""
    # Configure html2text for optimal EPUB conversion
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    h.ignore_emphasis = False  # Keep bold/italic for headings
    h.body_width = 0  # Don't wrap lines
    h.unicode_snob = True
    h.escape_snob = True
    h.mark_code = False
    
    # Convert HTML to text
    text = h.handle(html)
    
    # Convert markdown-style headings to our custom format
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if line.startswith('# '):
            lines.append(f"=== {line[2:].strip()} ===")
        elif line.startswith('## '):
            lines.append(f"== {line[3:].strip()} ==")
        elif line.startswith('### '):
            lines.append(f"-- {line[4:].strip()} --")
        elif line.startswith('#### '):
            lines.append(f"-- {line[5:].strip()} --")
        elif line.startswith('##### '):
            lines.append(f"-- {line[6:].strip()} --")
        elif line.startswith('###### '):
            lines.append(f"-- {line[7:].strip()} --")
        else:
            lines.append(line)
    
    text = '\n'.join(lines)
    
    # Clean up excessive whitespace while preserving paragraph structure
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = '\n'.join(line.rstrip() for line in text.split('\n')).strip()
    
    return text

def clean_html_with_beautifulsoup(html):
    """Enhanced HTML to text conversion using BeautifulSoup for better paragraph preservation."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Remove scripts and styles
    for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
        tag.decompose()
    
    # Process headings first to preserve their structure
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        level = int(heading.name[1])
        text = heading.get_text().strip()
        if text:
            if level == 1:
                heading.replace_with(f"=== {text} ===\n\n")
            elif level == 2:
                heading.replace_with(f"== {text} ==\n\n")
            else:
                heading.replace_with(f"-- {text} --\n\n")
    
    # Handle block elements that should create paragraph breaks
    block_elements = ['p', 'div', 'blockquote', 'pre', 'section', 'article', 'aside']
    for tag in soup.find_all(block_elements):
        # Add paragraph break after block elements
        if tag.get_text().strip():
            tag.append('\n\n')
    
    # Handle lists
    for ul in soup.find_all('ul'):
        for li in ul.find_all('li'):
            li_text = li.get_text().strip()
            if li_text:
                li.replace_with(f"- {li_text}\n")
        ul.append('\n')
    
    for ol in soup.find_all('ol'):
        for i, li in enumerate(ol.find_all('li'), 1):
            li_text = li.get_text().strip()
            if li_text:
                li.replace_with(f"{i}. {li_text}\n")
        ol.append('\n')
    
    # Handle line breaks
    for br in soup.find_all('br'):
        br.replace_with('\n')
    
    # Handle tables - convert to simple text format
    for table in soup.find_all('table'):
        rows = []
        for tr in table.find_all('tr'):
            cells = [td.get_text().strip() for td in tr.find_all(['td', 'th'])]
            if cells:
                rows.append(' | '.join(cells))
        if rows:
            table.replace_with('\n'.join(rows) + '\n\n')
    
    # Get the text and clean it up
    text = soup.get_text()
    
    # Normalize whitespace
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\r', '\n', text)
    
    # Clean up multiple newlines but preserve paragraph structure
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove trailing spaces from lines
    lines = [line.rstrip() for line in text.split('\n')]
    text = '\n'.join(lines).strip()
    
    return text

def clean_html_regex(html):
    """Fallback regex-based HTML to text conversion (original implementation)."""
    # Remove scripts/styles first
    text = re.sub(r'<script.*?>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style.*?>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # Use placeholder tokens for precise spacing (defined early so headings can use them)
    BR = '\uE000BR\uE000'
    PARA = '\uE000PARA\uE000'
    LI = '\uE000LI\uE000'

    # Replace headings with readable markers (protected by tokens so they don't get inlined)
    def _replace_heading(match):
        level = int(match.group(1))
        inner = match.group(2)
        inner = re.sub(r'<[^>]+>', '', inner)
        inner = html_unescape.unescape(inner)
        inner = re.sub(r'[\t ]+', ' ', inner).strip()
        if not inner:
            return ''
        if level == 1:
            return f"=== {inner} ==={PARA}"
        if level == 2:
            return f"== {inner} =={PARA}"
        return f"-- {inner} --{PARA}"

    text = re.sub(r'<h([1-6])[^>]*>([\s\S]*?)</h\1>', _replace_heading, text, flags=re.IGNORECASE)

    # Line breaks
    text = re.sub(r'<br\s*/?>', BR, text, flags=re.IGNORECASE)
    text = re.sub(r'</(li|tr)>', BR, text, flags=re.IGNORECASE)

    # Paragraph/block handling: only true text blocks cause paragraph breaks
    block_tags = (
        'p|blockquote|pre|table|ul|ol|dl|div|section|article'
    )
    # Closing blocks create paragraph breaks
    text = re.sub(rf'<\s*/\s*(?:{block_tags})\s*>', PARA, text, flags=re.IGNORECASE)
    # Opening blocks do not add spacing
    text = re.sub(rf'<\s*(?:{block_tags})(?:\s+[^>]*)?>', '', text, flags=re.IGNORECASE)
    # Lists: start of list item marker
    text = re.sub(r'<\s*li\b[^>]*>', LI, text, flags=re.IGNORECASE)

    # Strip remaining tags
    text = re.sub(r'<[^>]+>', '', text)

    # Unescape entities
    text = html_unescape.unescape(text)

    # Normalize whitespace: remove raw source newlines to avoid accidental blanks
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\n', ' ')
    text = re.sub(r'[\t ]+', ' ', text).strip()

    # Prevent blank lines within paragraphs by collapsing multiple BRs and
    # removing BRs adjacent to paragraph breaks before expanding tokens
    text = re.sub(r'(?:' + re.escape(BR) + r'[\t ]*){2,}', BR, text)
    text = re.sub(re.escape(BR) + r'[\t ]*' + re.escape(PARA), PARA, text)
    text = re.sub(re.escape(PARA) + r'[\t ]*' + re.escape(BR), PARA, text)
    text = re.sub(r'(?:' + re.escape(PARA) + r'[\t ]*){2,}', PARA, text)

    # Re-introduce structural breaks
    text = text.replace(LI, '\n- ')
    text = text.replace(PARA, '\n\n')
    # Inline line breaks (BR) should flow as spaces inside a paragraph
    text = text.replace(BR, ' ')

    # Tidy: ensure exactly one blank line after headings and between paragraphs
    # Collapse 3+ newlines to 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    # If there are spaces before newlines, trim them
    text = '\n'.join(line.rstrip() for line in text.split('\n')).strip()

    return text


def _safe_filename(name: str) -> str:
    name = name.strip()
    if not name:
        return "Untitled"
    # Remove Windows-forbidden characters and normalize whitespace
    name = re.sub(r'[\\/:*?"<>|]+', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    # Replace spaces with underscores for readability
    name = name.replace(' ', '_')
    # Limit length and avoid trailing dot/space
    name = name[:80].rstrip(' .')
    return name or "Untitled"

def _derive_title(plain_text: str) -> str:
    # Prefer explicit heading markers we emit
    for line in plain_text.split('\n'):
        s = line.strip()
        if not s:
            continue
        if (s.startswith('=== ') and s.endswith(' ===')) or \
           (s.startswith('== ') and s.endswith(' ==')) or \
           (s.startswith('-- ') and s.endswith(' --')):
            title = s.strip('= -')
            title = re.sub(r'\s+', ' ', title).strip()
            if title:
                return title
        # Fallback to first meaningful non-list line
        if not s.startswith('- '):
            return s[:120]
    return "Untitled"

def extract_epub(epub_file, output_dir, extract_images=True):
    # Create a subfolder under output_dir based on EPUB filename
    epub_basename = os.path.splitext(os.path.basename(epub_file))[0]
    safe_epub_name = _safe_filename(epub_basename)
    base_out_dir = os.path.join(output_dir, safe_epub_name)
    os.makedirs(base_out_dir, exist_ok=True)
    text_dir = os.path.join(base_out_dir, "text")
    img_dir = os.path.join(base_out_dir, "images")
    os.makedirs(text_dir, exist_ok=True)
    if extract_images:
        os.makedirs(img_dir, exist_ok=True)

    # Load EPUB
    book = epub.read_epub(epub_file)

    # Save metadata
    title = book.get_metadata('DC', 'title')
    author = book.get_metadata('DC', 'creator')
    with open(os.path.join(base_out_dir, "metadata.txt"), "w", encoding="utf-8") as meta:
        meta.write(f"Title: {title[0][0] if title else 'Unknown'}\n")
        meta.write(f"Author: {author[0][0] if author else 'Unknown'}\n")

    # Extract text in correct chapter order
    chapter_num = 1
    for item in book.get_items_of_type(ITEM_DOCUMENT):
        content = item.get_content().decode("utf-8", errors="ignore")
       
        plain_text = clean_html(content)
        # Build intuitive filename using detected title or first meaningful line
        title_guess = _derive_title(plain_text)
        safe_title = _safe_filename(title_guess)
        filename = f"{chapter_num:03d}_{safe_title}.txt"
        chapter_file = os.path.join(text_dir, filename)
        # De-duplicate if same name exists
        suffix = 2
        while os.path.exists(chapter_file):
            filename = f"{chapter_num:03d}_{safe_title}_{suffix}.txt"
            chapter_file = os.path.join(text_dir, filename)
            suffix += 1
        with open(chapter_file, "w", encoding="utf-8") as out:
            out.write(plain_text)
        chapter_num += 1

    # Extract images if requested
    if extract_images:
        for item in book.get_items_of_type(ITEM_IMAGE):
            img_name = os.path.basename(item.get_name())
            with open(os.path.join(img_dir, img_name), "wb") as img_file:
                img_file.write(item.get_content())

    print(f"\n✅ Extraction complete!")
    print(f"Base folder: {base_out_dir}")
    print(f"Text files in: {text_dir}")
    print(f"Metadata in: {os.path.join(base_out_dir, 'metadata.txt')}")
    if extract_images:
        print(f"Images in: {img_dir}")

def main():
    parser = argparse.ArgumentParser(description="Convert EPUB to plain text for ESP32 (EbookLib)")
    parser.add_argument("-i", "--input", required=True, help="Path to the EPUB file")
    parser.add_argument("-o", "--output", default="epub_output", help="Output folder for text/images")
    parser.add_argument("--images", action="store_true", help="Extract images as well")
    parser.add_argument("--converter", choices=['auto', 'html2text', 'beautifulsoup', 'regex'], 
                       default='auto', help="Choose HTML to text converter (auto uses best available)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ EPUB file '{args.input}' not found!")
        return

    print(f"Processing '{args.input}' ...")
    
    # Show available converters
    available_converters = []
    if html2text is not None:
        available_converters.append("html2text")
    if BeautifulSoup is not None:
        available_converters.append("BeautifulSoup")
    available_converters.append("regex")
    
    print(f"Available HTML converters: {', '.join(available_converters)}")
    

    extract_epub(args.input, args.output, args.images)

if __name__ == "__main__":
    main()