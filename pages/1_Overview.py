"""
pages/1_Overview.py

Province-wide top-line view: KPI row (Appeared / Passed / Failed, 2026
with YoY delta) and a handful of charts, all reactive to a Province
filter. Data source: the "Overall Summary" sheet (Board x Year x
Appeared x Passed x Pass %age), loaded via data/loader.py.
"""

import streamlit as st
from config.settings import APP_NAME, PAGE_ICON, ALL_BOARDS
from styles.css import inject_css
from components.sidebar import render_sidebar
from components.topbar import render_topbar
from components.filter_bar import render_filter_bar
from components.kpi_card import render_kpi_row, format_compact
from components.chart_card import chart_card
from components.page_header import render_page_header
from components.provincial_tiles import render_province_tiles
from data.loader import load_overall_summary
from data.availability import PROVINCE_BOARD_MAP
from data.recipes import load_gender_table, load_category_table
from charts.overview_charts import (
    compute_province_totals,
    chart_yoy_totals,
    chart_board_pass_rate,
    chart_yoy_change_by_board,
    chart_appeared_share,
    chart_gender_pass_rate,
    chart_gender_share,
    chart_category_pass_rate,
    chart_category_share,
    chart_province_pass_trend,
    chart_pakistan_map,
    top_movers,
)
from components.top_boards import render_top_boards

st.set_page_config(page_title="Overview - " + APP_NAME, page_icon=PAGE_ICON, layout="wide")
inject_css()
render_sidebar()

render_topbar(
    active_page="Overview",
    subtitle="Province-wide 9th Class results, 2025 vs 2026, across all 15 BISE boards.",
    stat_label="BISE Boards",
    stat_value="15",
    stat_icon="account_balance",
)

# ---------------------------------------------------------------------------
# Heading + Year selector — directly under the topbar. The topbar already
# shows the page title, so this section is intentionally minimal: a bold
# heading telling the user which year to select, with the 2026/2025 pills
# on the right. The chosen year drives the KPI row below.
# ---------------------------------------------------------------------------
selected_year = render_page_header(
    title="Select Year to View Results",
    year_options=[2026, 2025],
    year_default=2026,
    key="overview_year_selector",
)
other_year = 2025 if selected_year == 2026 else 2026

# ---------------------------------------------------------------------------
# Province filter — only provinces that actually have a board in our
# 15-board dataset are offered (see data/availability.PROVINCE_BOARD_MAP),
# so selecting one can never produce an empty page. Default is "All
# Provinces" so the page opens on the full province-wide picture.
# ---------------------------------------------------------------------------
ALL_PROVINCES_LABEL = "All Provinces"
province_options = [ALL_PROVINCES_LABEL] + list(PROVINCE_BOARD_MAP.keys())

selected_province = render_filter_bar(
    "Province",
    options=province_options,
    default=ALL_PROVINCES_LABEL,
    key="overview_province_filter",
)
selected_province = selected_province or ALL_PROVINCES_LABEL

overall_df = load_overall_summary()

if selected_province == ALL_PROVINCES_LABEL:
    filtered_df = overall_df
else:
    boards_in_province = PROVINCE_BOARD_MAP[selected_province]
    filtered_df = overall_df[overall_df["Board"].isin(boards_in_province)]

# ---------------------------------------------------------------------------
# KPI row — 5 cards: Appeared / Passed / Failed / Pass Rate / Boards for
# the selected year, with YoY delta vs the other year and a mini
# sparkline (2025 vs 2026). Recomputed from whichever boards the
# province filter has selected.
# ---------------------------------------------------------------------------
totals = compute_province_totals(filtered_df)
cur, prv = totals[selected_year], totals[other_year]
cur_pct = (cur["passed"] / cur["appeared"]) if cur["appeared"] else 0.0
prv_pct = (prv["passed"] / prv["appeared"]) if prv["appeared"] else 0.0

