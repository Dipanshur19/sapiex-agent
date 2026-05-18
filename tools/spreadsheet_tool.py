"""
tools/spreadsheet_tool.py — Read Excel (.xlsx/.xls) and CSV files.

Design choices:
- The model sees: column names, numeric summary stats, and the full data
  as a text table (capped at MAX_ROWS to protect context).
- For Excel with multiple sheets, each sheet is read separately.
- Numeric columns get min/max/mean/sum so the LLM can spot anomalies
  even without reading every cell.
- The raw data is shown as a string table so the LLM can cross-reference
  specific rows and values when comparing against a PDF.
"""
import os
import pandas as pd


MAX_ROWS = 200  # Max rows per sheet to show the LLM


def read_spreadsheet(path: str) -> str:
    """
    Read an Excel or CSV file and return a formatted text representation.
    """
    path = os.path.expanduser(path)

    if not os.path.exists(path):
        return f"ERROR: File not found: '{path}'"

    ext = os.path.splitext(path)[1].lower()

    if ext == ".csv":
        return _read_csv(path)
    elif ext in (".xlsx", ".xls", ".xlsm"):
        return _read_excel(path)
    else:
        return f"ERROR: Unsupported file type '{ext}'. Supported: .csv, .xlsx, .xls"


# ── CSV ──────────────────────────────────────────────────────────────────────

def _read_csv(path: str) -> str:
    try:
        df = pd.read_csv(path)
        parts = [f"=== CSV: {os.path.basename(path)} ==="]
        parts.append(_describe_df(df, "data"))
        parts.append(_df_to_text(df))
        return "\n\n".join(parts)
    except Exception as e:
        return f"ERROR reading CSV '{path}': {type(e).__name__}: {e}"


# ── Excel ─────────────────────────────────────────────────────────────────────

def _read_excel(path: str) -> str:
    try:
        xf = pd.ExcelFile(path)
        sheet_names = xf.sheet_names
        parts = [
            f"=== Excel: {os.path.basename(path)} ===\n"
            f"Sheets: {', '.join(sheet_names)}"
        ]
        for sheet in sheet_names:
            df = pd.read_excel(path, sheet_name=sheet)
            parts.append(f"\n── Sheet: {sheet} ──")
            parts.append(_describe_df(df, sheet))
            parts.append(_df_to_text(df))
        return "\n\n".join(parts)
    except Exception as e:
        return f"ERROR reading Excel '{path}': {type(e).__name__}: {e}"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _describe_df(df: pd.DataFrame, name: str) -> str:
    """Return a summary: shape, columns, and numeric stats."""
    lines = [
        f"Shape: {len(df)} rows × {len(df.columns)} columns",
        f"Columns: {', '.join(str(c) for c in df.columns)}",
    ]

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        lines.append("\nNumeric column summary:")
        for col in numeric_cols:
            s = df[col].dropna()
            if len(s) == 0:
                continue
            lines.append(
                f"  {col}: "
                f"count={len(s)}, "
                f"sum={s.sum():,.2f}, "
                f"mean={s.mean():,.2f}, "
                f"min={s.min():,.2f}, "
                f"max={s.max():,.2f}"
            )

    return "\n".join(lines)


def _df_to_text(df: pd.DataFrame) -> str:
    """Convert a DataFrame to a readable text table, capped at MAX_ROWS."""
    total = len(df)
    sample = df.head(MAX_ROWS)

    # Convert to string with full column width
    text = sample.to_string(index=True, max_colwidth=60)

    if total > MAX_ROWS:
        text += f"\n\n[Showing first {MAX_ROWS} of {total} rows]"

    return text
