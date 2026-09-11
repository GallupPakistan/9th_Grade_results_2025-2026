"""
data/loader.py

All Excel reading happens here and ONLY here — pages/charts should never
call pandas/openpyxl directly. This keeps caching in one place and means
if the master file's path or structure changes, only this file needs an
edit.

Header-offset handling: most per-board sheets in the master workbook
start with a clean header on row 0, but several (Gujranwala, Kohat,
Lahore, Mardan, Peshawar, Rawalpindi, Sahiwal — verified by inspecting
every sheet's raw rows) have a title/note row above the real header,
because the source gazette's PDF table had a caption baked into row 1.
load_sheet() auto-detects the real header row by scanning the first
few rows for one containing a cell that reads exactly "Year" (every
board sheet's first real column), so callers never need to know or
care which sheets have the offset.

Usage from a page:
    from data.loader import load_sheet, list_sheets
    df = load_sheet("Overall Summary")
"""

import pandas as pd
import streamlit as st
from config.settings import MASTER_XLSX_PATH

# Sheets known to have a genuinely irregular layout that the generic
# "find the row that says Year" auto-detection cannot parse cleanly
# (multi-level/merged headers, or a caption-only first table). These
# are not used by any currently planned page/chart; load_sheet() will
# still return them via a plain header=0 read (may contain "Unnamed:"
# columns) rather than raising, but calling code should not rely on
# their column names without manual inspection first.
_IRREGULAR_LAYOUT_SHEETS = {
    "Kohat-Overall Result (9th+10th)",
    "Rawalpindi-Matric-Tech Group Pa",
}


def _detect_header_row(raw: pd.DataFrame, max_scan: int = 6) -> int:
    """Scans the first `max_scan` rows of a headerless read for the one
    that looks like the real header row (contains a cell that reads
    exactly "Year", case-insensitive — every board sheet's first real
    column). Returns 0 (no offset) if none is found."""
    for i in range(min(max_scan, len(raw))):
        row_values = [str(v).strip().lower() for v in raw.iloc[i].tolist()]
        if "year" in row_values:
            return i
    return 0


@st.cache_data(show_spinner="Loading data...")
def list_sheets() -> list[str]:
    xls = pd.ExcelFile(MASTER_XLSX_PATH)
    return xls.sheet_names


@st.cache_data(show_spinner="Loading data...")
def load_sheet(sheet_name: str) -> pd.DataFrame:
    """Load a single sheet by its exact name (see the 'Summary' index
    sheet in the workbook for the full list of sheet names).

    Auto-detects and skips a leading title/note row where the source
    gazette table had one — see module docstring. Sheets in
    _IRREGULAR_LAYOUT_SHEETS are read as-is (header=0) since their
    layout needs manual handling, not auto-detection.
    """
    if sheet_name in _IRREGULAR_LAYOUT_SHEETS:
        return pd.read_excel(MASTER_XLSX_PATH, sheet_name=sheet_name)

    raw = pd.read_excel(MASTER_XLSX_PATH, sheet_name=sheet_name, header=None)
    header_row = _detect_header_row(raw)
    if header_row == 0:
        return pd.read_excel(MASTER_XLSX_PATH, sheet_name=sheet_name)
    return pd.read_excel(MASTER_XLSX_PATH, sheet_name=sheet_name, header=header_row)


@st.cache_data(show_spinner="Loading data...")
def load_overall_summary() -> pd.DataFrame:
    """Convenience wrapper for the cross-board 'Overall Summary' sheet
    used on the Overview and Board Comparison pages."""
    return load_sheet("Overall Summary")


@st.cache_data(show_spinner="Loading all board sheets...")
def load_all_sheets() -> dict[str, pd.DataFrame]:
    """Loads every sheet in the workbook into a dict keyed by sheet name,
    each passed through the same header-offset auto-detection as
    load_sheet(). Use sparingly (e.g. only on an admin/debug page) —
    prefer load_sheet() for a single sheet a page actually needs."""
    return {name: load_sheet(name) for name in list_sheets()}


def board_sheet_name(board: str, table_suffix: str) -> str:
    """
    Builds the exact sheet name convention used in the master workbook,
    e.g. board_sheet_name("Abbottabad", "Overall Pass %")
         -> "Abbottabad-Overall Pass %"
    Sheet names are truncated to Excel's 31-char limit, so long
    board/suffix combinations may need the exact name looked up via
    list_sheets() instead of this helper.
    """
    name = f"{board}-{table_suffix}"
    return name[:31]