render_kpi_row([
    {
        "icon": "groups",
        "value": format_compact(cur["appeared"]),
        "label": f"Total Appeared ({selected_year})",
        "delta": f"{format_compact(cur['appeared'] - prv['appeared'])} vs {other_year}",
        "delta_positive": cur["appeared"] >= prv["appeared"],
        "accent": "blue",
        "spark": [prv["appeared"], cur["appeared"]],
    },
    {
        "icon": "verified",
        "value": format_compact(cur["passed"]),
        "label": f"Total Passed ({selected_year})",
        "delta": f"{format_compact(cur['passed'] - prv['passed'])} vs {other_year}",
        "delta_positive": cur["passed"] >= prv["passed"],
        "accent": "green",
        "spark": [prv["passed"], cur["passed"]],
    },
    {
        "icon": "cancel",
        "value": format_compact(cur["failed"]),
        "label": f"Total Failed ({selected_year})",
        "delta": f"{format_compact(abs(cur['failed'] - prv['failed']))} vs {other_year}",
        "delta_positive": cur["failed"] <= prv["failed"],
        "accent": "red",
        "spark": [prv["failed"], cur["failed"]],
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
   
])

# ---------------------------------------------------------------------------
# Top Gainer / Top Decliner callout — straight from the Overall Summary's
# own 'Change (2026-2025)' rows (no recomputation), so the flagged boards
# are exactly the ones the workbook itself records as moving most.
# ---------------------------------------------------------------------------
gainer, decliner = top_movers(filtered_df)
if gainer is not None and decliner is not None:
    render_kpi_row([
        {
            "icon": "trending_up",
            "value": str(gainer["Board"]),
            "label": "Top Gainer · Pass % change",
            "delta": f"{gainer['Pass %age'] * 100:+.1f} pts vs 2025",
            "delta_positive": True,
            "accent": "green",
        },
        {
            "icon": "trending_down",
            "value": str(decliner["Board"]),
            "label": "Top Decliner · Pass % change",
            "delta": f"{decliner['Pass %age'] * 100:+.1f} pts vs 2025",
            "delta_positive": False,
            "accent": "red",
        },
    ])

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
subtitle_suffix = "all boards" if selected_province == ALL_PROVINCES_LABEL else selected_province

# ---- Row A: Overall Performance (2/3) + Pass % Trend (1/3) ---------------
colA, colB = st.columns([2, 1])
with colA:
    with chart_card("Overall Performance", f"{selected_year} vs {other_year}, {subtitle_suffix}"):
        st.plotly_chart(chart_yoy_totals(filtered_df), width="stretch")
with colB:
    with chart_card("Pass % Trend by Province", "2025 vs 2026, all boards"):
        st.plotly_chart(chart_province_pass_trend(overall_df), width="stretch")

# ---- Row B: Board-wise Pass % + YoY Change -------------------------------
col1, col2 = st.columns(2)
with col1:
    with chart_card("Board-wise Pass %", f"{selected_year}, {subtitle_suffix}"):
        st.plotly_chart(chart_board_pass_rate(filtered_df), width="stretch")
with col2:
    with chart_card("YoY Change in Pass %", f"2026 vs 2025, {subtitle_suffix}"):
        st.plotly_chart(chart_yoy_change_by_board(filtered_df), width="stretch")

# ---------------------------------------------------------------------------
# Province-level sections — these always use the FULL overall summary
# (all 15 boards grouped by province), regardless of the province
# filter, because a province map/trend only makes sense province-wide.
# ---------------------------------------------------------------------------
# ---- Row C: Pakistan Map + Top 5 Boards ---------------------------------
col5, col6 = st.columns([3, 2])
with col5:
    with chart_card("Pakistan Map", "Full Pakistan · hover for 2025 & 2026 details"):
        st.plotly_chart(chart_pakistan_map(overall_df), width="stretch")
with col6:
    with chart_card("Top 5 Boards", "By Pass %, 2026 & 2025, all boards"):
        render_top_boards(overall_df)

# ---- Row D: Provincial Comparison tiles (Appeared / Pass % toggle) -------
with chart_card("Provincial Comparison", f"{selected_year}, all boards"):
    prov_metric = st.pills(
        "Metric",
        options=["Appeared", "Pass %"],
        default="Appeared",
        key="overview_prov_metric",
        selection_mode="single",
        label_visibility="collapsed",
    )
    render_province_tiles(overall_df, prov_metric or "Appeared")

# ---- Row E: Share of Appeared Candidates --------------------------------
with chart_card("Share of Appeared Candidates", f"{selected_year}, {subtitle_suffix}"):
    st.plotly_chart(chart_appeared_share(filtered_df), width="stretch")

# ---------------------------------------------------------------------------
# Gender & Regular-vs-Private aggregates — from data/recipes.py's
# verified per-board extraction tables, narrowed to the same province
# filter as the rest of the page.
# ---------------------------------------------------------------------------
gender_df = load_gender_table()
category_df = load_category_table()
if selected_province != ALL_PROVINCES_LABEL:
    gender_df = gender_df[gender_df["Board"].isin(boards_in_province)]
    category_df = category_df[category_df["Board"].isin(boards_in_province)]

if gender_df.empty:
    st.info("No gender breakdown available for the selected boards.")
else:
    col5, col6 = st.columns(2)
    with col5:
        with chart_card("Gender-wise Pass %", f"2025 vs 2026, {subtitle_suffix}"):
            st.plotly_chart(chart_gender_pass_rate(gender_df), width="stretch")
    with col6:
        with chart_card("Gender Share of Appeared Candidates", f"2026, {subtitle_suffix}"):
            st.plotly_chart(chart_gender_share(gender_df), width="stretch")
    st.caption(
        "ℹ️ Data integrity notes: FSD publishes no gender breakdown (excluded). "
        "Mardan & Peshawar report 'Promoted' as pass. Bahawalpur 2026: 3,921 candidates "
        "are unclassified by gender in the source gazette and are not counted here."
    )

if category_df.empty:
    st.info("No Regular/Private breakdown available for the selected boards.")
else:
    col7, col8 = st.columns(2)
    with col7:
        with chart_card("Regular vs Private Pass %", f"2025 vs 2026, {subtitle_suffix}"):
            st.plotly_chart(chart_category_pass_rate(category_df), width="stretch")
    with col8:
        with chart_card("Regular vs Private Share of Appeared", f"2026, {subtitle_suffix}"):
            st.plotly_chart(chart_category_share(category_df), width="stretch")
