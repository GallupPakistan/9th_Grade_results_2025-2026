"""
pages/2_Board_Comparison.py

Side-by-side comparison of all 15 BISE boards: KPI row + six charts +
a full comparison table, all reactive to three filters —

  * Year pills (2026/2025) — drive the year-specific KPIs/charts
  * Province filter (pills, from PROVINCE_BOARD_MAP)
  * Board multiselect (separate from the province filter) — lets the
    user isolate 2+ specific boards for direct comparison; an empty
    selection means "all boards"

Data source: the "Overall Summary" sheet (Board x Year x Appeared x
Passed x Pass %age), loaded via data/loader.py. Aggregations always
sum raw Appeared/Passed counts. Swat has no 2025 gazette — its 2025
cells stay empty everywhere (skip, never fabricate).
"""

import streamlit as st
import pandas as pd
from config.settings import APP_NAME, PAGE_ICON, ALL_BOARDS
from styles.css import inject_css
from components.sidebar import render_sidebar
from components.topbar import render_topbar
from components.filter_bar import render_filter_bar
from components.kpi_card import render_kpi_row, format_compact
from components.chart_card import chart_card
from components.page_header import render_page_header
from data.loader import load_overall_summary
from data.availability import PROVINCE_BOARD_MAP
from charts.comparison_charts import (
    prepare_board_comparison,
    chart_pass_rate_comparison,
    chart_appeared_comparison,
    chart_yoy_pass_change,
    chart_board_ranking,
    chart_passed_vs_failed,
    chart_size_vs_performance,
)

st.set_page_config(page_title="Board Comparison - " + APP_NAME, page_icon=PAGE_ICON, layout="wide")
inject_css()
render_sidebar()

render_topbar(
    active_page="Board Comparison",
    subtitle="Compare Appeared, Passed and Pass % across all 15 boards, 2025 vs 2026.",
    stat_label="BISE Boards",
    stat_value="15",
    stat_icon="account_balance",
)

# ---------------------------------------------------------------------------
# Heading + Year selector — same minimal section as the Overview page.
# ---------------------------------------------------------------------------
selected_year = render_page_header(
    title="Select Year to View Results",
    year_options=[2026, 2025],
    year_default=2026,
    key="board_comparison_year_selector",
)
other_year = 2025 if selected_year == 2026 else 2026

# ---------------------------------------------------------------------------
# Filters — two independent widgets:
#   1. Province pills (same as Overview; "All Provinces" default)
#   2. Board multiselect (pills, multi) — separate from the province
#      filter, so the user can pick ANY 2+ boards for head-to-head
#      comparison. Empty selection = all boards. When both filters are
#      active, the intersection is shown.
# ---------------------------------------------------------------------------
ALL_PROVINCES_LABEL = "All Provinces"
province_options = [ALL_PROVINCES_LABEL] + list(PROVINCE_BOARD_MAP.keys())

selected_province = render_filter_bar(
    "Province",
    options=province_options,
    default=ALL_PROVINCES_LABEL,
    key="board_comparison_province_filter",
)
selected_province = selected_province or ALL_PROVINCES_LABEL

selected_boards = render_filter_bar(
    "Boards",
    options=ALL_BOARDS,
    default=None,
    multi=True,
    key="board_comparison_board_filter",
)
if not selected_boards:
    st.caption("Boards: nothing selected above = all 15 boards are shown. "
               "Pick any 2+ boards to isolate them for direct comparison.")

overall_df = load_overall_summary()

# Effective board list — both filters apply together (intersection).
allowed_boards = list(ALL_BOARDS)
if selected_province != ALL_PROVINCES_LABEL:
    allowed_boards = [b for b in allowed_boards if b in PROVINCE_BOARD_MAP[selected_province]]
if selected_boards:
    allowed_boards = [b for b in allowed_boards if b in selected_boards]

if not allowed_boards:
    st.warning(
        "The selected boards and province don't overlap — pick boards from "
        f"{selected_province} or set the province filter back to All Provinces."
    )
    st.stop()

filtered_df = overall_df[overall_df["Board"].isin(allowed_boards)]
comp = prepare_board_comparison(filtered_df)

# Human-readable description of the active filter, reused in chart subtitles.
filter_suffix = "all 15 boards"
if selected_province != ALL_PROVINCES_LABEL and selected_boards:
    filter_suffix = f"{selected_province} · {len(comp)} boards"
elif selected_province != ALL_PROVINCES_LABEL:
    filter_suffix = selected_province
elif selected_boards:
    filter_suffix = f"{len(comp)} boards · head-to-head"

# ---------------------------------------------------------------------------
# KPI row — 5 cards for the SELECTED year with YoY deltas vs the other
# year. All values aggregated from RAW counts of whichever boards the
# two filters selected (never an average of board rates). When year
# 2025 is selected, Swat is silently excluded — it has no 2025 gazette.
# ---------------------------------------------------------------------------
cur_appeared = int(pd.to_numeric(comp[f"Appeared {selected_year}"], errors="coerce").sum())
cur_passed = int(pd.to_numeric(comp[f"Passed {selected_year}"], errors="coerce").sum())
prv_appeared = int(pd.to_numeric(comp[f"Appeared {other_year}"], errors="coerce").sum())
prv_passed = int(pd.to_numeric(comp[f"Passed {other_year}"], errors="coerce").sum())
cur_pct = (cur_passed / cur_appeared) if cur_appeared else 0.0
prv_pct = (prv_passed / prv_appeared) if prv_appeared else 0.0

ranked = comp.dropna(subset=[f"Pass % {selected_year}"])
top = ranked.sort_values(f"Pass % {selected_year}", ascending=False).iloc[0]

