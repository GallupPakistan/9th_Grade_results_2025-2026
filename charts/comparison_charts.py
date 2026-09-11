"""
charts/comparison_charts.py

Charts for pages/2_Board_Comparison.py.

All functions take the "Overall Summary" DataFrame (Board x Year x
Appeared x Passed x Pass %age, loaded via data/loader.py — already
narrowed to the selected province / board-multiselect by the page)
plus, where a year matters, the selected year. The shared
prepare_board_comparison() pivot turns the 3-rows-per-board layout
(2025 / 2026 / Change) into ONE row per board with paired 2025-vs-2026
columns so every chart works from the same comparison table.

Data-integrity rules encoded here:
  * Aggregations always sum RAW Appeared/Passed counts — board pass
    rates are never averaged.
  * Swat has no 2025 gazette, so its 2025 cells are None/NaN. Every
    chart tolerates that (skip, never fabricate).
  * Board colors come from ALL_BOARDS order (styles.theme's stable
    BOARD_COLOR_SEQUENCE), so the same board renders in the same color
    no matter which province/board filter is active.

Conventions match charts/overview_charts.py (_base_layout, trend year
colors) so the two pages look identical.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from config.settings import ALL_BOARDS
from styles.theme import COLORS, BOARD_COLOR_SEQUENCE
from data.availability import PROVINCE_BOARD_MAP


# ---------------------------------------------------------------------------
# Shared pivot — one row per board with paired 2025 / 2026 columns
# ---------------------------------------------------------------------------
def prepare_board_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Turns the 3-rows-per-board Overall Summary layout into one row
    per board: Appeared/Passed/Pass% for 2025 and 2026, plus the change
    in Pass % (percentage points, recomputed from the paired rates —
    never averaged). Boards are ordered by 2026 Pass % (best first).
    Swat's 2025 cells stay None where the gazette is missing."""
    rows = df[df["Year"].isin([2025, 2026])].copy()
    recs = []
    for board, sub in rows.groupby("Board"):
        rec = {"Board": board}
        for year in (2025, 2026):
            y = sub[sub["Year"] == year]
            if y.empty:
                rec[f"Appeared {year}"] = None
                rec[f"Passed {year}"] = None
                rec[f"Pass % {year}"] = None
            else:
                r = y.iloc[0]
                appeared = pd.to_numeric(r["Appeared"], errors="coerce")
                passed = pd.to_numeric(r["Passed"], errors="coerce")
                pct = pd.to_numeric(r["Pass %age"], errors="coerce")
                if pd.isna(appeared) or pd.isna(passed) or pd.isna(pct):
                    # e.g. Swat's 2025 row exists but is blank (no gazette)
                    rec[f"Appeared {year}"] = None
                    rec[f"Passed {year}"] = None
                    rec[f"Pass % {year}"] = None
                else:
                    rec[f"Appeared {year}"] = int(appeared)
                    rec[f"Passed {year}"] = int(passed)
                    rec[f"Pass % {year}"] = float(pct)
        p25, p26 = rec["Pass % 2025"], rec["Pass % 2026"]
        rec["Pass % Change"] = (p26 - p25) if (p25 is not None and p26 is not None) else None
        recs.append(rec)
    comp = pd.DataFrame(recs)
    return comp.sort_values("Pass % 2026", ascending=False).reset_index(drop=True)


def _province_of(board) -> str:
    """Reverse lookup: which province does this board belong to."""
    for province, boards in PROVINCE_BOARD_MAP.items():
        if board in boards:
            return province
    return "Other"


# Stable board -> color map keyed on ALL_BOARDS order, so a board keeps
# its color regardless of any active filter.
_BOARD_COLOR_MAP = {b: BOARD_COLOR_SEQUENCE[i % len(BOARD_COLOR_SEQUENCE)]
                    for i, b in enumerate(ALL_BOARDS)}


def _base_layout(fig: go.Figure, legend_title: str = "", height: int = 400) -> go.Figure:
    """Shared layout — identical to overview_charts._base_layout so the
    two pages' charts sit at the same visual weight."""
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color=COLORS["text_on_light"],
        font_size=12,
        legend_title_text=legend_title,
        margin=dict(t=10, b=10, l=10, r=10),
        height=height,
        uniformtext_minsize=10,
        uniformtext_mode="hide",
        bargap=0.35,
    )
    fig.update_xaxes(gridcolor="rgba(20,27,60,0.08)")
    fig.update_yaxes(gridcolor="rgba(20,27,60,0.08)")
    return fig


