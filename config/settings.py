"""
config/settings.py

Single source of truth for text/identity constants and static data lists
used across the whole dashboard. Change the app name, icon, or board
lists ONLY here — every page/component reads from this file.
"""

# ---------------------------------------------------------------------------
# App identity (used by the topbar / browser tab)
# ---------------------------------------------------------------------------
APP_NAME = "9th Class Results"
APP_SUBTITLE = "Analytics Dashboard"
APP_ICON = "school"          # Google "Material Symbols Outlined" icon name
PAGE_ICON = "🎓"              # browser tab favicon (emoji, used in st.set_page_config)
LAST_UPDATED = "10 Sep 2026"  # update this whenever the underlying data file changes

# ---------------------------------------------------------------------------
# Data file location
# ---------------------------------------------------------------------------
MASTER_XLSX_PATH = "data/BISE_9th_MASTER_2025-2026.xlsx"

# ---------------------------------------------------------------------------
# Boards covered by this dashboard (15 total)
# ---------------------------------------------------------------------------
ALL_BOARDS = [
    "Abbottabad", "Bahawalpur", "Bannu", "DGK", "FBISE", "FSD",
    "Gujranwala", "Kohat", "Lahore", "Mardan", "Peshawar",
    "Rawalpindi", "Sahiwal", "Sargodha", "Swat",
]

YEARS = [2025, 2026]

# ---------------------------------------------------------------------------
# Color palette (kept generic here; actual CSS values live in styles/theme.py)
# ---------------------------------------------------------------------------
