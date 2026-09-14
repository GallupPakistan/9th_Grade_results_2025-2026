"""
charts/subject_charts.py

Charts for pages/6_Subject_Wise.py.

8 charts for subject-wise analysis:
  1. Hero horizontal bar (top-N subjects, "show all" toggle)
  2. Heatmap (Subject x Board -> Pass%)
  3. Box plot (Pass% distribution by subject)
  4. Scatter (Appeared vs Pass%)
  5. Line trend (top-5 subjects, 2025->2026)
  6. Treemap (Board -> Subject hierarchy)
  7. Diverging bar (YoY change per subject)
  8. Ranking table (sortable)

Multi-board aware:
  - Hero bar/Scatter/Treemap/Box: multi-board supported
  - Line trend: always top-5 subjects overall (regardless of board count)
  - Heatmap: best for 3+ boards comparison

Normalization: subject names are pre-normalized in data/recipes.py
(case/hyphen/spacing only). Meaningful suffixes like "(NEW COURSE)" and
"(TECH)" are preserved to avoid accidentally merging different subjects.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from styles.theme import COLORS, BOARD_COLOR_SEQUENCE
from config.settings import ALL_BOARDS

SUBJECT_COLORS = COLORS["accent"]
_HIGHLIGHT = COLORS["gold"]


def _base_layout(fig: go.Figure, legend_title: str = "", height: int = 400) -> go.Figure:
    """Shared layout — identical to the other pages' _base_layout."""
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


# def chart_xxx(df) -> go.Figure:
#     fig = px.bar(df, x=..., y=..., color_discrete_sequence=BOARD_COLOR_SEQUENCE)
#     fig.update_layout(
#         plot_bgcolor="rgba(0,0,0,0)",
#         paper_bgcolor="rgba(0,0,0,0)",
#         font_color=COLORS["text_primary"],
#     )
#     return fig


# ---------------------------------------------------------------------------
# Chart 1: Hero horizontal bar (top-N subjects by Pass %)
# ---------------------------------------------------------------------------
def chart_subject_hero(subject_df: pd.DataFrame, year: int, top_n: int = 20) -> go.Figure:
    """Horizontal bar: top-N subjects by Pass % for the selected year.
    Multi-board: shows top-N across all selected boards."""
    d = subject_df[subject_df["Year"] == year].copy()
    n_boards = d["Board"].nunique()
    if d.empty:
        fig = go.Figure()
        fig.add_annotation(text=f"No subject data for {year}", showarrow=False)
        return fig
    d = d.sort_values("Pass %", ascending=True).tail(top_n)
    fig = px.bar(d, x="Pass %", y="Subject", color="Board",
                 orientation="h", text=d["Pass %"].map(lambda v: f"{v*100:.0f}%"),
                 color_discrete_sequence=BOARD_COLOR_SEQUENCE)
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_xaxes(tickformat=".0%", range=[0, 1.05])
    return _base_layout(fig, legend_title="Board", height=max(300, n_boards * 60))


# ---------------------------------------------------------------------------
# Chart 2: Heatmap (Subject x Board -> Pass%)
# ---------------------------------------------------------------------------
def chart_subject_heatmap(subject_df: pd.DataFrame, year: int, top_n: int = 20) -> go.Figure:
    """Heatmap: Subject x Board -> Pass %. Best for 3+ boards.
    Sorted by Appeared descending — tiny-cohort subjects naturally go to bottom."""
    d = subject_df[subject_df["Year"] == year][["Board", "Subject", "Pass %", "Appeared"]].copy()
    if d.empty:
        fig = go.Figure()
        fig.add_annotation(text=f"No subject data for {year}", showarrow=False)
        return fig
    pivot = d.pivot_table(index="Board", columns="Subject", values="Pass %", aggfunc="mean")
    n_boards = d["Board"].nunique()
    subj_appeared = d.groupby("Subject")["Appeared"].sum().sort_values(ascending=False)
    pivot = pivot[subj_appeared.head(top_n).index]
    fig = px.imshow(pivot, text_auto=".0%", aspect="auto",
                    color_continuous_scale="RdYlGn", range_color=[0.3, 1.0], width=max(600, d["Board"].nunique() * 100))
    fig.update_layout(height=max(300, n_boards * 60))
    return _base_layout(fig, height=max(300, n_boards * 60))


