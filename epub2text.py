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

def clean_html(html):
    """Convert HTML to plain text preserving line breaks and marking headings without extra blanks inside paragraphs."""
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
        'p|blockquote|pre|table|ul|ol|dl'
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

def clean_html_with_pandoc(html: str) -> str:
    """Use BeautifulSoup + pypandoc to convert HTML to plain text, preserving paragraphing.

    - Removes <script>/<style>
    - Uses pandoc (if available) to convert HTML -> plain text with natural paragraph breaks
    - Converts markdown-style headers to the same markers we use
    - Keeps exactly one blank line between paragraphs
    """
    # Fallback if deps missing
    if pypandoc is None or BeautifulSoup is None:
        return clean_html(html)

    # Remove scripts/styles and lightly normalize with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style']):
        tag.decompose()

    # Let pandoc do the heavy lifting
    try:
        text = pypandoc.convert_text(str(soup), 'plain', format='html', extra_args=['--wrap=none'])
    except Exception:
        return clean_html(html)

    # Normalize newlines
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Convert markdown-style headings to our markers
    def _md_heading_to_markers(line: str) -> str:
        s = line.strip()
        # Pandoc typically emits atx headers like '#', '##', ... in plain output
        if s.startswith('# '):
            return f"=== {s[2:].strip()} ==="
        if s.startswith('## '):
            return f"== {s[3:].strip()} =="
        if s.startswith('### '):
            return f"-- {s[4:].strip()} --"
        if s.startswith('#### '):
            return f"-- {s[5:].strip()} --"
        if s.startswith('##### '):
            return f"-- {s[6:].strip()} --"
        if s.startswith('###### '):
            return f"-- {s[7:].strip()} --"
        return line

    lines = [
        _md_heading_to_markers(l)
        for l in text.split('\n')
    ]
    text = '\n'.join(lines)

    # Ensure exactly one blank line after headings and between paragraphs
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Trim trailing spaces per line
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

def extract_epub(epub_file, output_dir, extract_images=True, use_pandoc=False):
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
        if use_pandoc:
            plain_text = clean_html_with_pandoc(content)
        else:
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
    parser.add_argument("--pandoc", action="store_true", help="Use BeautifulSoup + pypandoc to preserve paragraphing")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ EPUB file '{args.input}' not found!")
        return

    print(f"Processing '{args.input}' ...")
    if args.pandoc and (pypandoc is None or BeautifulSoup is None):
        print("⚠️  --pandoc requested but pypandoc/BeautifulSoup not available. Falling back to built-in converter.")
    use_pandoc = bool(args.pandoc and pypandoc is not None and BeautifulSoup is not None)
    extract_epub(args.input, args.output, args.images, use_pandoc)

if __name__ == "__main__":
    main()