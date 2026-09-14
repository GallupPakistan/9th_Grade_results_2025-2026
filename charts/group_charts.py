"""
charts/group_charts.py

Charts for pages/4_Group_Wise.py.

All functions take the normalized group table from data/recipes.py
(Board x Year x Group x Appeared x Passed x Pass %, Group always
"Science"/"Humanities" — already narrowed to the selected boards by the
page) plus, where a year matters, the selected year(s). All 15 boards
publish a group split; Swat has only a 2026 gazette, so it is absent
from every 2025 view — skip, never fabricate. Gap convention (deliberate,
page-subject-first): Gap = Science % − Humanities %.

Conventions match charts/overview_charts.py / gender_charts.py
(_base_layout; Science=blue / Humanities=gold like the other
this-vs-that charts).
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from styles.theme import COLORS, BOARD_COLOR_SEQUENCE
from config.settings import ALL_BOARDS

GROUP_COLORS = {"Science": COLORS["accent"], "Humanities": COLORS["gold"]}

_YEAR_COLORS = {"2025": COLORS["trend_2025"], "2026": COLORS["trend_2026"]}

_BOARD_COLOR_MAP = {b: BOARD_COLOR_SEQUENCE[i % len(BOARD_COLOR_SEQUENCE)]
                    for i, b in enumerate(ALL_BOARDS)}


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


# ---------------------------------------------------------------------------
# Shared pivot — one row per board with paired Science / Humanities columns
# ---------------------------------------------------------------------------
def prepare_group_comparison(group_df: pd.DataFrame, year: int) -> pd.DataFrame:
    """One row per board for the given year: Appeared/Passed/Pass % for
    Science and Humanities, plus the Gap (Science % − Humanities %,
    stored as a fraction). Boards missing a group row for that year are
    dropped — Swat in 2025 (no 2025 gazette) is the real-world case.
    Sorted by Gap, widest Science advantage first."""
    rows = group_df[group_df["Year"] == year]
    recs = []
    for board, sub in rows.groupby("Board"):
        rec = {"Board": board}
        ok = True
        for group in ("Science", "Humanities"):
            g = sub[sub["Group"] == group]
            if g.empty:
                ok = False
                break
            r = g.iloc[0]
            appeared = pd.to_numeric(r["Appeared"], errors="coerce")
            passed = pd.to_numeric(r["Passed"], errors="coerce")
            if pd.isna(appeared) or pd.isna(passed):
                ok = False
                break
            rec[f"Appeared {group}"] = int(appeared)
            rec[f"Passed {group}"] = int(passed)
            rec[f"Pass % {group}"] = float(passed / appeared) if appeared else None
        if ok:
            rec["Gap"] = rec["Pass % Science"] - rec["Pass % Humanities"]
            rec["Appeared Total"] = rec["Appeared Science"] + rec["Appeared Humanities"]
            recs.append(rec)
    piv = pd.DataFrame(recs)
    if piv.empty:
        return pd.DataFrame(columns=[
            "Board", "Appeared Science", "Passed Science", "Pass % Science",
            "Appeared Humanities", "Passed Humanities", "Pass % Humanities",
            "Gap", "Appeared Total",
        ])
    return piv.sort_values("Gap", ascending=False).reset_index(drop=True)


def group_kpis(group_df: pd.DataFrame, primary_year: int, other_year: int) -> dict:
    """KPI values aggregated from RAW counts (never an average of board
    rates) for the primary year, with the other year as delta baseline."""
    def _year_agg(year: int) -> dict:
        out = {}
        for group in ("Science", "Humanities"):
            g = group_df[(group_df["Year"] == year) & (group_df["Group"] == group)]
            appeared = pd.to_numeric(g["Appeared"], errors="coerce").sum()
            passed = pd.to_numeric(g["Passed"], errors="coerce").sum()
            out[group] = {"appeared": int(appeared), "passed": int(passed),
                          "pct": (passed / appeared) if appeared else 0.0}
        out["gap"] = out["Science"]["pct"] - out["Humanities"]["pct"]
        return out

    cur, prv = _year_agg(primary_year), _year_agg(other_year)
    piv = prepare_group_comparison(group_df, primary_year)
    widest = None
    if not piv.empty:
        w = piv.loc[piv["Gap"].abs().idxmax()]
        widest = {"board": w["Board"], "gap": float(w["Gap"])}
    return {
        "science": cur["Science"],
        "humanities": cur["Humanities"],
        "gap": cur["gap"],
        "gap_delta": cur["gap"] - prv["gap"],
        "science_delta": cur["Science"]["pct"] - prv["Science"]["pct"],
        "humanities_delta": cur["Humanities"]["pct"] - prv["Humanities"]["pct"],
        "widest_gap_board": widest,
        "boards": int(group_df[group_df["Year"] == primary_year]["Board"].nunique()),
    }


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def chart_hero_group_pass_rate(group_df: pd.DataFrame, years: list[int]) -> go.Figure:
    """HERO — vertical grouped bar: Science vs Humanities Pass % per
    board. One year = single panel; 'Both' = two panels (2025 | 2026).
    Boards ordered by the primary year's Gap (widest Science advantage
    first) so both panels read together."""
    primary = max(years)
    piv = prepare_group_comparison(group_df, primary)
    board_order = list(piv["Board"])

    d = group_df[group_df["Year"].isin(years)][["Board", "Year", "Group", "Pass %"]].copy()
    d["Pass %"] = pd.to_numeric(d["Pass %"], errors="coerce")
    d = d.dropna(subset=["Pass %"])
    d["Year"] = d["Year"].astype(str)

    facet = len(years) > 1
    fig = px.bar(
        d, x="Board", y="Pass %", color="Group", barmode="group",
        color_discrete_map=GROUP_COLORS, text_auto=".1%",
        category_orders={"Board": board_order},
        facet_col="Year" if facet else None,
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_yaxes(tickformat=".0%", range=[0, 1], matches=None)
    fig.update_xaxes(tickangle=-45)
    if facet:
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    return _base_layout(fig, legend_title="Group", height=460)


def chart_group_gap(group_df: pd.DataFrame, years: list[int]) -> go.Figure:
    """Diverging horizontal bar: Gap (Science % − Humanities %) per
    board. Single year = one bar per board (green = Science ahead, red =
    Humanities ahead). 'Both' = two year-colored bars per board so the
    gap's drift is visible."""
    if len(years) == 1:
        piv = prepare_group_comparison(group_df, years[0]).sort_values("Gap")
        colors = [COLORS["positive"] if v >= 0 else COLORS["negative"] for v in piv["Gap"]]
        fig = go.Figure(go.Bar(
            x=piv["Gap"], y=piv["Board"], orientation="h",
            marker_color=colors,
            text=piv["Gap"].map(lambda v: f"{v*100:+.1f} pp"),
            textposition="outside", cliponaxis=False,
        ))
    else:
        recs = []
        for year in years:
            p = prepare_group_comparison(group_df, year)
            for _, r in p.iterrows():
                recs.append({"Board": r["Board"], "Year": str(year), "Gap": r["Gap"]})
        d = pd.DataFrame(recs)
        order = list(prepare_group_comparison(group_df, max(years))["Board"])
        fig = px.bar(
            d, x="Gap", y="Board", color="Year", orientation="h", barmode="group",
            color_discrete_map=_YEAR_COLORS, category_orders={"Board": order},
        )
        fig.update_traces(texttemplate="%{x*100:+.1f} pp",
                          textposition="outside", cliponaxis=False)
    fig.update_xaxes(tickformat=".0%")
    return _base_layout(fig, legend_title="Year" if len(years) > 1 else "", height=460)


