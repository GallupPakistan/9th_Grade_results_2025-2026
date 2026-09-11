"""
charts/gender_charts.py

Charts for pages/3_Gender_Analysis.py.

All functions take the normalized gender table from data/recipes.py
(Board x Year x Gender x Appeared x Passed x Pass % — already narrowed
to the boards selected via the restricted board multiselect by the
page) plus, where a year matters, the selected year(s). 14 of the 15
boards publish a gender split (FSD does not — see
data/availability.GENDER_AVAILABLE_BOARDS); Swat has only a 2026
gazette, so it is absent from every 2025 view — skip, never fabricate.

Conventions match charts/overview_charts.py (_base_layout, GENDER
colors Male=blue / Female=gold) so the pages look consistent.
"""

import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from styles.theme import COLORS, BOARD_COLOR_SEQUENCE
from config.settings import ALL_BOARDS

# Gender color-coding — identical to charts/overview_charts.py so the
# same gender renders in the same color everywhere.
GENDER_COLORS = {"Male": COLORS["accent"], "Female": COLORS["gold"]}

_YEAR_COLORS = {"2025": COLORS["trend_2025"], "2026": COLORS["trend_2026"]}

# Stable board -> color map keyed on ALL_BOARDS order, so a board keeps
# its color regardless of any active filter.
_BOARD_COLOR_MAP = {b: BOARD_COLOR_SEQUENCE[i % len(BOARD_COLOR_SEQUENCE)]
                    for i, b in enumerate(ALL_BOARDS)}


def _base_layout(fig: go.Figure, legend_title: str = "", height: int = 400) -> go.Figure:
    """Shared layout — identical to overview_charts._base_layout so the
    pages' charts sit at the same visual weight."""
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


def _compact(v: float) -> str:
    """Compact number label for chart text (2213000 -> 2.21M)."""
    v = float(v)
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:.2f}M"
    if abs(v) >= 1_000:
        return f"{v / 1_000:.1f}K"
    return f"{v:,.0f}"


# ---------------------------------------------------------------------------
# Shared pivot — one row per board with paired Male / Female columns
# ---------------------------------------------------------------------------
def prepare_gender_pivot(gender_df: pd.DataFrame, year: int) -> pd.DataFrame:
    """One row per board for the given year: Appeared/Passed/Pass % for
    Male and Female, plus the Gender Gap (Female % − Male %, stored as a
    fraction). Boards missing a gender row for that year are dropped —
    Swat in 2025 (no 2025 gazette) is the real-world case. Sorted by
    gap, widest Female advantage first."""
    rows = gender_df[gender_df["Year"] == year]
    recs = []
    for board, sub in rows.groupby("Board"):
        rec = {"Board": board}
        ok = True
        for gender in ("Male", "Female"):
            g = sub[sub["Gender"] == gender]
            if g.empty:
                ok = False
                break
            r = g.iloc[0]
            appeared = pd.to_numeric(r["Appeared"], errors="coerce")
            passed = pd.to_numeric(r["Passed"], errors="coerce")
            if pd.isna(appeared) or pd.isna(passed):
                ok = False
                break
            rec[f"Appeared {gender}"] = int(appeared)
            rec[f"Passed {gender}"] = int(passed)
            rec[f"Pass % {gender}"] = float(passed / appeared) if appeared else None
        if ok:
            rec["Gap"] = rec["Pass % Female"] - rec["Pass % Male"]
            rec["Appeared Total"] = rec["Appeared Male"] + rec["Appeared Female"]
            recs.append(rec)
    piv = pd.DataFrame(recs)
    if piv.empty:
        # e.g. Swat asked for 2025 — no rows at all; return the expected
        # shape so callers (trend chart etc.) can safely dropna/skip.
        return pd.DataFrame(columns=[
            "Board", "Appeared Male", "Passed Male", "Pass % Male",
            "Appeared Female", "Passed Female", "Pass % Female",
            "Gap", "Appeared Total",
        ])
    return piv.sort_values("Gap", ascending=False).reset_index(drop=True)