render_kpi_row([
    {
        "icon": "groups",
        "value": format_compact(cur_appeared),
        "label": f"Total Appeared ({selected_year})",
        "delta": f"{format_compact(cur_appeared - prv_appeared)} vs {other_year}",
        "delta_positive": cur_appeared >= prv_appeared,
        "accent": "blue",
        "spark": [prv_appeared, cur_appeared],
    },
    {
        "icon": "verified",
        "value": format_compact(cur_passed),
        "label": f"Total Passed ({selected_year})",
        "delta": f"{format_compact(cur_passed - prv_passed)} vs {other_year}",
        "delta_positive": cur_passed >= prv_passed,
        "accent": "green",
        "spark": [prv_passed, cur_passed],
    },
    {
        "icon": "percent",
        "value": f"{cur_pct * 100:.1f}%",
        "label": f"Pass Rate ({selected_year})",
        "delta": f"{(cur_pct - prv_pct) * 100:+.1f} pts vs {other_year}",
        "delta_positive": cur_pct >= prv_pct,
        "accent": "gold",
        "spark": [prv_pct, cur_pct],
    },
    {
        "icon": "emoji_events",
        "value": str(top["Board"]),
        "label": f"Top Board ({selected_year})",
        "delta": f"{top[f'Pass % {selected_year}'] * 100:.1f}% pass",
        "delta_positive": True,
        "accent": "green",
    },
    {
        "icon": "account_balance",
        "value": str(len(comp)),
        "label": f"Boards Shown ({selected_year})",
        "delta": f"of {len(ALL_BOARDS)} total",
        "delta_positive": True,
        "accent": "blue",
    },
])

# ---------------------------------------------------------------------------
# Charts — every card reads the same filter-narrowed comp table, so the
# province filter AND the board multiselect apply across every chart.
# ---------------------------------------------------------------------------
# ---- Row A: Pass % by board (2025 vs 2026) + YoY change -------------------
colA, colB = st.columns([2, 1])
with colA:
    with chart_card("Pass % by Board", f"2025 vs 2026 · {filter_suffix}"):
        st.plotly_chart(chart_pass_rate_comparison(comp), width="stretch")
with colB:
    with chart_card("YoY Change in Pass %", "2026 vs 2025 · green = improved"):
        st.plotly_chart(chart_yoy_pass_change(comp), width="stretch")

# ---- Row B: Ranking (selected year) + Passed vs Failed (selected year) ----
col1, col2 = st.columns(2)
with col1:
    if ranked.empty:
        with chart_card("Board Ranking", f"{selected_year}"):
            st.info(f"No board in the current selection published a {selected_year} pass rate.")
    else:
        with chart_card("Board Ranking", f"Pass %, {selected_year} · best to worst · {filter_suffix}"):
            st.plotly_chart(chart_board_ranking(comp, selected_year), width="stretch")
with col2:
    if comp.dropna(subset=[f"Passed {selected_year}"]).empty:
        with chart_card("Passed vs Failed", f"{selected_year}"):
            st.info(f"No {selected_year} outcome counts available for the selected boards.")
    else:
        with chart_card("Passed vs Failed", f"{selected_year} · board size + outcome · {filter_suffix}"):
            st.plotly_chart(chart_passed_vs_failed(comp, selected_year), width="stretch")

# ---- Row C: Appeared (2025 vs 2026) + Size vs Performance -----------------
col3, col4 = st.columns(2)
with col3:
    with chart_card("Appeared Candidates by Board", f"2025 vs 2026 · {filter_suffix}"):
        st.plotly_chart(chart_appeared_comparison(comp), width="stretch")
with col4:
    with chart_card("Board Size vs Performance", f"{selected_year} · does scale help? · {filter_suffix}"):
        st.plotly_chart(chart_size_vs_performance(comp, selected_year), width="stretch")

# ---------------------------------------------------------------------------
# Full comparison table — one row per board, paired 2025/2026 columns.
# Swat's 2025 cells stay blank (no 2025 gazette — nothing is invented).
# NOTE: Streamlit's NumberColumn printf format does NOT scale fractions,
# so the display copy stores Pass % (and the change) ×100 and shows them
# with "%.1f%%" — the chart-side comp table keeps true fractions.
# ---------------------------------------------------------------------------
display = comp.copy()
for col in ("Pass % 2025", "Pass % 2026", "Pass % Change"):
    display[col] = display[col] * 100

with chart_card("Full Comparison Table", "All boards in the current selection · 2025 vs 2026"):
    st.dataframe(
        display,
        hide_index=True,
        column_config={
            "Board": st.column_config.TextColumn("Board", width="medium"),
            "Appeared 2025": st.column_config.NumberColumn("Appeared 2025", format="%,d"),
            "Appeared 2026": st.column_config.NumberColumn("Appeared 2026", format="%,d"),
            "Passed 2025": st.column_config.NumberColumn("Passed 2025", format="%,d"),
            "Passed 2026": st.column_config.NumberColumn("Passed 2026", format="%,d"),
            "Pass % 2025": st.column_config.NumberColumn("Pass % 2025", format="%.1f%%"),
            "Pass % 2026": st.column_config.NumberColumn("Pass % 2026", format="%.1f%%"),
            "Pass % Change": st.column_config.NumberColumn("Change vs 2025 (pts)", format="%+.1f%%"),
        },
    )

st.caption(
    "ℹ️ Data integrity notes: Swat has no 2025 gazette, so its 2025 cells are blank and it is "
    "excluded from every 2025-vs-2026 comparison — nothing is estimated. Pass rates for a "
    "selection are recomputed from raw Passed/Appeared sums (never an average of board rates). "
    "Mardan & Peshawar report 'Promoted' as pass in their source gazettes."
)
