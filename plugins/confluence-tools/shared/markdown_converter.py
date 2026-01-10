"""
Markdown to Confluence storage format converter.

Converts common markdown elements to Confluence XHTML storage format.
"""

import re
from typing import Optional


def markdown_to_confluence(markdown_text: str) -> str:
    """
    Convert markdown text to Confluence storage format (XHTML).

    Handles:
    - Headers (h1-h6)
    - Bold and italic
    - Code blocks (fenced and indented)
    - Inline code
    - Unordered and ordered lists
    - Links
    - Images
    - Blockquotes
    - Horizontal rules
    - Tables
    """
    lines = markdown_text.split('\n')
    result = []
    in_code_block = False
    code_block_lang = ""
    code_block_content = []
    in_list = False
    list_type = None
    list_items = []
    in_table = False
    table_rows = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Handle fenced code blocks
        if line.startswith('```'):
            if in_code_block:
                # End code block
                result.append(_format_code_block('\n'.join(code_block_content), code_block_lang))
                in_code_block = False
                code_block_content = []
                code_block_lang = ""
            else:
                # Start code block - flush any pending list
                if in_list:
                    result.append(_format_list(list_items, list_type))
                    in_list = False
                    list_items = []
                in_code_block = True
                code_block_lang = line[3:].strip()
            i += 1
            continue

        if in_code_block:
            code_block_content.append(line)
            i += 1
            continue

        # Handle tables
        if '|' in line and line.strip().startswith('|'):
            if in_list:
                result.append(_format_list(list_items, list_type))
                in_list = False
                list_items = []

            # Check if this is separator row (|---|---|)
            if re.match(r'^\s*\|[\s\-:|]+\|\s*$', line):
                i += 1
                continue

            if not in_table:
                in_table = True
                table_rows = []

            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            table_rows.append(cells)
            i += 1
            continue
        elif in_table:
            result.append(_format_table(table_rows))
            in_table = False
            table_rows = []

        # Handle lists
        ul_match = re.match(r'^(\s*)[-*+]\s+(.+)$', line)
        ol_match = re.match(r'^(\s*)\d+\.\s+(.+)$', line)

        if ul_match or ol_match:
            new_type = 'ul' if ul_match else 'ol'
            match = ul_match or ol_match
            content = match.group(2)

            if in_list and list_type != new_type:
                result.append(_format_list(list_items, list_type))
                list_items = []

            in_list = True
            list_type = new_type
            list_items.append(_convert_inline(content))
            i += 1
            continue
        elif in_list and line.strip() == '':
            result.append(_format_list(list_items, list_type))
            in_list = False
            list_items = []
        elif in_list:
            result.append(_format_list(list_items, list_type))
            in_list = False
            list_items = []

        # Handle headers
        header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if header_match:
            level = len(header_match.group(1))
            content = _convert_inline(header_match.group(2))
            result.append(f'<h{level}>{content}</h{level}>')
            i += 1
            continue

        # Handle horizontal rule
        if re.match(r'^[-*_]{3,}\s*$', line):
            result.append('<hr />')
            i += 1
            continue

        # Handle blockquote
        if line.startswith('>'):
            quote_content = _convert_inline(line[1:].strip())
            result.append(f'<blockquote><p>{quote_content}</p></blockquote>')
            i += 1
            continue

        # Handle empty lines
        if line.strip() == '':
            i += 1
            continue

        # Regular paragraph
        result.append(f'<p>{_convert_inline(line)}</p>')
        i += 1

    # Flush any remaining content
    if in_code_block:
        result.append(_format_code_block('\n'.join(code_block_content), code_block_lang))
    if in_list:
        result.append(_format_list(list_items, list_type))
    if in_table:
        result.append(_format_table(table_rows))

    return '\n'.join(result)


def _convert_inline(text: str) -> str:
    """Convert inline markdown elements to HTML."""
    # Escape any existing HTML entities first (except in code)
    # Skip this to allow HTML passthrough

    # Images: ![alt](url)
    text = re.sub(
        r'!\[([^\]]*)\]\(([^)]+)\)',
        r'<ac:image><ri:url ri:value="\2"/></ac:image>',
        text
    )

    # Links: [text](url)
    text = re.sub(
        r'\[([^\]]+)\]\(([^)]+)\)',
        r'<a href="\2">\1</a>',
        text
    )

    # Bold: **text** or __text__
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__([^_]+)__', r'<strong>\1</strong>', text)

    # Italic: *text* or _text_
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    text = re.sub(r'(?<!\w)_([^_]+)_(?!\w)', r'<em>\1</em>', text)

    # Strikethrough: ~~text~~
    text = re.sub(r'~~([^~]+)~~', r'<del>\1</del>', text)

    # Inline code: `code`
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

    return text


def _format_code_block(content: str, language: str = "") -> str:
    """Format a code block in Confluence storage format."""
    # Escape CDATA end sequence if present
    content = content.replace(']]>', ']]]]><![CDATA[>')

    lang_param = ""
    if language:
        lang_param = f'<ac:parameter ac:name="language">{_escape_xml(language)}</ac:parameter>'

    return f'''<ac:structured-macro ac:name="code">
{lang_param}<ac:plain-text-body><![CDATA[{content}]]></ac:plain-text-body>
</ac:structured-macro>'''


def _format_list(items: list, list_type: str) -> str:
    """Format a list in HTML."""
    tag = list_type
    items_html = '\n'.join(f'<li>{item}</li>' for item in items)
    return f'<{tag}>\n{items_html}\n</{tag}>'


def _format_table(rows: list) -> str:
    """Format a table in HTML."""
    if not rows:
        return ''

    result = ['<table>']

    # First row as header
    if rows:
        result.append('<tr>')
        for cell in rows[0]:
            result.append(f'<th>{_convert_inline(cell)}</th>')
        result.append('</tr>')

    # Remaining rows as body
    for row in rows[1:]:
        result.append('<tr>')
        for cell in row:
            result.append(f'<td>{_convert_inline(cell)}</td>')
        result.append('</tr>')

    result.append('</table>')
    return '\n'.join(result)


def _escape_xml(text: str) -> str:
    """Escape special XML characters."""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;'))
