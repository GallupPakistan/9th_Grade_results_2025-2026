"""
pages/6_Subject_Wise.py

Subject-wise pass percentage analysis across 12 boards that publish
subject-wise tables. 8 charts + comparison table.

Data notes (see data/recipes.py load_subject_table for extraction logic):
- 12 of 15 boards publish subject-wise tables (Bannu, Mardan, Sahiwal do not)
- Subject names normalized (case/hyphen/spacing) but meaningful suffixes
  like "(NEW COURSE)" and "(TECH)" are PRESERVED to avoid accidentally
  merging different subjects (especially Bahawalpur's Old/New Course)
- NaN rows excluded (curriculum-gap subjects: Tech subjects 2026-only,
  Old Course subjects 2025-only for Bahawalpur)
- Pass % recomputed as Passed / Appeared (never taken from sheet directly)
"""

import streamlit as st
from config.settings import APP_NAME, PAGE_ICON
from styles.css import inject_css
from components.sidebar import render_sidebar
from components.topbar import render_topbar
from components.kpi_card import render_kpi_row
from components.chart_card import chart_card
from components.filter_bar import render_filter_row
from data.availability import SUBJECT_AVAILABLE_BOARDS
from data.recipes import load_subject_table
from charts.subject_charts import (
    chart_subject_hero,
    chart_subject_heatmap,
    chart_subject_box,
    chart_subject_scatter,
    chart_subject_trend,
    chart_subject_treemap,
    chart_subject_gap,
    subject_table,
    subject_kpis,
)

st.set_page_config(page_title="Subject Wise - " + APP_NAME, page_icon=PAGE_ICON, layout="wide")
inject_css()
render_sidebar()

render_topbar(
    active_page="Subject Wise",
    subtitle="Subject-level pass percentage, for boards that publish subject-wise tables.",
    stat_label="12 Boards with Subject Data",
)

st.markdown("ℹ️ 12 of 15 boards publish a subject-wise pass table — Bannu, Mardan, and Sahiwal do not.")

subject_df = load_subject_table()

filters = render_filter_row([
    {"label": "Year", "options": ["2026", "2025"], "default": "2026", "key": "subject_year"},
    {"label": "Boards", "options": SUBJECT_AVAILABLE_BOARDS, "default": SUBJECT_AVAILABLE_BOARDS,
     "key": "subject_boards", "multi": True},
])

primary_year = int(filters["subject_year"])
selected_boards = filters["subject_boards"]
df = subject_df[subject_df["Board"].isin(selected_boards)]
kpis = subject_kpis(df, primary_year)

if kpis["highest"] is None:
    st.info(f"No subject data for the selected boards in {primary_year}.")
    st.stop()

# KPI row (4 cards)
render_kpi_row([
    {
        "icon": "emoji_events",
        "value": f"{kpis['highest']['pct']:.1f}%",
        "label": f"Highest Pass % ({primary_year})",
        "delta": f"{kpis['highest']['subject']} ({kpis['highest']['board']}, {kpis['highest']['appeared']:,} candidates)",
        "delta_positive": True,
        "accent": "green",
    },
    {
        "icon": "trending_down",
        "value": f"{kpis['lowest']['pct']:.1f}%",
        "label": f"Lowest Pass % ({primary_year})",
        "delta": f"{kpis['lowest']['subject']} ({kpis['lowest']['board']}, {kpis['lowest']['appeared']:,} candidates)",
        "delta_positive": False,
        "accent": "red",
    },
    {
        "icon": "groups",
        "value": f"{kpis['popular']['appeared']:,}",
        "label": f"Most Popular Subject ({primary_year})",
        "delta": f"{kpis['popular']['subject']} ({kpis['popular']['board']})",
        "delta_positive": True,
        "accent": "blue",
    },
    {
        "icon": "bar_chart",
        "value": f"{kpis['avg']:.1f}%",
        "label": f"Average Pass % ({primary_year})",
        "delta": f"Across {df[df['Year']==primary_year]['Subject'].nunique()} subjects",
        "delta_positive": True,
        "accent": "gold",
    },
])