def gender_kpis(gender_df: pd.DataFrame, primary_year: int, other_year: int) -> dict:
    """KPI values aggregated from RAW counts (Passed sum / Appeared sum —
    never an average of board rates) for the primary year, with the
    other year as the delta baseline. Boards with no gender rows for a
    year (Swat 2025) simply don't contribute to that year's totals."""
    def _year_agg(year: int) -> dict:
        rows = gender_df[gender_df["Year"] == year]
        out = {}
        for gender in ("Male", "Female"):
            g = rows[rows["Gender"] == gender]
            appeared = pd.to_numeric(g["Appeared"], errors="coerce").sum()
            passed = pd.to_numeric(g["Passed"], errors="coerce").sum()
            out[gender] = {"appeared": int(appeared), "passed": int(passed),
                           "pct": (passed / appeared) if appeared else 0.0}
        out["gap"] = out["Female"]["pct"] - out["Male"]["pct"]
        return out

    cur, prv = _year_agg(primary_year), _year_agg(other_year)
    piv = prepare_gender_pivot(gender_df, primary_year)
    best = None
    if not piv.empty:
        b = piv.iloc[0]
        best = {"board": b["Board"], "gap": float(b["Gap"])}
    return {
        "male": cur["Male"],
        "female": cur["Female"],
        "gap": cur["gap"],
        "gap_delta": cur["gap"] - prv["gap"],
        "male_delta": cur["Male"]["pct"] - prv["Male"]["pct"],
        "female_delta": cur["Female"]["pct"] - prv["Female"]["pct"],
        "best_gap_board": best,
        "boards": int(gender_df[gender_df["Year"] == primary_year]["Board"].nunique()),
    }


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def chart_hero_gender_pass_rate(gender_df: pd.DataFrame, years: list[int]) -> go.Figure:
    """HERO — vertical grouped bar: Male vs Female Pass % per board for
    the selected year(s). One year = single panel; 'Both' = two panels
    (2025 | 2026) via facets. Boards ordered by the primary year's gap
    (widest Female advantage first) so both panels read together."""
    primary = max(years)
    piv = prepare_gender_pivot(gender_df, primary)
    board_order = list(piv["Board"])

    d = gender_df[gender_df["Year"].isin(years)][["Board", "Year", "Gender", "Pass %"]].copy()
    d["Pass %"] = pd.to_numeric(d["Pass %"], errors="coerce")
    d = d.dropna(subset=["Pass %"])
    d["Year"] = d["Year"].astype(str)

    facet = len(years) > 1
    fig = px.bar(
        d, x="Board", y="Pass %", color="Gender", barmode="group",
        color_discrete_map=GENDER_COLORS, text_auto=".1%",
        category_orders={"Board": board_order},
        facet_col="Year" if facet else None,
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_yaxes(tickformat=".0%", range=[0, 1], matches=None)
    fig.update_xaxes(tickangle=-45)
    if facet:
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    return _base_layout(fig, legend_title="Gender", height=460)


def chart_gender_gap(gender_df: pd.DataFrame, years: list[int]) -> go.Figure:
    """Diverging horizontal bar: Gender Gap (Female % − Male %) per board.
    Single year = one bar per board, colored by direction (green =
    Female ahead / red = Male ahead). 'Both' = two year-colored bars per
    board so the gap's drift 2025→2026 is visible."""
    if len(years) == 1:
        piv = prepare_gender_pivot(gender_df, years[0]).sort_values("Gap")
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
            p = prepare_gender_pivot(gender_df, year)
            for _, r in p.iterrows():
                recs.append({"Board": r["Board"], "Year": str(year), "Gap": r["Gap"]})
        d = pd.DataFrame(recs)
        order = list(prepare_gender_pivot(gender_df, max(years))["Board"])
        fig = px.bar(
            d, x="Gap", y="Board", color="Year", orientation="h", barmode="group",
            color_discrete_map=_YEAR_COLORS, category_orders={"Board": order},
        )
        fig.update_traces(texttemplate="%{x*100:+.1f} pp",
                          textposition="outside", cliponaxis=False)
    fig.update_xaxes(tickformat=".0%")
    return _base_layout(fig, legend_title="Year" if len(years) > 1 else "", height=460)


def chart_gap_trend_by_board(gender_df: pd.DataFrame) -> go.Figure:
    """Line chart: the gender gap (Female % − Male %) per board, 2025 →
    2026 — one stable-colored line per board. Boards without a 2025
    gazette (Swat) show only their 2026 point; the zero line marks
    parity. Shows whether each board's gap is widening or closing."""
    fig = go.Figure()
    for _, r in prepare_gender_pivot(gender_df, 2026).iterrows():
        board = r["Board"]
        sub = gender_df[(gender_df["Board"] == board) & (gender_df["Year"].isin([2025, 2026]))]
        xs, ys = [], []
        for year in (2025, 2026):
            p = prepare_gender_pivot(sub, year)
            row = p[p["Board"] == board]
            if not row.empty:
                xs.append(year)
                ys.append(float(row.iloc[0]["Gap"]))
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines+markers+text", name=board,
            line=dict(color=_BOARD_COLOR_MAP[board], width=2),
            marker=dict(size=7),
            text=[f"{y*100:+.1f}" for y in ys],
            textposition="top center", textfont_size=9, cliponaxis=False,
            hovertemplate=f"{board}<br>%{{x}} gap: %{{y*100:+.1f}} pp<extra></extra>",
        ))
    fig.add_hline(y=0, line_dash="dash", line_color=COLORS["neutral"],
                  annotation_text="Parity (M = F)")
    fig.update_xaxes(tickformat="d", tickmode="array",
                     tickvals=[2025, 2026], range=[2024.6, 2026.4])
    fig.update_yaxes(tickformat=".0%")
    return _base_layout(fig, legend_title="Board", height=460)


