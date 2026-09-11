"""
data/availability.py

Maps each "comparison type" (gender / district / grade / etc.) to the
list of boards that actually publish usable data for it. Every filter
dropdown in the app should pull its `options=` list from here — never
hardcode a board list inside a page or chart file.

These lists were built by opening every one of the 58 per-board sheets
in the master workbook (raw rows, not just column names) and checking
what each board's Category/Candidate Type/Group columns actually
contain, plus whether numeric columns (like grade counts) are
populated or effectively empty. A board is only included in a list
below if it has real, non-trivial data for that comparison type.

When we add/verify data for a new board, update ONLY this file and
every filter across the whole dashboard picks it up automatically.
"""

# Boards whose gazette reports a Male/Female (or Boys/Girls) breakdown.
# In most boards this is embedded as combined text within a
# Category/Candidate Type column (e.g. "Regular (Boys)", "Private
# Female") rather than its own column — chart/loading code should
# expect to parse it out of that column. FSD is the only board with
# no gender breakdown anywhere in its sheets.
GENDER_AVAILABLE_BOARDS = [
    "Abbottabad", "Bahawalpur", "Bannu", "DGK", "FBISE", "Gujranwala",
    "Kohat", "Lahore", "Mardan", "Peshawar", "Rawalpindi", "Sahiwal",
    "Sargodha", "Swat",
]

# Boards whose gazette reports a district-wise breakdown.
DISTRICT_AVAILABLE_BOARDS = [
    "Bahawalpur", "DGK", "FSD", "Rawalpindi", "Sargodha",
]

# Boards whose gazette reports a letter-grade (A1/A/B/C/D/E) breakdown
# with real, populated counts. Bannu has a grade column in its sheet
# but it is ~99% zero (only 50 students total across the whole board
# have a non-zero grade recorded) — almost certainly an extraction gap
# in the source gazette rather than real data, so it is excluded here.
GRADE_AVAILABLE_BOARDS = [
    "Bahawalpur", "DGK", "Peshawar", "Sargodha", "Swat",
]

# Boards whose gazette includes a multi-year (5-year) historical trend
# table. None of the 15 boards' source gazettes actually published
# this — kept as an empty list (rather than removed) so any code that
# imports it fails safe/empty instead of raising ImportError.
TREND_AVAILABLE_BOARDS = []

# Boards with a Regular vs Private breakdown. All 15 boards report
# this in some form (FSD even has it as two fully separate sheets per
# table type), so this is deliberately the same as ALL_BOARDS rather
# than a subset — kept as its own list (not aliased) so a page can
# still filter on it explicitly and stay correct if a future board
# turns out not to have it.
REGULAR_PRIVATE_AVAILABLE_BOARDS = [
    "Abbottabad", "Bahawalpur", "Bannu", "DGK", "FBISE", "FSD",
    "Gujranwala", "Kohat", "Lahore", "Mardan", "Peshawar",
    "Rawalpindi", "Sahiwal", "Sargodha", "Swat",
]

# Boards with a Science vs Humanities/Arts (or broader group taxonomy,
# e.g. FSD's Science/General/Dars-e-Nazami/Computer Science/etc.)
# group-wise breakdown. All 15 boards report some form of this.
GROUP_AVAILABLE_BOARDS = [
    "Abbottabad", "Bahawalpur", "Bannu", "DGK", "FBISE", "FSD",
    "Gujranwala", "Kohat", "Lahore", "Mardan", "Peshawar",
    "Rawalpindi", "Sahiwal", "Sargodha", "Swat",
]

# Boards with a subject-wise pass-percentage table. Missing for Bannu,
# Mardan, and Sahiwal — their gazettes don't publish one.
SUBJECT_AVAILABLE_BOARDS = [
    "Abbottabad", "Bahawalpur", "DGK", "FBISE", "FSD", "Gujranwala",
    "Kohat", "Lahore", "Peshawar", "Rawalpindi", "Sargodha", "Swat",
]

# Boards with 2025 data available (Swat only has a 2026 gazette).
YEAR_2025_AVAILABLE_BOARDS = [b for b in [
    "Abbottabad", "Bahawalpur", "Bannu", "DGK", "FBISE", "FSD",
    "Gujranwala", "Kohat", "Lahore", "Mardan", "Peshawar",
    "Rawalpindi", "Sahiwal", "Sargodha",
]]

# Boards that report "Promoted %" instead of / alongside a strict Pass
# %, so chart/KPI code must NOT assume every board's "pass rate" is
# labeled or computed the same way (see charts using Group/Overall
# Result sheets for these boards).
PROMOTED_TERMINOLOGY_BOARDS = ["Mardan", "Peshawar"]

# Maps each province/region to the boards (from ALL_BOARDS) that fall
# under it. Only provinces that actually have at least one board in
# our 15-board dataset are listed here — a province filter widget
# should build its options from this dict's keys only, so it never
# offers a province (e.g. Sindh, Balochistan, AJK, Gilgit-Baltistan)
# that would produce an empty result.
PROVINCE_BOARD_MAP = {
    "Federal": ["FBISE"],
    "Punjab": [
        "Lahore", "Rawalpindi", "Gujranwala", "FSD", "Sargodha",
        "Sahiwal", "Bahawalpur", "DGK",
    ],
    "Khyber Pakhtunkhwa": [
        "Peshawar", "Swat", "Abbottabad", "Mardan", "Kohat", "Bannu",
    ],
}