def chart_group_slope(group_df: pd.DataFrame) -> go.Figure:
    """Slope chart: aggregate Science vs Humanities Pass %, 2025 → 2026
    (aggregate = raw Passed/Appeared sums across the selected boards,
    never an average of board rates). Two lines with value labels —
    parallel slopes = the gap held; converging/diverging = it moved."""
    recs = []
    for year in (2025, 2026):
        sub = group_df[group_df["Year"] == year]
        for group in ("Science", "Humanities"):
            g = sub[sub["Group"] == group]
            appeared = pd.to_numeric(g["Appeared"], errors="coerce").sum()
            passed = pd.to_numeric(g["Passed"], errors="coerce").sum()
            if appeared:
                recs.append({"Year": year, "Group": group, "Pass %": passed / appeared})
    d = pd.DataFrame(recs)
    d["Year"] = d["Year"].astype(str)

    fig = px.line(
        d, x="Year", y="Pass %", color="Group", markers=True,
        color_discrete_map=GROUP_COLORS, text=d["Pass %"].map(lambda v: f"{v*100:.1f}%"),
        category_orders={"Year": ["2025", "2026"]},
    )
    fig.update_traces(textposition="top center", cliponaxis=False,
                      line=dict(width=3), marker=dict(size=9))
    fig.update_yaxes(tickformat=".0%", range=[0, 1])
    return _base_layout(fig, legend_title="Group")