# ---------------------------------------------------------------------------
# Chart 3: Box plot (Pass% distribution by subject)
# ---------------------------------------------------------------------------
def chart_subject_box(subject_df: pd.DataFrame, year: int) -> go.Figure:
    """Box plot: Pass % distribution across boards for each subject.
    Shows which subjects are consistently high/low across boards."""
    d = subject_df[subject_df["Year"] == year][["Board", "Subject", "Pass %"]].copy()
    if d.empty:
        fig = go.Figure()
        fig.add_annotation(text=f"No subject data for {year}", showarrow=False)
        return fig
    # Only show subjects that appear in 2+ boards for meaningful boxes
    subj_counts = d.groupby("Subject")["Board"].nunique()
    common_subjs = subj_counts[subj_counts >= 2].index
    d = d[d["Subject"].isin(common_subjs)]
    if d.empty:
        fig = go.Figure()
        fig.add_annotation(text="No common subjects across boards", showarrow=False)
        return fig
    fig = px.box(d, x="Subject", y="Pass %", color="Subject",
                 points="all", color_discrete_sequence=BOARD_COLOR_SEQUENCE)
    fig.update_traces(jitter=0.3, pointpos=-1.6, marker=dict(size=5, opacity=0.7))
    fig.update_yaxes(tickformat=".0%")
    fig.update_xaxes(tickangle=-45)
    fig.update_layout(showlegend=False)
    return _base_layout(fig, height=480)


# ---------------------------------------------------------------------------
# Chart 4: Scatter (Appeared vs Pass%)
# ---------------------------------------------------------------------------
def chart_subject_scatter(subject_df: pd.DataFrame, year: int) -> go.Figure:
    """Scatter: Appeared (x) vs Pass % (y), colored by board.
    Reveals relationship between subject difficulty and popularity."""
    d = subject_df[subject_df["Year"] == year][["Board", "Subject", "Appeared", "Pass %"]].copy()
    if d.empty:
        fig = go.Figure()
        fig.add_annotation(text=f"No subject data for {year}", showarrow=False)
        return fig
    fig = px.scatter(d, x="Appeared", y="Pass %", color="Board",
                     size="Appeared", hover_data=["Subject"],
                     color_discrete_sequence=BOARD_COLOR_SEQUENCE)
    fig.update_yaxes(tickformat=".0%")
    fig.update_xaxes(tickformat=",")
    return _base_layout(fig, legend_title="Board")


# ---------------------------------------------------------------------------
# Chart 5: Line trend (top-5 subjects, 2025->2026)
# ---------------------------------------------------------------------------
def chart_subject_trend(subject_df: pd.DataFrame) -> go.Figure:
    """Line trend: top-5 subjects (by total Appeared) across 2025->2026.
    Always shows 5 lines regardless of board count."""
    d = subject_df.copy()
    if d.empty:
        fig = go.Figure()
        fig.add_annotation(text="No subject data", showarrow=False)
        return fig
    # Find top-5 subjects by total Appeared across all boards/years
    top5 = d.groupby("Subject")["Appeared"].sum().nlargest(5).index
    d = d[d["Subject"].isin(top5)]
    if d.empty:
        fig = go.Figure()
        fig.add_annotation(text="No trend data", showarrow=False)
        return fig
    # Aggregate per subject per year
    agg = d.groupby(["Subject", "Year"]).agg({"Appeared": "sum", "Passed": "sum"}).reset_index()
    agg["Pass %"] = agg["Passed"] / agg["Appeared"]
    fig = px.line(agg, x="Year", y="Pass %", color="Subject", markers=True,
                  color_discrete_sequence=BOARD_COLOR_SEQUENCE)
    fig.update_traces(line=dict(width=3), marker=dict(size=9))
    fig.update_yaxes(tickformat=".0%")
    return _base_layout(fig, legend_title="Subject")


# ---------------------------------------------------------------------------
# Chart 6: Treemap (Board -> Subject hierarchy)
# ---------------------------------------------------------------------------
def chart_subject_treemap(subject_df: pd.DataFrame, year: int) -> go.Figure:
    """Treemap: Board -> Subject hierarchy sized by Appeared.
    Shows subject popularity within and across boards."""
    d = subject_df[subject_df["Year"] == year][["Board", "Subject", "Appeared"]].copy()
    if d.empty:
        fig = go.Figure()
        fig.add_annotation(text=f"No subject data for {year}", showarrow=False)
        return fig
    fig = px.treemap(d, path=[px.Constant("All"), "Board", "Subject"],
                     values="Appeared", color="Appeared",
                     color_continuous_scale="Blues")
    fig.update_traces(texttemplate="%{label}<br>%{value:,}",
                      hovertemplate="%{label}<br>Appeared %{value:,}<extra></extra>")
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=460,
                      paper_bgcolor="rgba(0,0,0,0)", font_color=COLORS["text_on_light"])
    return fig


