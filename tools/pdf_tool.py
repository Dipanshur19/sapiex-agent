"""
tools/pdf_tool.py — Extract text and tables from PDF files.

Design choices:
- We use pdfplumber which handles both text-layer PDFs and can extract tables.
- Pages are read up to MAX_PAGES to avoid overwhelming the context window.
- Tables are formatted as pipe-separated rows so the LLM can parse them.
- If a page has no extractable text it's noted (could be a scanned image).
"""
import os
import pdfplumber


MAX_PAGES = 30  # Hard cap to protect context window


def read_pdf(path: str) -> str:
    """
    Extract all text and tables from a PDF.
    Returns a single formatted string.
    """
    path = os.path.expanduser(path)

    if not os.path.exists(path):
        return f"ERROR: File not found: '{path}'"
    if not path.lower().endswith(".pdf"):
        return f"ERROR: '{path}' does not appear to be a PDF."

    try:
        with pdfplumber.open(path) as pdf:
            total_pages = len(pdf.pages)
            pages_to_read = min(total_pages, MAX_PAGES)

            parts: list[str] = []
            parts.append(
                f"=== PDF: {os.path.basename(path)} ===\n"
                f"Total pages: {total_pages}  |  Reading: {pages_to_read} pages\n"
            )

            for i, page in enumerate(pdf.pages[:pages_to_read]):
                page_num = i + 1
                page_parts: list[str] = [f"--- Page {page_num} ---"]

                # Extract raw text
                text = page.extract_text()
                if text and text.strip():
                    page_parts.append(text.strip())
                else:
                    page_parts.append("[No selectable text on this page — may be a scanned image]")

                # Extract tables (if any)
                tables = page.extract_tables()
                for t_idx, table in enumerate(tables, 1):
                    formatted = _format_table(table)
                    if formatted:
                        page_parts.append(f"\n[Table {t_idx} on page {page_num}]\n{formatted}")

                parts.append("\n".join(page_parts))

            if total_pages > MAX_PAGES:
                parts.append(
                    f"\n[NOTE: Only the first {MAX_PAGES} of {total_pages} pages were read. "
                    f"Ask to read specific pages if you need more.]"
                )

            return "\n\n".join(parts)

    except Exception as e:
        return f"ERROR reading PDF '{path}': {type(e).__name__}: {e}"


def _format_table(table: list) -> str:
    """Convert a pdfplumber table (list of lists) into a readable string."""
    if not table:
        return ""

    rows: list[str] = []
    for row in table:
        # Replace None with empty string, strip whitespace
        cells = [str(cell).strip() if cell is not None else "" for cell in row]
        rows.append(" | ".join(cells))

    return "\n".join(rows)