def chart_group_appeared(group_df: pd.DataFrame, years: list[int]) -> go.Figure:
    """Stacked vertical bar: Appeared candidates per board split into
    Science (bottom) vs Humanities (top), for the selected year(s).
    'Both' = two panels via facets. Volume context behind the rates."""
    primary = max(years)
    piv = prepare_group_comparison(group_df, primary)
    board_order = list(piv.sort_values("Appeared Total", ascending=False)["Board"])

    d = group_df[group_df["Year"].isin(years)][["Board", "Year", "Group", "Appeared"]].copy()
    d["Appeared"] = pd.to_numeric(d["Appeared"], errors="coerce")
    d = d.dropna(subset=["Appeared"])
    d["Year"] = d["Year"].astype(str)

    facet = len(years) > 1
    fig = px.bar(
        d, x="Board", y="Appeared", color="Group", barmode="stack",
        color_discrete_map=GROUP_COLORS,
        category_orders={"Board": board_order},
        facet_col="Year" if facet else None,
    )
    fig.update_traces(texttemplate="%{y:,}", textposition="inside",
                      insidetextanchor="middle", cliponaxis=False)
    fig.update_yaxes(tickformat=".2s")
    fig.update_xaxes(tickangle=-45)
    if facet:
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    return _base_layout(fig, legend_title="Group", height=460)


def chart_group_box(group_df: pd.DataFrame, years: list[int]) -> go.Figure:
    """Box plot: the distribution of board-level Pass % within each
    group (each point = one board). Science vs Humanities side by side;
    'Both' splits the boxes by year. Shows whether one group is not just
    ahead on average but consistently ahead across boards."""
    d = group_df[group_df["Year"].isin(years)][["Board", "Year", "Group", "Pass %"]].copy()
    d["Pass %"] = pd.to_numeric(d["Pass %"], errors="coerce")
    d = d.dropna(subset=["Pass %"])
    d["Year"] = d["Year"].astype(str)
    d["Series"] = d["Group"] + " · " + d["Year"] if len(years) > 1 else d["Group"]
    series_order = ([f"{g} · {y}" for y in sorted(years, reverse=True) for g in ("Science", "Humanities")]
                    if len(years) > 1 else ["Science", "Humanities"])
    color_map = (GROUP_COLORS if len(years) == 1 else
                 {f"{g} · {y}": GROUP_COLORS[g] for y in years for g in ("Science", "Humanities")})

    fig = px.box(
        d, x="Series", y="Pass %", color="Series", points="all",
        category_orders={"Series": series_order}, color_discrete_map=color_map,
    )
    fig.update_traces(jitter=0.25, pointpos=-1.6,
                      marker=dict(size=6, opacity=0.8))
    for tr in fig.data:
        boards = d[d["Series"] == tr.name]["Board"]
        tr.customdata = boards
        tr.hovertemplate = "%{customdata}<br>Pass %{y:.1%}<extra></extra>"
    fig.update_yaxes(tickformat=".0%")
    fig.update_layout(showlegend=False)
    return _base_layout(fig, height=460)


def chart_group_treemap(group_df: pd.DataFrame, year: int) -> go.Figure:
    """Treemap: Board -> Group hierarchy sized by Appeared candidates for
    the selected year (every box's area = its share of candidates). The
    single place where scale AND structure are visible at once."""
    rows = group_df[group_df["Year"] == year]
    if rows.empty:
        fig = go.Figure()
        fig.add_annotation(text=f"No group data for {year}", showarrow=False)
        return fig
    fig = px.treemap(
        rows, path=[px.Constant("All boards"), "Board", "Group"],
        values="Appeared", color="Group", color_discrete_map=GROUP_COLORS,
    )
    fig.update_traces(
        texttemplate="%{label}<br>%{value:,}",
        hovertemplate="%{label}<br>Appeared %{value:,}<extra></extra>",
    )
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=460,
                      paper_bgcolor="rgba(0,0,0,0)", font_color=COLORS["text_on_light"])
    return fig


def group_table(group_df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Display table for one year: Board | S-Appeared/Passed/Pass % |
    H-Appeared/Passed/Pass % | Gap. Pass % and Gap are stored ×100
    (percentage points) because Streamlit's NumberColumn printf format
    does not scale fractions."""
    piv = prepare_group_comparison(group_df, year)
    return pd.DataFrame({
        "Board": piv["Board"],
        "S-Appeared": piv["Appeared Science"],
        "S-Passed": piv["Passed Science"],
        "S-Pass %": piv["Pass % Science"] * 100,
        "H-Appeared": piv["Appeared Humanities"],
        "H-Passed": piv["Passed Humanities"],
        "H-Pass %": piv["Pass % Humanities"] * 100,
        "Gap (pts)": piv["Gap"] * 100,
    })