# ---------------------------------------------------------------------------
# Chart 7: Diverging bar (YoY change per subject)
# ---------------------------------------------------------------------------
def chart_subject_gap(subject_df: pd.DataFrame) -> go.Figure:
    """Diverging bar: YoY Pass % change (2026 - 2025) per subject.
    Green = improvement, Red = decline."""
    d = subject_df[["Board", "Subject", "Year", "Pass %"]].copy()
    if d.empty:
        fig = go.Figure()
        fig.add_annotation(text="No subject data", showarrow=False)
        return fig
    # Pivot to get 2025 and 2026 side by side
    pivot = d.pivot_table(index=["Board", "Subject"], columns="Year", values="Pass %").reset_index()
    pivot.columns = ["Board", "Subject", "Pct2025", "Pct2026"]
    pivot = pivot.dropna()
    if pivot.empty:
        fig = go.Figure()
        fig.add_annotation(text="No YoY comparison available", showarrow=False)
        return fig
    pivot["Change"] = pivot["Pct2026"] - pivot["Pct2025"]
    pivot = pivot.sort_values("Change", ascending=True).head(20)
    colors = [COLORS["positive"] if v >= 0 else COLORS["negative"] for v in pivot["Change"]]
    fig = go.Figure(go.Bar(x=pivot["Change"], y=pivot["Subject"], orientation="h",
                           marker_color=colors,
                           text=pivot["Change"].map(lambda v: f"{v*100:+.0f}pp"),
                           textposition="outside"))
    fig.update_xaxes(tickformat="+.0%")
    return _base_layout(fig, height=420)


# ---------------------------------------------------------------------------
# Chart 8: Ranking table (sortable)
# ---------------------------------------------------------------------------
def subject_table(subject_df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Display table for one year: Board | Subject | Appeared | Passed | Pass %.
    Pass % stored x100 for printf formatting."""
    d = subject_df[subject_df["Year"] == year].copy()
    if d.empty:
        return pd.DataFrame(columns=["Board", "Subject", "Appeared", "Passed", "Pass %"])
    return pd.DataFrame({
        "Board": d["Board"],
        "Subject": d["Subject"],
        "Appeared": d["Appeared"],
        "Passed": d["Passed"],
        "Pass %": (d["Pass %"] * 100).round(1),
    })


# ---------------------------------------------------------------------------
# KPI helpers
# ---------------------------------------------------------------------------
def subject_kpis(subject_df: pd.DataFrame, year: int, min_appeared: int = 50) -> dict:
    """KPI values for the subject page.

    Highest/Lowest Pass% only consider subjects with min_appeared (default 50)
    candidates to avoid tiny-cohort distortion. Smaller-cohort subjects remain
    visible in the heatmap and comparison table, just not in headline KPIs.
    """
    d = subject_df[subject_df["Year"] == year]
    if d.empty:
        return {"highest": None, "lowest": None, "popular": None, "avg": None, "min_appeared": min_appeared}
    d_meaningful = d[d["Appeared"] >= min_appeared]
    if d_meaningful.empty:
        return {"highest": None, "lowest": None, "popular": None, "avg": None, "min_appeared": min_appeared}
    highest = d_meaningful.loc[d_meaningful["Pass %"].idxmax()]
    lowest = d_meaningful.loc[d_meaningful["Pass %"].idxmin()]
    popular = d.loc[d["Appeared"].idxmax()]
    avg_pass = d_meaningful["Pass %"].mean()
    return {
        "highest": {"subject": highest["Subject"], "board": highest["Board"],
                    "pct": highest["Pass %"] * 100, "appeared": int(highest["Appeared"])},
        "lowest": {"subject": lowest["Subject"], "board": lowest["Board"],
                   "pct": lowest["Pass %"] * 100, "appeared": int(lowest["Appeared"])},
        "popular": {"subject": popular["Subject"], "board": popular["Board"],
                    "appeared": int(popular["Appeared"])},
        "avg": avg_pass * 100,
        "min_appeared": min_appeared,
    }