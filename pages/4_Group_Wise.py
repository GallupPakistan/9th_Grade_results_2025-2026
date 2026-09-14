"""
pages/4_Group_Wise.py

Science vs Humanities performance across the boards that publish a
group split — all 15 of them (see data/availability.GROUP_AVAILABLE_BOARDS).
Data comes from data/recipes.py's verified per-board extraction table
(raw gazette counts), where "Arts" (Abbottabad, Peshawar) and "General"
(DGK's M/F sheet, FSD, Gujranwala, Kohat, Sahiwal) normalize to
"Humanities", and Rawalpindi's 2025 "Humanities (General)" is its 2026
"Humanities" (renamed).

Layout: year pills (2026 / 2025 / Both) + restricted board multiselect,
KPI row (Science Pass % / Humanities Pass % / Gap / Widest-Gap Board),
hero grouped-bar chart, diverging gap bar, slope trend, stacked appeared
split, pass-% box plot, and a Board -> Group treemap.
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
from data.recipes import load_group_table
from data.availability import GROUP_AVAILABLE_BOARDS
from charts.group_charts import (
    group_kpis,
    chart_hero_group_pass_rate,
    chart_group_gap,
    chart_group_slope,
    chart_group_appeared,
    chart_group_box,
    chart_group_treemap,
    group_table,
)

st.set_page_config(page_title="Group Wise - " + APP_NAME, page_icon=PAGE_ICON, layout="wide")
inject_css()
render_sidebar()

render_topbar(
    active_page="Group Wise",
    subtitle="Science vs Humanities performance, for boards that report a group split.",
    stat_label="BISE Boards",
    stat_value="15",
    stat_icon="account_balance",
)

# ---------------------------------------------------------------------------
# Year selector — 2026 / 2025 / Both, same as the Gender page.
# ---------------------------------------------------------------------------
year_label = render_filter_bar(
    "Year",
    options=["2026", "2025", "Both"],
    default="2026",
    key="group_year_filter",
)
year_label = year_label or "2026"
if year_label == "Both":
    years = [2026, 2025]
else:
    years = [int(year_label)]
primary_year, other_year = max(years), min(years)

# ---------------------------------------------------------------------------
# Board multiselect — options FROM GROUP_AVAILABLE_BOARDS (all 15 boards
# publish a group split; FSD, DGK's applied groups etc. are covered or
# excluded at the DATA layer, see data/recipes.py).
# ---------------------------------------------------------------------------
st.markdown('<div class="filter-bar"><span class="filter-bar-label">Boards</span></div>',
            unsafe_allow_html=True)
selected_boards = board_multiselect(
    "Boards",
    available_boards=GROUP_AVAILABLE_BOARDS,
    key="group_board_filter",
    default_all=True,
)
data_availability_note("Group", GROUP_AVAILABLE_BOARDS)

if not selected_boards:
    st.warning("Select at least one board to compare.")
    st.stop()

group_df = load_group_table()
group_df = group_df[group_df["Board"].isin(selected_boards)]

kpis = group_kpis(group_df, primary_year, other_year)
if kpis["widest_gap_board"] is None:
    st.info(f"No group breakdown published for the selected boards in {primary_year}.")
    st.stop()

boards_n = kpis["boards"]
suffix = f"{boards_n} board{'s' if boards_n != 1 else ''}"

# ---------------------------------------------------------------------------
# KPI row (4 cards) — aggregate Pass % from RAW Passed/Appeared sums
# (never an average of board rates); Gap = Science % − Humanities %.
# ---------------------------------------------------------------------------
sci, hum = kpis["science"], kpis["humanities"]
render_kpi_row([
    {
        "icon": "biotech",
        "value": f"{sci['pct'] * 100:.1f}%",
        "label": f"Science Pass % ({primary_year})",
        "delta": f"{kpis['science_delta'] * 100:+.1f} pts vs {other_year}",
        "delta_positive": kpis["science_delta"] >= 0,
        "accent": "blue",
        "spark": [sci["pct"] - kpis["science_delta"], sci["pct"]],
    },
    {
        "icon": "menu_book",
        "value": f"{hum['pct'] * 100:.1f}%",
        "label": f"Humanities Pass % ({primary_year})",
        "delta": f"{kpis['humanities_delta'] * 100:+.1f} pts vs {other_year}",
        "delta_positive": kpis["humanities_delta"] >= 0,
        "accent": "gold",
        "spark": [hum["pct"] - kpis["humanities_delta"], hum["pct"]],
    },
    {
        "icon": "compare_arrows",
        "value": f"{kpis['gap'] * 100:+.1f} pp",
        "label": "Gap (Science − Humanities)",
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
                 f"({'Science' if kpis['widest_gap_board']['gap'] >= 0 else 'Humanities'} ahead)",
        "delta_positive": kpis["widest_gap_board"]["gap"] >= 0,
        "accent": "green",
    },
])

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
year_suffix = " & ".join(str(y) for y in years)

# ---- HERO: Science vs Humanities Pass % per board (full width) ------------
with chart_card("Pass % by Board — Science vs Humanities", f"{year_suffix} · {suffix} · ordered by gap"):
    st.plotly_chart(chart_hero_group_pass_rate(group_df, years), width="stretch")

# ---- Row B: diverging gap bar + slope trend --------------------------------
col1, col2 = st.columns(2)
with col1:
    with chart_card("Gap (Science % − Humanities %)", f"{year_suffix} · {suffix} · green = Science ahead"):
        st.plotly_chart(chart_group_gap(group_df, years), width="stretch")
with col2:
    with chart_card("Pass % Slope 2025 → 2026", "Aggregate across the selected boards · raw sums"):
        st.plotly_chart(chart_group_slope(group_df), width="stretch")

# ---- Row C: appeared split + pass-% box plot -------------------------------
col3, col4 = st.columns(2)
with col3:
    with chart_card("Appeared Candidates by Board", f"{year_suffix} · Science + Humanities stacked · {suffix}"):
        st.plotly_chart(chart_group_appeared(group_df, years), width="stretch")
with col4:
    with chart_card("Pass % Distribution", f"{year_suffix} · each point = one board"):
        st.plotly_chart(chart_group_box(group_df, years), width="stretch")

# ---- Board -> Group treemap (full width) ------------------------------------
with chart_card("Board → Group Treemap", f"{primary_year} · box area = Appeared candidates · {suffix}"):
    st.plotly_chart(chart_group_treemap(group_df, primary_year), width="stretch")

# ---------------------------------------------------------------------------
# Full comparison table(s) — one per selected year. Swat (2026-only
# gazette) simply doesn't appear in the 2025 table — nothing invented.
# ---------------------------------------------------------------------------
table_years = years if len(years) > 1 else [primary_year]
for t_year in sorted(table_years, reverse=True):
    tdf = group_table(group_df, t_year)
    with chart_card("Full Comparison Table", f"{t_year} · {len(tdf)} board{'s' if len(tdf) != 1 else ''}"):
        st.dataframe(
            tdf,
            hide_index=True,
            column_config={
                "Board": st.column_config.TextColumn("Board", width="medium"),
                "S-Appeared": st.column_config.NumberColumn("Science Appeared", format="%,d"),
                "S-Passed": st.column_config.NumberColumn("Science Passed", format="%,d"),
                "S-Pass %": st.column_config.NumberColumn("Science Pass %", format="%.1f%%"),
                "H-Appeared": st.column_config.NumberColumn("Humanities Appeared", format="%,d"),
                "H-Passed": st.column_config.NumberColumn("Humanities Passed", format="%,d"),
                "H-Pass %": st.column_config.NumberColumn("Humanities Pass %", format="%.1f%%"),
                "Gap (pts)": st.column_config.NumberColumn("Gap (S − H, pts)", format="%+.1f%%"),
            },
        )

st.caption(
    "ℹ️ Data provenance: all 15 boards publish a Science/Humanities-style group split — counts "
    "are parsed from each board's own gazette sheets (raw Appeared/Passed). "
    "Label normalization: 'Arts' (Abbottabad, Peshawar) and 'General' (DGK's Male/Female table, "
    "FSD, Gujranwala, Kohat, Sahiwal) = Humanities; Rawalpindi's 2025 'Humanities (General)' is "
    "its 2026 'Humanities' (renamed in the gazette). "
    "Excluded non-core groups (so Science+Humanities can cover less than the board total, e.g. "
    "Rawalpindi 2026: 94.5%): Matric-Tech (Rawalpindi, Sahiwal, Sargodha), Tech (Gujranwala, "
    "Lahore), Deaf & Dumb (Gujranwala, Sahiwal, Sargodha), FSD's applied groups (Computer "
    "Science, Agriculture, Dars-e-Nazami, Fashion Designing, Deaf & Defective). "
    "Every Total / Sub Total / Grand Total rollup is excluded — including Kohat's "
    "'Grand Total (Science + General)'. "
    "DGK: its Science/General split covers 100% of its candidates (appeared & passed match the "
    "Overall Summary exactly for both years); its Regular/Private table uses a different, "
    "non-reconciling taxonomy and is not used here. "
    "Bahawalpur 2026: 3,921 candidates are unclassified by group in the gazette (group rows cover "
    "101,680 of its 105,601 total). "
    "Mardan & Peshawar report 'Promoted' as pass. "
    "Swat has only a 2026 gazette — no 2025 group data."
)
