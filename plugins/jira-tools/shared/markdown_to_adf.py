#!/usr/bin/env python3
"""
Convert markdown text to Atlassian Document Format (ADF).

Supports:
  - Headings (## Heading)
  - Paragraphs (blank-line separated)
  - Bullet lists (- item or * item)
  - Ordered lists (1. item)
  - Fenced code blocks (``` ... ```)
  - Horizontal rules (--- or ***)
  - Tables (| col | col |)
  - Bold (**text**), Italic (*text*), Inline code (`code`)
  - Links ([text](url))

Usage:
    from markdown_to_adf import markdown_to_adf
    adf_doc = markdown_to_adf("## Hello\\n\\nSome **bold** text")
"""

import re
from typing import Optional


def markdown_to_adf(text: str) -> dict:
    """Convert markdown text to an ADF document."""
    if not text or not text.strip():
        return {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": " "}]}
            ],
        }

    blocks = _parse_blocks(text)
    return {"type": "doc", "version": 1, "content": blocks}


# ---------------------------------------------------------------------------
# Inline parsing
# ---------------------------------------------------------------------------

# Order matters: code first (no nesting), then bold, italic, links
_INLINE_RE = re.compile(
    r"(`[^`]+`)"  # inline code
    r"|(\*\*(?:[^*]|\*(?!\*))+\*\*)"  # bold **...**
    r"|(\*(?:[^*])+\*)"  # italic *...*
    r"|(\[[^\]]+\]\([^)]+\))"  # link [text](url)
)


def _parse_inline(text: str) -> list[dict]:
    """Parse inline markdown formatting into ADF text nodes."""
    if not text:
        return []

    nodes: list[dict] = []
    last_end = 0

    for m in _INLINE_RE.finditer(text):
        # Plain text before this match
        if m.start() > last_end:
            plain = text[last_end : m.start()]
            if plain:
                nodes.append({"type": "text", "text": plain})

        matched = m.group(0)

        if m.group(1):  # inline code
            nodes.append(
                {"type": "text", "text": matched[1:-1], "marks": [{"type": "code"}]}
            )
        elif m.group(2):  # bold
            inner = matched[2:-2]
            nodes.append(
                {"type": "text", "text": inner, "marks": [{"type": "strong"}]}
            )
        elif m.group(3):  # italic
            inner = matched[1:-1]
            nodes.append({"type": "text", "text": inner, "marks": [{"type": "em"}]})
        elif m.group(4):  # link
            link_m = re.match(r"\[([^\]]+)\]\(([^)]+)\)", matched)
            if link_m:
                nodes.append(
                    {
                        "type": "text",
                        "text": link_m.group(1),
                        "marks": [
                            {
                                "type": "link",
                                "attrs": {"href": link_m.group(2)},
                            }
                        ],
                    }
                )

        last_end = m.end()

    # Remaining plain text
    if last_end < len(text):
        remaining = text[last_end:]
        if remaining:
            nodes.append({"type": "text", "text": remaining})

    return nodes if nodes else [{"type": "text", "text": text}]


def _make_paragraph(text: str) -> dict:
    """Create a paragraph node from text with inline parsing."""
    content = _parse_inline(text)
    return {"type": "paragraph", "content": content}


# ---------------------------------------------------------------------------
# Block parsing
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_BULLET_RE = re.compile(r"^(\s*)[-*]\s+(.+)$")
_ORDERED_RE = re.compile(r"^(\s*)\d+\.\s+(.+)$")
_HR_RE = re.compile(r"^(\s*[-*_]\s*){3,}$")
_TABLE_SEP_RE = re.compile(r"^\|?\s*[-:]+[-|:\s]+$")
_TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
_CODE_FENCE_RE = re.compile(r"^```(\w*)$")


