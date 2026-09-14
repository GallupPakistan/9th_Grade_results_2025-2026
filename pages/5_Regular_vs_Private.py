"""
pages/5_Regular_vs_Private.py

Regular vs Private performance — all 15 boards publish a candidate-type
split (see data/availability.REGULAR_PRIVATE_AVAILABLE_BOARDS). Data
comes from data/recipes.py's verified extraction table (raw gazette
counts): Bahawalpur's and Rawalpindi's Regular sub-types (Govt./
Affiliated) are merged, and FBISE's 'Ex/Private' counts as Private.
Verified: Regular + Private sums equal each board's Overall Summary
totals EXACTLY (appeared & passed, both years) for all 15 boards.

Layout: year pills (2026 / 2025 / Both) + restricted board multiselect,
KPI row (Regular Pass % / Private Pass % / Gap / Widest-Gap Board),
hero grouped-bar chart, diverging gap bar, slope trend, stacked appeared
split, pass-% box plot, and a Board -> Category treemap.
"""

import streamlit as st
from config.settings import APP_NAME, PAGE_ICON
from styles.css import inject_css
from components.sidebar import render_sidebar
from components.topbar import render_topbar
from components.filter_bar import render_filter_bar
from components.filters import board_multiselect, data_availability_note
from components.kpi_card import render_kpi_row
from components.chart_card import chart_card
from data.recipes import load_category_table
from data.availability import REGULAR_PRIVATE_AVAILABLE_BOARDS
from charts.regular_private_charts import (
    category_kpis,
    chart_hero_category_pass_rate,
    chart_category_gap,
    chart_category_slope,
    chart_category_appeared,
    chart_category_box,
    chart_category_treemap,
    category_table,
)

st.set_page_config(page_title="Regular vs Private - " + APP_NAME, page_icon=PAGE_ICON, layout="wide")
inject_css()
render_sidebar()

render_topbar(
    active_page="Regular vs Private",
    subtitle="Regular vs Private candidate performance, for boards that report it.",
    stat_label="BISE Boards",
    stat_value="15",
    stat_icon="account_balance",
)

# ---------------------------------------------------------------------------
# Year selector — 2026 / 2025 / Both, same as the other comparison pages.
# ---------------------------------------------------------------------------
year_label = render_filter_bar(
    "Year",
    options=["2026", "2025", "Both"],
    default="2026",
    key="reg_priv_year_filter",
)
year_label = year_label or "2026"
if year_label == "Both":
    years = [2026, 2025]
else:
    years = [int(year_label)]
primary_year, other_year = max(years), min(years)

# ---------------------------------------------------------------------------
# Board multiselect — options FROM REGULAR_PRIVATE_AVAILABLE_BOARDS (all
# 15 boards publish a Regular/Private split).
# ---------------------------------------------------------------------------
st.markdown('<div class="filter-bar"><span class="filter-bar-label">Boards</span></div>',
            unsafe_allow_html=True)
selected_boards = board_multiselect(
    "Boards",
    available_boards=REGULAR_PRIVATE_AVAILABLE_BOARDS,
    key="reg_priv_board_filter",
    default_all=True,
)
data_availability_note("Regular vs Private", REGULAR_PRIVATE_AVAILABLE_BOARDS)

if not selected_boards:
    st.warning("Select at least one board to compare.")
    st.stop()

category_df = load_category_table()
category_df = category_df[category_df["Board"].isin(selected_boards)]

kpis = category_kpis(category_df, primary_year, other_year)
if kpis["widest_gap_board"] is None:
    st.info(f"No Regular/Private breakdown published for the selected boards in {primary_year}.")
    st.stop()

boards_n = kpis["boards"]
suffix = f"{boards_n} board{'s' if boards_n != 1 else ''}"

# ---------------------------------------------------------------------------
# KPI row (4 cards) — aggregate Pass % from RAW Passed/Appeared sums
# (never an average of board rates); Gap = Regular % − Private %.
# ---------------------------------------------------------------------------
reg, prv = kpis["regular"], kpis["private"]
render_kpi_row([
    {
        "icon": "school",
        "value": f"{reg['pct'] * 100:.1f}%",
        "label": f"Regular Pass % ({primary_year})",
        "delta": f"{kpis['regular_delta'] * 100:+.1f} pts vs {other_year}",
        "delta_positive": kpis["regular_delta"] >= 0,
        "accent": "blue",
        "spark": [reg["pct"] - kpis["regular_delta"], reg["pct"]],
    },
    {
        "icon": "groups",
        "value": f"{prv['pct'] * 100:.1f}%",
        "label": f"Private Pass % ({primary_year})",
        "delta": f"{kpis['private_delta'] * 100:+.1f} pts vs {other_year}",
        "delta_positive": kpis["private_delta"] >= 0,
        "accent": "gold",
        "spark": [prv["pct"] - kpis["private_delta"], prv["pct"]],
    },
    {
        "icon": "compare_arrows",
        "value": f"{kpis['gap'] * 100:+.1f} pp",
        "label": "Gap (Regular − Private)",
        "delta": f"{kpis['gap_delta'] * 100:+.1f} pts vs {other_year}",
        "delta_positive": kpis["gap_delta"] >= 0,
        "accent": "blue" if kpis["gap"] >= 0 else "red",
        "spark": [kpis["gap"] - kpis["gap_delta"], kpis["gap"]],
    },
    {
        "icon": "emoji_events",
        "value": str(kpis["widest_gap_board"]["board"]),
        "label": "Widest-Gap Board",
        "delta": f"{kpis['widest_gap_board']['gap'] * 100:+.1f} pp "
                 f"({'Regular' if kpis['widest_gap_board']['gap'] >= 0 else 'Private'} ahead)",
        "delta_positive": kpis["widest_gap_board"]["gap"] >= 0,
        "accent": "green",
    },
])

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
year_suffix = " & ".join(str(y) for y in years)