def chart_gender_appeared(gender_df: pd.DataFrame, years: list[int]) -> go.Figure:
    """Stacked vertical bar: Appeared candidates per board split into
    Male (bottom) vs Female (top), for the selected year(s). 'Both' =
    two panels via facets. Shows the volume context behind the rates."""
    primary = max(years)
    piv = prepare_gender_pivot(gender_df, primary)
    board_order = list(piv.sort_values("Appeared Total", ascending=False)["Board"])

    d = gender_df[gender_df["Year"].isin(years)][["Board", "Year", "Gender", "Appeared"]].copy()
    d["Appeared"] = pd.to_numeric(d["Appeared"], errors="coerce")
    d = d.dropna(subset=["Appeared"])
    d["Year"] = d["Year"].astype(str)

    facet = len(years) > 1
    fig = px.bar(
        d, x="Board", y="Appeared", color="Gender", barmode="stack",
        color_discrete_map=GENDER_COLORS,
        category_orders={"Board": board_order},
        facet_col="Year" if facet else None,
    )
    fig.update_traces(texttemplate="%{y:,}", textposition="inside",
                      insidetextanchor="middle", cliponaxis=False)
    fig.update_yaxes(tickformat=".2s")
    fig.update_xaxes(tickangle=-45)
    if facet:
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    return _base_layout(fig, legend_title="Gender", height=460)


def chart_gender_scatter(gender_df: pd.DataFrame, years: list[int]) -> go.Figure:
    """Scatter: Male Pass % (x) vs Female Pass % (y), one labelled point
    per board, with a dashed 45° parity line — above the line = Female
    ahead, below = Male ahead. 'Both' colors the points by year."""
    recs = []
    for year in years:
        p = prepare_gender_pivot(gender_df, year)
        for _, r in p.iterrows():
            recs.append({"Board": r["Board"], "Year": str(year),
                         "Male": r["Pass % Male"], "Female": r["Pass % Female"],
                         "Appeared": r["Appeared Total"]})
    d = pd.DataFrame(recs)

    fig = px.scatter(
        d, x="Male", y="Female", color="Year" if len(years) > 1 else None,
        text="Board", custom_data=["Appeared"],
        color_discrete_map=_YEAR_COLORS,
    )
    fig.update_traces(
        textposition="top center", textfont_size=9, cliponaxis=False,
        marker=dict(size=11, opacity=0.85),
        hovertemplate="%{text}<br>Male %{x:.1%} · Female %{y:.1%}"
                      "<br>Appeared %{customdata[0]:,}<extra></extra>",
    )
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1], mode="lines",
        line=dict(dash="dash", color=COLORS["neutral"]),
        name="Parity (M = F)", hoverinfo="skip",
    ))
    fig.update_xaxes(tickformat=".0%", range=[0.2, 1.02])
    fig.update_yaxes(tickformat=".0%", range=[0.2, 1.02])
    return _base_layout(fig, legend_title="Year" if len(years) > 1 else "", height=460)