# Chart 1: Hero horizontal bar
with chart_card(f"Top Subjects by Pass % ({primary_year})",
                f"Top 20 of {df[df['Year']==primary_year]['Subject'].nunique()} subjects"):
    top_n = st.slider("Show top N", 5, 50, 20, key="subject_hero_n")
    st.plotly_chart(chart_subject_hero(df, primary_year, top_n=top_n), use_container_width=True)

# Chart 2: Heatmap (full width)
with chart_card(f"Subject x Board Heatmap ({primary_year})", "Green = higher Pass %, sorted by popularity"):
    heatmap_top_n = st.slider("Show top N subjects", 5, 50, 20, key="heatmap_top_n")
    st.plotly_chart(chart_subject_heatmap(df, primary_year, top_n=heatmap_top_n), use_container_width=True)

# Chart 3: Box plot (full width, below heatmap)
with chart_card(f"Pass % Distribution by Subject ({primary_year})", "Subjects in 2+ boards"):
    st.plotly_chart(chart_subject_box(df, primary_year), use_container_width=True)

# Chart 4: Scatter + Chart 5: Line trend (side by side)
col1, col2 = st.columns(2)
with col1:
    with chart_card(f"Appeared vs Pass % ({primary_year})", "Each point = one subject-board"):
        st.plotly_chart(chart_subject_scatter(df, primary_year), use_container_width=True)
with col2:
    with chart_card("Top-5 Subject Trend (2025-2026)", "Most popular subjects over time"):
        st.plotly_chart(chart_subject_trend(df), use_container_width=True)

# Chart 6: Treemap
with chart_card(f"Board -> Subject Hierarchy ({primary_year})", "Area = Appeared candidates"):
    st.plotly_chart(chart_subject_treemap(df, primary_year), use_container_width=True)

# Chart 7: Diverging bar (YoY change)
with chart_card("Year-over-Year Change by Subject (2025-2026)",
                "Green = improvement, Red = decline"):
    st.plotly_chart(chart_subject_gap(df), use_container_width=True)

# Comparison table
with chart_card(f"Full Subject Table ({primary_year})",
                f"{len(df[df['Year']==primary_year])} subject-board combinations"):
    tdf = subject_table(df, primary_year)
    st.dataframe(
        tdf,
        hide_index=True,
        column_config={
            "Board": st.column_config.TextColumn("Board", width="medium"),
            "Subject": st.column_config.TextColumn("Subject", width="large"),
            "Appeared": st.column_config.NumberColumn("Appeared", format="%,d"),
            "Passed": st.column_config.NumberColumn("Passed", format="%,d"),
            "Pass %": st.column_config.NumberColumn("Pass %", format="%.1f%%"),
        },
    )

st.caption(
    " Data provenance: all 12 boards subject-wise tables are parsed from each board own gazette "
    "(raw Appeared/Passed counts). Subject names are normalized (case/hyphen/spacing) but meaningful suffixes "
    "like (NEW COURSE) and (TECH) are PRESERVED to avoid accidentally merging different subjects. "
    "Bahawalpur: Old Course (2025) and New Course (2026) subjects are kept separate. "
    "DGK and FSD: Tech-stream subjects only exist in 2026 gazette (new curriculum). "
    "Gujranwala: only 2025 subject-wise data published. "
    "Pass % is recomputed as Passed / Appeared. "
    "Note: individual subject Appeared counts may exceed board totals because one candidate takes "
    "multiple subjects, and compulsory subjects include retake candidates."
    "Headline KPI cards show subjects with 50+ candidates only (avoids tiny-cohort "
    "distortion). Subjects with fewer candidates remain visible in the heatmap "
    "and comparison table. Same subject name may appear across different boards "
    "with different results (e.g., Clothing And Textile-I in Bahawalpur vs FBISE)."""
)
