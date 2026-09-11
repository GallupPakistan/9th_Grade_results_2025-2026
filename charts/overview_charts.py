"""
charts/overview_charts.py

Charts for pages/1_Overview.py.

Two families of functions live here:

1. Overall-Summary charts (chart_yoy_totals, chart_board_pass_rate,
   chart_yoy_change_by_board, chart_appeared_share, top_movers) — each
   takes the filtered "Overall Summary" DataFrame (already narrowed to
   the selected province's boards by the page file) and returns a
   plotly Figure. The "Overall Summary" sheet has 3 rows per board:
   Year=2025, Year=2026, and Year="Change (2026-2025)". Every function
   must exclude the "Change" rows before aggregating numeric totals —
   it is a delta row, not a data point — except
   chart_yoy_change_by_board() and top_movers(), which read it directly
   since it IS the change.

2. Gender / Regular-vs-Private aggregate charts (chart_gender_*,
   chart_category_*) — each takes the corresponding normalized table
   from data/recipes.py (already narrowed to the selected province's
   boards by the page file). Pass % is always recomputed as
   Passed / Appeared from the recipe tables' raw counts.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from styles.theme import COLORS, BOARD_COLOR_SEQUENCE
from data.availability import PROVINCE_BOARD_MAP


def _data_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Returns only the real Year=2025 / Year=2026 rows, dropping the
    'Change (2026-2025)' delta rows that the master sheet also carries."""
    return df[df["Year"].isin([2025, 2026])].copy()


def _base_layout(fig: go.Figure, legend_title: str = "", height: int = 400) -> go.Figure:
    """Shared layout for every Overview chart. The fixed height keeps
    the 2-column chart grid visually even; uniformtext hides (instead
    of overlapping) any bar/slice label that doesn't fit."""
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


def compute_province_totals(df: pd.DataFrame) -> dict:
    """Aggregates Appeared / Passed / Failed for whatever boards are
    already present in df (the page decides which boards to pass in
    based on the province filter), for both years.

    Returns a dict with 2025/2026 totals and the YoY deltas, used to
    drive the KPI row.
    """
    rows = _data_rows(df)
    out = {}
    for year in (2025, 2026):
        year_rows = rows[rows["Year"] == year]
        appeared = int(year_rows["Appeared"].sum())
        passed = int(year_rows["Passed"].sum())
        failed = appeared - passed
        out[year] = {"appeared": appeared, "passed": passed, "failed": failed}
    out["appeared_delta"] = out[2026]["appeared"] - out[2025]["appeared"]
    out["passed_delta"] = out[2026]["passed"] - out[2025]["passed"]
    out["failed_delta"] = out[2026]["failed"] - out[2025]["failed"]
    return out


def chart_yoy_totals(df: pd.DataFrame) -> go.Figure:
    """Overall Performance (grouped bar): totals for the selected boards —
    Appeared vs Passed vs Failed, 2025 vs 2026. Metric-colored (Appeared
    blue / Passed green / Failed red) with year groups, compact value
    labels above each bar."""
    rows = _data_rows(df)
    agg = rows.groupby("Year")[["Appeared", "Passed"]].sum().reset_index()
    agg["Failed"] = agg["Appeared"] - agg["Passed"]
    melted = agg.melt(id_vars="Year", value_vars=["Appeared", "Passed", "Failed"],
                       var_name="Metric", value_name="Count")
    melted["Year"] = melted["Year"].astype(str)

    fig = go.Figure()
    for metric, color_key in (("Appeared", "accent"), ("Passed", "positive"), ("Failed", "negative")):
        sub = melted[melted["Metric"] == metric]
        fig.add_trace(go.Bar(
            x=sub["Year"], y=sub["Count"], name=metric,
            marker_color=COLORS[color_key],
            text=[_compact(v) for v in sub["Count"]],
            textposition="outside", cliponaxis=False,
        ))
    fig.update_xaxes(categoryorder="array", categoryarray=["2025", "2026"])
    fig.update_yaxes(tickformat="~s")
    return _base_layout(fig, legend_title="")


def _compact(v: float) -> str:
    """Compact label helper for chart text (2213000 -> 2.21M)."""
    v = float(v)
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:.2f}M"
    if abs(v) >= 1_000:
        return f"{v / 1_000:.1f}K"
    return f"{v:,.0f}"