def chart_gender_donut_grid(gender_df: pd.DataFrame, year: int) -> go.Figure:
    """Grid of small donut pairs — per board, a Male donut (pass vs fail)
    beside a Female donut (pass vs fail), 4 boards per row. Green =
    passed, red = failed; the hole carries M/F. Boards ordered by the
    gender gap (widest Female advantage first)."""
    piv = prepare_gender_pivot(gender_df, year)
    boards = list(piv["Board"])
    per_row = 4                      # boards per row → 8 pie columns
    n_cols = per_row * 2
    n_rows = math.ceil(len(boards) / per_row)

    hs, vs = 0.02, 0.10
    cell_w = (1 - hs * (n_cols - 1)) / n_cols
    cell_h = (1 - vs * (n_rows - 1)) / n_rows

    fig = make_subplots(
        rows=n_rows, cols=n_cols,
        specs=[[{"type": "domain"}] * n_cols for _ in range(n_rows)],
        horizontal_spacing=hs, vertical_spacing=vs,
    )

    def _col_center(c: int) -> float:
        return (c - 1) * (cell_w + hs) + cell_w / 2

    def _row_top(r: int) -> float:
        return 1 - (r - 1) * (cell_h + vs)

    for i, board in enumerate(boards):
        r = i // per_row + 1
        c0 = (i % per_row) * 2 + 1
        row_top, row_center = _row_top(r), _row_top(r) - cell_h / 2
        rec = piv[piv["Board"] == board].iloc[0]
        for j, gender in enumerate(("Male", "Female")):
            appeared = int(rec[f"Appeared {gender}"])
            passed = int(rec[f"Passed {gender}"])
            failed = appeared - passed
            fig.add_trace(go.Pie(
                values=[passed, failed], labels=["Passed", "Failed"], hole=0.62,
                marker_colors=[COLORS["positive"], COLORS["negative"]],
                textinfo="percent", textposition="inside",
                insidetextorientation="horizontal", textfont_size=9,
                sort=False, direction="clockwise",
                showlegend=(i == 0 and j == 0),
                hovertemplate=(f"{board} · {gender}<br>%{{label}}: "
                               f"%{{value:,}} (%{{percent}})<extra></extra>"),
            ), row=r, col=c0 + j)
            fig.add_annotation(
                x=_col_center(c0 + j), y=row_center, text="M" if gender == "Male" else "F",
                showarrow=False, font=dict(size=17, color=GENDER_COLORS[gender]),
            )
        fig.add_annotation(
            x=(_col_center(c0) + _col_center(c0 + 1)) / 2,
            y=row_top - cell_h * 0.06, text=board, showarrow=False,
            font=dict(size=11, color=COLORS["text_on_light"]),
        )

    fig.update_layout(height=240 * n_rows + 60, margin=dict(t=16, b=16, l=16, r=16),
                      paper_bgcolor="rgba(0,0,0,0)", font_color=COLORS["text_on_light"],
                      legend=dict(orientation="h", y=-0.02))
    return fig


def gender_table(gender_df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Display table for one year: Board | M Appeared/Passed/Pass% |
    F Appeared/Passed/Pass% | Gap. Pass % and Gap are stored ×100 (and
    gap in percentage points) because Streamlit's NumberColumn printf
    format does not scale fractions."""
    piv = prepare_gender_pivot(gender_df, year)
    out = pd.DataFrame({
        "Board": piv["Board"],
        "M-Appeared": piv["Appeared Male"],
        "M-Passed": piv["Passed Male"],
        "M-Pass %": piv["Pass % Male"] * 100,
        "F-Appeared": piv["Appeared Female"],
        "F-Passed": piv["Passed Female"],
        "F-Pass %": piv["Pass % Female"] * 100,
        "Gap (pts)": piv["Gap"] * 100,
    })
    return out