def _parse_blocks(text: str) -> list[dict]:
    """Parse markdown text into ADF block nodes."""
    lines = text.split("\n")
    blocks: list[dict] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # --- Fenced code block ---
        code_m = _CODE_FENCE_RE.match(line.strip())
        if code_m:
            language = code_m.group(1) or None
            code_lines: list[str] = []
            i += 1
            while i < n and not _CODE_FENCE_RE.match(lines[i].strip()):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            block: dict = {
                "type": "codeBlock",
                "content": [{"type": "text", "text": "\n".join(code_lines)}],
            }
            if language:
                block["attrs"] = {"language": language}
            blocks.append(block)
            continue

        # --- Blank line ---
        if not line.strip():
            i += 1
            continue

        # --- Horizontal rule ---
        if _HR_RE.match(line.strip()):
            blocks.append({"type": "rule"})
            i += 1
            continue

        # --- Heading ---
        heading_m = _HEADING_RE.match(line.strip())
        if heading_m:
            level = len(heading_m.group(1))
            content = _parse_inline(heading_m.group(2))
            blocks.append(
                {
                    "type": "heading",
                    "attrs": {"level": level},
                    "content": content,
                }
            )
            i += 1
            continue

        # --- Table ---
        table_m = _TABLE_ROW_RE.match(line.strip())
        if table_m:
            table_lines: list[str] = []
            while i < n and _TABLE_ROW_RE.match(lines[i].strip()):
                table_lines.append(lines[i].strip())
                i += 1
                # Also consume separator line
                if i < n and _TABLE_SEP_RE.match(lines[i].strip()):
                    i += 1
            table_node = _parse_table(table_lines)
            if table_node:
                blocks.append(table_node)
            continue

        # --- Bullet list ---
        bullet_m = _BULLET_RE.match(line)
        if bullet_m:
            items: list[str] = []
            while i < n and _BULLET_RE.match(lines[i]):
                items.append(_BULLET_RE.match(lines[i]).group(2))
                i += 1
            blocks.append(
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [_make_paragraph(item)],
                        }
                        for item in items
                    ],
                }
            )
            continue

        # --- Ordered list ---
        ordered_m = _ORDERED_RE.match(line)
        if ordered_m:
            items_o: list[str] = []
            while i < n and _ORDERED_RE.match(lines[i]):
                items_o.append(_ORDERED_RE.match(lines[i]).group(2))
                i += 1
            blocks.append(
                {
                    "type": "orderedList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [_make_paragraph(item)],
                        }
                        for item in items_o
                    ],
                }
            )
            continue

        # --- Paragraph (default) ---
        # Collect consecutive non-blank, non-special lines
        para_lines: list[str] = []
        while i < n and lines[i].strip():
            peek = lines[i]
            # Stop if next line starts a new block type
            if (
                _HEADING_RE.match(peek.strip())
                or _HR_RE.match(peek.strip())
                or _CODE_FENCE_RE.match(peek.strip())
                or _TABLE_ROW_RE.match(peek.strip())
                or _BULLET_RE.match(peek)
                or _ORDERED_RE.match(peek)
            ):
                # Only break if we already have paragraph content
                if para_lines:
                    break
                # Otherwise this is the first line and shouldn't be a paragraph
                # (should have been caught above — safety fallback)
                para_lines.append(peek)
                i += 1
                break
            para_lines.append(peek)
            i += 1

        if para_lines:
            # Join lines with space for soft wraps, or preserve line breaks
            full_text = "\n".join(para_lines)
            blocks.append(_make_paragraph(full_text))

    return blocks if blocks else [_make_paragraph(" ")]


def _parse_table(table_lines: list[str]) -> Optional[dict]:
    """Parse markdown table lines into an ADF table node."""
    if not table_lines:
        return None

    rows: list[list[str]] = []
    for line in table_lines:
        # Skip separator rows
        if _TABLE_SEP_RE.match(line):
            continue
        # Split cells: strip leading/trailing |, then split on |
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)

    if not rows:
        return None

    table_rows: list[dict] = []
    for idx, row in enumerate(rows):
        cell_type = "tableHeader" if idx == 0 else "tableCell"
        cells = []
        for cell_text in row:
            cells.append(
                {
                    "type": cell_type,
                    "attrs": {},
                    "content": [_make_paragraph(cell_text)],
                }
            )
        table_rows.append({"type": "tableRow", "content": cells})

    return {
        "type": "table",
        "attrs": {"isNumberColumnEnabled": False, "layout": "default"},
        "content": table_rows,
    }