def chart_province_pass_trend(overall_df: pd.DataFrame) -> go.Figure:
    """Pass % Trend by Province — aggregate Pass % (Passed / Appeared,
    recomputed from raw counts, never averaged) for each province in
    PROVINCE_BOARD_MAP, 2025 vs 2026. Light blue vs dark navy."""
    rows = _data_rows(overall_df)
    recs = []
    for province, boards in PROVINCE_BOARD_MAP.items():
        sub = rows[rows["Board"].isin(boards)]
        for year in (2025, 2026):
            y = sub[sub["Year"] == year]
            appeared = y["Appeared"].sum()
            if appeared == 0:
                continue  # e.g. Swat has no 2025 gazette — skip, never fabricate
            recs.append({"Province": province, "Year": str(year),
                         "Pass %": y["Passed"].sum() / appeared})
    agg = pd.DataFrame(recs)

    fig = px.bar(
        agg, x="Province", y="Pass %", color="Year", barmode="group",
        color_discrete_map={"2025": COLORS["trend_2025"], "2026": COLORS["trend_2026"]},
        text_auto=".1%",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_yaxes(tickformat=".0%", range=[0, 1])
    fig.update_layout(xaxis_categoryorder="total descending")
    return _base_layout(fig, legend_title="Year")


def chart_board_pass_rate(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar: Pass % per board (within the current filter), 2026, sorted best to worst."""
    rows = _data_rows(df)
    board_2026 = rows[rows["Year"] == 2026].sort_values("Pass %age", ascending=True)

    fig = px.bar(
        board_2026, x="Pass %age", y="Board", orientation="h",
        color="Board", color_discrete_sequence=BOARD_COLOR_SEQUENCE,
        text=board_2026["Pass %age"].map(lambda v: f"{v*100:.1f}%"),
    )
    fig.update_layout(showlegend=False)
    fig.update_xaxes(tickformat=".0%")
    return _base_layout(fig)


def chart_yoy_change_by_board(df: pd.DataFrame) -> go.Figure:
    """Diverging bar: change in Pass % (2026 vs 2025) per board."""
    change_rows = df[df["Year"] == "Change (2026-2025)"].copy()
    change_rows = change_rows.sort_values("Pass %age")
    colors = [COLORS["positive"] if v >= 0 else COLORS["negative"] for v in change_rows["Pass %age"]]

    fig = go.Figure(go.Bar(
        x=change_rows["Pass %age"],
        y=change_rows["Board"],
        orientation="h",
        marker_color=colors,
        text=change_rows["Pass %age"].map(lambda v: f"{v*100:+.1f}%"),
        textposition="outside",
        cliponaxis=False,  # keep outside labels from being clipped at the plot edge
    ))
    fig.update_xaxes(tickformat=".0%")
    return _base_layout(fig)


def chart_appeared_share(df: pd.DataFrame) -> go.Figure:
    """Donut: share of total 2026 Appeared candidates per board (within the current filter)."""
    rows = _data_rows(df)
    board_2026 = rows[rows["Year"] == 2026]

    fig = px.pie(
        board_2026, names="Board", values="Appeared", hole=0.55,
        color_discrete_sequence=BOARD_COLOR_SEQUENCE,
    )
    # 15 slices: inside percents only (labels would overlap); the legend
    # carries the board names. uniformtext hides too-tight percents.
    fig.update_traces(
        textinfo="percent", textposition="inside", insidetextorientation="horizontal",
    )
    return _base_layout(fig)


# ---------------------------------------------------------------------------
# Gender & Regular-vs-Private aggregate charts — data comes from the
# verified per-board extraction tables in data/recipes.py, narrowed to
# the current province filter by the page before being passed in.
# ---------------------------------------------------------------------------

GENDER_COLORS = {"Male": COLORS["accent"], "Female": COLORS["gold"]}
CATEGORY_COLORS = {"Regular": COLORS["accent"], "Private": COLORS["gold"]}


def _aggregate_rate(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Sums Appeared/Passed by the given keys and recomputes the
    aggregate Pass % from the totals (never averages per-board rates)."""
    agg = df.groupby(keys, as_index=False)[["Appeared", "Passed"]].sum()
    agg["Pass %"] = agg["Passed"] / agg["Appeared"]
    return agg


def chart_gender_pass_rate(gender_df: pd.DataFrame) -> go.Figure:
    """Grouped bar: aggregate Pass % by gender, 2025 vs 2026."""
    agg = _aggregate_rate(gender_df, ["Gender", "Year"])
    agg["Year"] = agg["Year"].astype(str)

    fig = px.bar(
        agg, x="Gender", y="Pass %", color="Year", barmode="group",
        color_discrete_map={"2025": COLORS["year_2025"], "2026": COLORS["year_2026"]},
        text_auto=".1%",
    )
    fig.update_yaxes(tickformat=".0%")
    return _base_layout(fig, legend_title="Year")


def chart_gender_share(gender_df: pd.DataFrame) -> go.Figure:
    """Donut: share of 2026 Appeared candidates by gender."""
    rows = gender_df[gender_df["Year"] == 2026]
    agg = rows.groupby("Gender", as_index=False)["Appeared"].sum()

    fig = px.pie(
        agg, names="Gender", values="Appeared", hole=0.55,
        color="Gender", color_discrete_map=GENDER_COLORS,
    )
    fig.update_traces(textinfo="percent+label")
    return _base_layout(fig)


def chart_category_pass_rate(category_df: pd.DataFrame) -> go.Figure:
    """Grouped bar: Regular vs Private aggregate Pass %, 2025 vs 2026."""
    agg = _aggregate_rate(category_df, ["Category", "Year"])
    agg["Year"] = agg["Year"].astype(str)

    fig = px.bar(
        agg, x="Category", y="Pass %", color="Year", barmode="group",
        color_discrete_map={"2025": COLORS["year_2025"], "2026": COLORS["year_2026"]},
        text_auto=".1%",
    )
    fig.update_yaxes(tickformat=".0%")
    return _base_layout(fig, legend_title="Year")


def chart_category_share(category_df: pd.DataFrame) -> go.Figure:
    """Donut: share of 2026 Appeared candidates, Regular vs Private."""
    rows = category_df[category_df["Year"] == 2026]
    agg = rows.groupby("Category", as_index=False)["Appeared"].sum()

    fig = px.pie(
        agg, names="Category", values="Appeared", hole=0.55,
        color="Category", color_discrete_map=CATEGORY_COLORS,
    )
    fig.update_traces(textinfo="percent+label")
    return _base_layout(fig)


# ---------------------------------------------------------------------------
# Pakistan choropleth map — real province boundaries from
# assets/pakistan_provinces.geojson (geoBoundaries ADM1, Public Domain).
# Only provinces that actually have boards in our 15-board dataset are
# colored (by 2026 Appeared count); all others render grey — we never
# fabricate data for Sindh/Balochistan/AJK/GB.
# ---------------------------------------------------------------------------

import json
from pathlib import Path

_GEOJSON_PATH = Path(__file__).resolve().parent.parent / "assets" / "pakistan_provinces.geojson"

# GeoJSON shapeName -> our PROVINCE_BOARD_MAP keys
_GEO_PROVINCE_ALIASES = {
    "Punjab": "Punjab",
    "Khyber Pakhtunkhwa": "Khyber Pakhtunkhwa",
    "Islamabad Capital Territory": "Federal",
}


def _province_totals(overall_df: pd.DataFrame) -> dict:
    """{province: {year: {appeared, passed, pass%}}} for both 2025 and
    2026, aggregated from raw counts. Provinces without any appeared
    candidates are never fabricated — they're simply absent here."""
    rows = _data_rows(overall_df)
    out = {}
    for province, boards in PROVINCE_BOARD_MAP.items():
        sub = rows[rows["Board"].isin(boards)]
        year_data = {}
        for year in (2025, 2026):
            y = sub[sub["Year"] == year]
            appeared = int(y["Appeared"].sum())
            passed = int(y["Passed"].sum())
            year_data[year] = {
                "appeared": appeared,
                "passed": passed,
                "pass_pct": passed / appeared if appeared else 0.0,
            }
        if any(d["appeared"] > 0 for d in year_data.values()):
            out[province] = year_data
    return out


def _map_empty_fallback(message: str) -> go.Figure:
    """Friendly placeholder when the GeoJSON is missing, so the page never
    crashes on the map."""
    fig = go.Figure()
    fig.update_layout(
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        annotations=[dict(
            text=message, showarrow=False,
            font=dict(color=COLORS["text_on_light_muted"], size=14),
        )],
        height=440, margin=dict(t=10, b=10, l=10, r=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def chart_pakistan_map(overall_df: pd.DataFrame) -> go.Figure:
    """Full-Pakistan choropleth. Every region in the GeoJSON renders (grey
    when the 15-board dataset has no boards there, colored by 2026 Appeared
    when it does), so the whole country outline is always visible. Hovering
    a data province shows the full picture: 2026 AND 2025 Appeared / Passed
    / Pass % plus the number of boards feeding it."""
    if not _GEOJSON_PATH.exists():
        return _map_empty_fallback("Pakistan map data not found")

    with open(_GEOJSON_PATH, encoding="utf-8") as f:
        geo = json.load(f)

    totals = _province_totals(overall_df)
    data_locs, data_vals, data_hover = [], [], []
    nodata_locs, nodata_hover = [], []

    for feature in geo["features"]:
        name = feature["properties"]["shapeName"]
        prov = _GEO_PROVINCE_ALIASES.get(name)
        if prov and prov in totals:
            t = totals[prov]
            t26, t25 = t.get(2026), t.get(2025)
            a26 = t26["appeared"] if t26 else 0
            p26 = t26["passed"] if t26 else 0
            a25 = t25["appeared"] if t25 else 0
            p25 = t25["passed"] if t25 else 0
            pct26 = p26 / a26 * 100 if a26 else 0.0
            pct25 = p25 / a25 * 100 if a25 else 0.0
            boards = PROVINCE_BOARD_MAP[prov]
            data_locs.append(name)
            data_vals.append(a26)
            data_hover.append(
                f"<b>{name}</b>"
                f"<br><span style='opacity:.7'>Appeared 2026</span> {a26:,}"
                f"<br><span style='opacity:.7'>Passed 2026</span> {p26:,}"
                f"<br><span style='opacity:.7'>Pass % 2026</span> <b>{pct26:.1f}%</b>"
                f"<br><span style='opacity:.7'>Appeared 2025</span> {a25:,}"
                f"<br><span style='opacity:.7'>Passed 2025</span> {p25:,}"
                f"<br><span style='opacity:.7'>Pass % 2025</span> <b>{pct25:.1f}%</b>"
                f"<br><span style='opacity:.7'>BISE boards in dataset</span> {len(boards)}"
                f"<extra></extra>"
            )
        else:
            nodata_locs.append(name)
            nodata_hover.append(
                f"<b>{name}</b>"
                f"<br><span style='opacity:.7'>No BISE board data in this dataset</span>"
                f"<extra></extra>"
            )

        # Build a SINGLE choropleth trace containing every GeoJSON region so
    # that `fitbounds="locations"` frames to the full Pakistan outline
    # (two-trace approaches make Plotly 7 zoom to only the data provinces and
    # drop the no-data grey regions — the "tiny blob / one area" symptom).
    #
    # Color logic:
    #   * Provinces WITH board data  -> blue scale  (Appeared 2026)
    #   * Provinces WITHOUT data      -> flat grey   (map_no_data_strong)
    #
    # Implemented via one z array (0 for no-data, real Appeared for data)
    # plus a custom colorscale whose 0 bucket is grey and whose remaining
    # range maps through COLORS["map_scale"]. zmin=0 / zmax=max(data) pins
    # the scale so the blue gradient is deterministic (not collapsed to black).
    map_locs, map_z, map_hover = [], [], []
    vmax = max(data_vals) if data_vals else 1
    for feature in geo["features"]:
        name = feature["properties"]["shapeName"]
        prov = _GEO_PROVINCE_ALIASES.get(name)
        if prov and prov in totals:
            t = totals[prov]
            t26, t25 = t.get(2026), t.get(2025)
            a26 = t26["appeared"] if t26 else 0
            p26 = t26["passed"] if t26 else 0
            a25 = t25["appeared"] if t25 else 0
            p25 = t25["passed"] if t25 else 0
            pct26 = p26 / a26 * 100 if a26 else 0.0
            pct25 = p25 / a25 * 100 if a25 else 0.0
            boards = PROVINCE_BOARD_MAP[prov]
            map_locs.append(name)
            map_z.append(a26)
            map_hover.append(
                f"<b>{name}</b>"
                f"<br><span style='opacity:.7'>Appeared 2026</span> {a26:,}"
                f"<br><span style='opacity:.7'>Passed 2026</span> {p26:,}"
                f"<br><span style='opacity:.7'>Pass % 2026</span> <b>{pct26:.1f}%</b>"
                f"<br><span style='opacity:.7'>Appeared 2025</span> {a25:,}"
                f"<br><span style='opacity:.7'>Passed 2025</span> {p25:,}"
                f"<br><span style='opacity:.7'>Pass % 2025</span> <b>{pct25:.1f}%</b>"
                f"<br><span style='opacity:.7'>BISE boards in dataset</span> {len(boards)}"
                f"<extra></extra>"
            )
        else:
            map_locs.append(name)
            map_z.append(0)
            map_hover.append(
                f"<b>{name}</b>"
                f"<br><span style='opacity:.7'>No BISE board data in this dataset</span>"
                f"<extra></extra>"
            )

    # Custom colorscale: a hard grey stop at z=0 (no-data provinces) then the
    # blue progression for real Appeared values. The two identical grey stops
    # bracket the z=0 bucket so it's a flat grey, and the blue scale begins
    # immediately after.
    grey = COLORS["map_no_data_strong"]
    blues = COLORS["map_scale"]
    # Interpolate blue stops across the non-zero portion of [0, vmax].
    blue_stops = []
    n = max(len(blues) - 1, 1)
    for i, col in enumerate(blues):
        frac = i / n if n else 0.0
        # map blue range to (0+epsilon, 1] of the z domain
        blue_stops.append([frac, col])
    # Shift so the first blue stop sits just above 0 (keeps z=0 = grey)
    z_epsilon = 0.5 / vmax if vmax else 0.0  # half a step above 0
    colorscale = [[0.0, grey], [z_epsilon, grey]]
    for frac, col in blue_stops:
        # remap frac (0..1) to (z_epsilon .. 1)
        mapped = z_epsilon + frac * (1.0 - z_epsilon)
        colorscale.append([mapped, col])

    fig = go.Figure(go.Choropleth(
        geojson=geo,
        featureidkey="properties.shapeName",
        locations=map_locs,
        z=map_z,
        zmin=0,
        zmax=vmax,
        colorscale=colorscale,
        showscale=True,
        colorbar=dict(
            title="Appeared 2026", thickness=12, len=0.75,
            tickformat="~s", x=1.0,
        ),
        marker_line_color="#FFFFFF",
        marker_line_width=1.2,
        text=map_hover,
        hovertemplate="%{text}",
        name="",
    ))

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_color=COLORS["text_on_light"], font_size=12,
        margin=dict(t=6, b=6, l=6, r=6), height=460,
        hoverlabel=dict(bgcolor=COLORS["primary"], font_color="#FFFFFF",
                        font_size=12, bordercolor=COLORS["primary_light"]),
    )
    # Map framing — fitbounds="locations" ALONE does the zoom/frame.
    # Do NOT add center / lataxis_range / lonaxis_range alongside it:
    # Plotly treats a manual center + explicit axis ranges as a competing
    # "user override" vs fitbounds' auto-computed frame, which corrupts the
    # geo projection scale and pushes every province polygon outside the
    # canvas (leaving only the flat landcolor background visible). With only
    # fitbounds set, Plotly computes the frame from all 7 regions' GeoJSON
    # coordinates, so the whole country always fills the chart.
    fig.update_geos(
        fitbounds="locations",
        visible=True,
        projection_type="mercator",
        showframe=False,
        showcoastlines=False,
        showcountries=False,
        showland=True,
        landcolor=COLORS["map_land"],
        bgcolor="rgba(0,0,0,0)",
    )
    return fig


def top_movers(df: pd.DataFrame) -> tuple:
    """Reads the 'Change (2026-2025)' rows of the Overall Summary and
    returns (gainer_row, decliner_row) — the boards with the largest
    rise and fall in Pass %age. Either may be None if no change rows
    exist. Pass %age here is a fraction (e.g. 0.0428 = +4.28 pts)."""
    change = df[df["Year"] == "Change (2026-2025)"].copy()
    change["Pass %age"] = pd.to_numeric(change["Pass %age"], errors="coerce")
    change = change.dropna(subset=["Pass %age"])
    if change.empty:
        return None, None
    gainer = change.loc[change["Pass %age"].idxmax()]
    decliner = change.loc[change["Pass %age"].idxmin()]
    return gainer, decliner