_YEAR_COLORS = {"2025": COLORS["trend_2025"], "2026": COLORS["trend_2026"]}


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def chart_pass_rate_comparison(comp: pd.DataFrame) -> go.Figure:
    """Grouped vertical bar: Pass % per board, 2025 vs 2026 side by side,
    boards ordered best-to-worst by 2026. Swat shows only its 2026 bar."""
    d = comp[["Board", "Pass % 2025", "Pass % 2026"]].melt(
        id_vars="Board", var_name="Year", value_name="Pass %"
    )
    d = d.dropna(subset=["Pass %"])
    d["Year"] = d["Year"].str.replace("Pass % ", "", regex=False)

    fig = px.bar(
        d, x="Board", y="Pass %", color="Year", barmode="group",
        color_discrete_map=_YEAR_COLORS, text_auto=".1%",
        category_orders={"Board": list(comp["Board"])},
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_yaxes(tickformat=".0%", range=[0, 1])
    fig.update_xaxes(tickangle=-45)
    return _base_layout(fig, legend_title="Year")


def chart_appeared_comparison(comp: pd.DataFrame) -> go.Figure:
    """Grouped vertical bar: Appeared candidates per board, 2025 vs 2026,
    same board order as the Pass % chart so the two read together."""
    d = comp[["Board", "Appeared 2025", "Appeared 2026"]].melt(
        id_vars="Board", var_name="Year", value_name="Appeared"
    )
    d = d.dropna(subset=["Appeared"])
    d["Year"] = d["Year"].str.replace("Appeared ", "", regex=False)

    fig = px.bar(
        d, x="Board", y="Appeared", color="Year", barmode="group",
        color_discrete_map=_YEAR_COLORS,
        category_orders={"Board": list(comp["Board"])},
    )
    fig.update_yaxes(tickformat=".2s")
    fig.update_xaxes(tickangle=-45)
    return _base_layout(fig, legend_title="Year")


def chart_yoy_pass_change(comp: pd.DataFrame) -> go.Figure:
    """Diverging horizontal bar: change in Pass % (2026 vs 2025) per
    board, green for gainers / red for decliners. Swat (no 2025) is
    excluded — the chart omits it rather than guessing."""
    d = comp.dropna(subset=["Pass % Change"]).sort_values("Pass % Change")
    colors = [COLORS["positive"] if v >= 0 else COLORS["negative"] for v in d["Pass % Change"]]

    fig = go.Figure(go.Bar(
        x=d["Pass % Change"], y=d["Board"], orientation="h",
        marker_color=colors,
        text=d["Pass % Change"].map(lambda v: f"{v*100:+.1f} pp"),
        textposition="outside",
        cliponaxis=False,
        customdata=d["Board"].map(_province_of),
        hovertemplate="%{y} (%{customdata})<br>%{x*100:+.1f} pp<extra></extra>",
    ))
    fig.update_xaxes(tickformat=".0%")
    return _base_layout(fig)


def chart_board_ranking(comp: pd.DataFrame, year: int) -> go.Figure:
    """Horizontal bar: boards ranked by Pass % for the SELECTED year,
    best at top, stable per-board colors. Boards without that year
    (Swat 2025) drop out — the page shows a caption in that case."""
    d = comp.dropna(subset=[f"Pass % {year}"]).sort_values(f"Pass % {year}", ascending=True)

    fig = go.Figure(go.Bar(
        x=d[f"Pass % {year}"], y=d["Board"], orientation="h",
        marker_color=[_BOARD_COLOR_MAP[b] for b in d["Board"]],
        text=d[f"Pass % {year}"].map(lambda v: f"{v*100:.1f}%"),
        textposition="outside",
        cliponaxis=False,
        customdata=d["Board"].map(_province_of),
        hovertemplate="%{y} (%{customdata})<br>Pass %{x:.1%}<extra></extra>",
    ))
    fig.update_xaxes(tickformat=".0%", range=[0, 1])
    fig.update_layout(showlegend=False)
    return _base_layout(fig, height=max(400, 26 * len(d) + 60))


def chart_passed_vs_failed(comp: pd.DataFrame, year: int) -> go.Figure:
    """Stacked horizontal bar: Passed (green) vs Failed (red) per board
    for the selected year — shows board scale AND outcome in one view."""
    d = comp.dropna(subset=[f"Passed {year}"]).copy()
    d["Failed"] = d[f"Appeared {year}"] - d[f"Passed {year}"]
    d = d.sort_values(f"Appeared {year}", ascending=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=d["Board"], x=d[f"Passed {year}"], name="Passed", orientation="h",
        marker_color=COLORS["positive"],
        hovertemplate="%{y}<br>Passed %{x:,}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=d["Board"], x=d["Failed"], name="Failed", orientation="h",
        marker_color=COLORS["negative"],
        hovertemplate="%{y}<br>Failed %{x:,}<extra></extra>",
    ))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(tickformat=".2s")
    return _base_layout(fig, legend_title="Outcome", height=max(400, 26 * len(d) + 60))


def chart_size_vs_performance(comp: pd.DataFrame, year: int) -> go.Figure:
    """Scatter: x = Appeared (board size), y = Pass %, one labelled point
    per board for the selected year, colored by province. Answers 'do the
    biggest boards perform better?' at a glance."""
    d = comp.dropna(subset=[f"Pass % {year}"]).copy()
    d["Province"] = d["Board"].map(_province_of)

    fig = px.scatter(
        d, x=f"Appeared {year}", y=f"Pass % {year}", color="Province",
        hover_name="Board", text="Board",
        color_discrete_sequence=BOARD_COLOR_SEQUENCE,
    )
    fig.update_traces(textposition="top center", textfont_size=9, cliponaxis=False)
    fig.update_yaxes(tickformat=".0%")
    fig.update_xaxes(tickformat=".2s")
    return _base_layout(fig, legend_title="Province")
