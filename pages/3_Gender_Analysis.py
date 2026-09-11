"""
pages/3_Gender_Analysis.py

Male vs Female performance across the boards that publish a gender
breakdown — 14 of 15 (FSD does not; see
data/availability.GENDER_AVAILABLE_BOARDS, the single source of truth
the board filter is built from). Data comes from data/recipes.py's
verified per-board extraction table (raw gazette counts).

Layout: year pills (2026 / 2025 / Both) + restricted board multiselect,
KPI row (Male Pass % / Female Pass % / Gender Gap / Best-Gap Board),
hero grouped-bar chart, diverging gap bar, per-board gap trend, stacked
appeared split, pass-rate scatter with 45° parity line, a donut-pair
grid, and a full comparison table.
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
from data.recipes import load_gender_table
from data.availability import GENDER_AVAILABLE_BOARDS
from charts.gender_charts import (
    gender_kpis,
    chart_hero_gender_pass_rate,
    chart_gender_gap,
    chart_gap_trend_by_board,
    chart_gender_appeared,
    chart_gender_scatter,
    chart_gender_donut_grid,
    gender_table,
)

st.set_page_config(page_title="Gender Analysis - " + APP_NAME, page_icon=PAGE_ICON, layout="wide")
inject_css()
render_sidebar()

render_topbar(
    active_page="Gender Analysis",
    subtitle="Male vs Female performance, for boards that report a gender breakdown.",
    stat_label="Boards with Gender Data",
    stat_value=str(len(GENDER_AVAILABLE_BOARDS)),
    stat_icon="wc",
)

# ---------------------------------------------------------------------------
# Year selector — 2026 / 2025 / Both. 'Both' shows paired panels/two
# bars in the year-specific charts and 2026-with-delta in the KPIs.
# ---------------------------------------------------------------------------
year_label = render_filter_bar(
    "Year",
    options=["2026", "2025", "Both"],
    default="2026",
    key="gender_year_filter",
)
year_label = year_label or "2026"
if year_label == "Both":
    years = [2026, 2025]
else:
    years = [int(year_label)]
primary_year, other_year = max(years), min(years)

# ---------------------------------------------------------------------------
# Board multiselect — options are ONLY the boards that publish a gender
# breakdown (never ALL_BOARDS). The ℹ️ note explains why the other board
# is missing instead of the user assuming it's a bug.
# ---------------------------------------------------------------------------
st.markdown('<div class="filter-bar"><span class="filter-bar-label">Boards</span></div>',
            unsafe_allow_html=True)
selected_boards = board_multiselect(
    "Boards",
    available_boards=GENDER_AVAILABLE_BOARDS,
    key="gender_board_filter",
    default_all=True,
)
data_availability_note("Gender", GENDER_AVAILABLE_BOARDS)

if not selected_boards:
    st.warning("Select at least one board to compare.")
    st.stop()

gender_df = load_gender_table()
gender_df = gender_df[gender_df["Board"].isin(selected_boards)]

kpis = gender_kpis(gender_df, primary_year, other_year)
if kpis["best_gap_board"] is None:
    st.info(f"No gender breakdown published for the selected boards in {primary_year}.")
    st.stop()

boards_n = kpis["boards"]
suffix = f"{boards_n} board{'s' if boards_n != 1 else ''}"

# ---------------------------------------------------------------------------
# KPI row (4 cards) — aggregate Pass % from RAW Passed/Appeared sums
# (never an average of board rates), Gender Gap = Female % − Male %.
# ---------------------------------------------------------------------------
male, female = kpis["male"], kpis["female"]
render_kpi_row([
    {
        "icon": "male",
        "value": f"{male['pct'] * 100:.1f}%",
        "label": f"Male Pass % ({primary_year})",
        "delta": f"{kpis['male_delta'] * 100:+.1f} pts vs {other_year}",
        "delta_positive": kpis["male_delta"] >= 0,
        "accent": "blue",
        "spark": [male["pct"] - kpis["male_delta"], male["pct"]],
    },
    {
        "icon": "female",
        "value": f"{female['pct'] * 100:.1f}%",
        "label": f"Female Pass % ({primary_year})",
        "delta": f"{kpis['female_delta'] * 100:+.1f} pts vs {other_year}",
        "delta_positive": kpis["female_delta"] >= 0,
        "accent": "gold",
        "spark": [female["pct"] - kpis["female_delta"], female["pct"]],
    },
    {
        "icon": "compare_arrows",
        "value": f"{kpis['gap'] * 100:+.1f} pp",
        "label": "Gender Gap (F − M)",
        "delta": f"{kpis['gap_delta'] * 100:+.1f} pts vs {other_year}",
        "delta_positive": kpis["gap_delta"] >= 0,
        "accent": "blue" if kpis["gap"] >= 0 else "red",
        "spark": [kpis["gap"] - kpis["gap_delta"], kpis["gap"]],
    },
    {
        "icon": "emoji_events",
        "value": str(kpis["best_gap_board"]["board"]),
        "label": "Best-Gap Board (F ahead)",
        "delta": f"{kpis['best_gap_board']['gap'] * 100:+.1f} pp gap",
        "delta_positive": kpis["best_gap_board"]["gap"] >= 0,
        "accent": "green",
    },
])

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
year_suffix = " & ".join(str(y) for y in years)

# ---- HERO: Male vs Female Pass % per board (full width) -------------------
with chart_card("Pass % by Board — Male vs Female", f"{year_suffix} · {suffix} · ordered by gap"):
    st.plotly_chart(chart_hero_gender_pass_rate(gender_df, years), width="stretch")

# ---- Row B: Gender Gap diverging bar + per-board gap trend ----------------
col1, col2 = st.columns(2)
with col1:
    with chart_card("Gender Gap (Female % − Male %)", f"{year_suffix} · {suffix} · green = F ahead"):
        st.plotly_chart(chart_gender_gap(gender_df, years), width="stretch")
with col2:
    with chart_card("Gap Trend by Board", "2025 → 2026 · dashed line = parity (M = F)"):
        st.plotly_chart(chart_gap_trend_by_board(gender_df), width="stretch")

# ---- Row C: Appeared split + Male vs Female scatter ------------------------
col3, col4 = st.columns(2)
with col3:
    with chart_card("Appeared Candidates by Board", f"{year_suffix} · Male + Female stacked · {suffix}"):
        st.plotly_chart(chart_gender_appeared(gender_df, years), width="stretch")
with col4:
    with chart_card("Male vs Female Pass %", f"{year_suffix} · above the 45° line = Female ahead"):
        st.plotly_chart(chart_gender_scatter(gender_df, years), width="stretch")

# ---- Donut-pair grid (full width) ------------------------------------------
with chart_card("Pass vs Fail — Donut Pairs per Board",
                f"{primary_year} · left donut = Male, right = Female · {suffix}"):
    st.plotly_chart(chart_gender_donut_grid(gender_df, primary_year), width="stretch")

# ---------------------------------------------------------------------------
# Full comparison table(s) — one per selected year. Swat (2026-only
# gazette) simply doesn't appear in the 2025 table — nothing invented.
# ---------------------------------------------------------------------------
table_years = years if len(years) > 1 else [primary_year]
for t_year in sorted(table_years, reverse=True):
    tdf = gender_table(gender_df, t_year)
    with chart_card("Full Comparison Table", f"{t_year} · {len(tdf)} board{'s' if len(tdf) != 1 else ''}"):
        st.dataframe(
            tdf,
            hide_index=True,
            column_config={
                "Board": st.column_config.TextColumn("Board", width="medium"),
                "M-Appeared": st.column_config.NumberColumn("M-Appeared", format="%,d"),
                "M-Passed": st.column_config.NumberColumn("M-Passed", format="%,d"),
                "M-Pass %": st.column_config.NumberColumn("M-Pass %", format="%.1f%%"),
                "F-Appeared": st.column_config.NumberColumn("F-Appeared", format="%,d"),
                "F-Passed": st.column_config.NumberColumn("F-Passed", format="%,d"),
                "F-Pass %": st.column_config.NumberColumn("F-Pass %", format="%.1f%%"),
                "Gap (pts)": st.column_config.NumberColumn("Gap (F − M, pts)", format="%+.1f%%"),
            },
        )

st.caption(
    "ℹ️ Data provenance: 14 of 15 boards publish a Male/Female split — all counts above are "
    "parsed from each board's own gazette sheet (raw Appeared/Passed). "
    "Data integrity: FSD publishes no gender breakdown (excluded). Bahawalpur 2026: 3,921 "
    "candidates are unclassified by gender in the source gazette — its gender rows cover "
    "101,680 of its 105,601 total. Mardan & Peshawar report 'Promoted' as pass. "
    "Swat has only a 2026 gazette, so it has no 2025 gender data."
)