# ---- HERO: Regular vs Private Pass % per board (full width) ---------------
with chart_card("Pass % by Board — Regular vs Private", f"{year_suffix} · {suffix} · ordered by gap"):
    st.plotly_chart(chart_hero_category_pass_rate(category_df, years), width="stretch")

# ---- Row B: diverging gap bar + slope trend -------------------------------
col1, col2 = st.columns(2)
with col1:
    with chart_card("Gap (Regular % − Private %)", f"{year_suffix} · {suffix} · green = Regular ahead"):
        st.plotly_chart(chart_category_gap(category_df, years), width="stretch")
with col2:
    with chart_card("Pass % Slope 2025 → 2026", "Aggregate across the selected boards · raw sums"):
        st.plotly_chart(chart_category_slope(category_df), width="stretch")

# ---- Row C: appeared split + pass-% box plot ------------------------------
col3, col4 = st.columns(2)
with col3:
    with chart_card("Appeared Candidates by Board", f"{year_suffix} · Regular + Private stacked · {suffix}"):
        st.plotly_chart(chart_category_appeared(category_df, years), width="stretch")
with col4:
    with chart_card("Pass % Distribution", f"{year_suffix} · each point = one board"):
        st.plotly_chart(chart_category_box(category_df, years), width="stretch")

# ---- Board -> Category treemap (full width) --------------------------------
with chart_card("Board → Category Treemap", f"{primary_year} · box area = Appeared candidates · {suffix}"):
    st.plotly_chart(chart_category_treemap(category_df, primary_year), width="stretch")

# ---------------------------------------------------------------------------
# Full comparison table(s) — one per selected year. Swat (2026-only
# gazette) simply doesn't appear in the 2025 table — nothing invented.
# ---------------------------------------------------------------------------
table_years = years if len(years) > 1 else [primary_year]
for t_year in sorted(table_years, reverse=True):
    tdf = category_table(category_df, t_year)
    with chart_card("Full Comparison Table", f"{t_year} · {len(tdf)} board{'s' if len(tdf) != 1 else ''}"):
        st.dataframe(
            tdf,
            hide_index=True,
            column_config={
                "Board": st.column_config.TextColumn("Board", width="medium"),
                "R-Appeared": st.column_config.NumberColumn("Regular Appeared", format="%,d"),
                "R-Pass %": st.column_config.NumberColumn("Regular Pass %", format="%.1f%%"),
                "P-Appeared": st.column_config.NumberColumn("Private Appeared", format="%,d"),
                "P-Pass %": st.column_config.NumberColumn("Private Pass %", format="%.1f%%"),
                "Gap (pts)": st.column_config.NumberColumn("Gap (R − P, pts)", format="%+.1f%%"),
            },
        )

st.caption(
    "ℹ️ Data provenance: all 15 boards publish a Regular/Private candidate split — counts are "
    "parsed from each board's own gazette sheets (raw Appeared/Passed). "
    "Label normalization: Bahawalpur's 'Regular (Govt.)' + 'Regular (Affiliated)' use the sheet's "
    "own published 'Total (Regular)' row; Rawalpindi's 'Regular (Government Institutes)' + 'Regular "
    "(Affiliated Institutes)' are merged into Regular; 'Private Candidates' (Rawalpindi) and "
    "'Ex/Private' (FBISE) count as Private. "
    "Every rollup row is excluded: Bahawalpur 'Grand Total', Bannu 'Sub Total'/'G. Total', DGK "
    "'Grand Total', FBISE 'Grand Total', FSD 'Overall …Candidates', Gujranwala 'Sub Total'/'Grand "
    "Total', Kohat 'Total'/'Grand Total (Science + General)', Mardan 'TOTAL', Rawalpindi "
    "'Sub-Total'/'GRAND TOTAL', Sahiwal & Sargodha 'Overall', Swat 'Sub Total'/'Grand Total'. "
    "COVERAGE CHECK: Regular + Private Appeared AND Passed equal each board's Overall Summary "
    "totals exactly for both years — no candidate is unaccounted for. "
    "Mardan & Peshawar report 'Promoted' as pass. "
    "Swat has only a 2026 gazette — no 2025 Regular/Private data."
)
