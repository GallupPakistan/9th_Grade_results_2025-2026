"""
components/top_boards.py

Top N Boards ranked list — real data derived view from the "Overall
Summary" sheet's own Pass %age column per year (no recomputation of
board rates, straight from the source sheet). Renders 2026 first and
2025 directly beneath it in the same card, each with its own year
subheading. Rank badges, board names and progress bars are pure
HTML/CSS.

Styling lives in styles/css.py (_top_boards_css).
"""

import pandas as pd
import streamlit as st


def _year_block(df: pd.DataFrame, year: int, n: int) -> str | None:
    """HTML block for one year's Top-N list, or None when no rows exist."""
    rows = df[df["Year"] == year].copy()
    rows["Pass %age"] = pd.to_numeric(rows["Pass %age"], errors="coerce")
    rows = rows.dropna(subset=["Pass %age"]).sort_values("Pass %age", ascending=False)
    top = rows.head(n)
    if top.empty:
        return None

    max_pct = float(top["Pass %age"].max()) or 1.0
    items_html = []
    for rank, (_, row) in enumerate(top.iterrows(), start=1):
        pct = float(row["Pass %age"])
        width = max(4.0, pct / max_pct * 100.0)
        items_html.append(
            f'<div class="topboard-row">'
            f'<div class="topboard-rank">{rank}</div>'
            f'<div class="topboard-name">{row["Board"]}</div>'
            f'<div class="topboard-bar"><div class="topboard-fill" style="width:{width:.1f}%"></div></div>'
            f'<div class="topboard-value">{pct*100:.1f}%</div>'
            f"</div>"
        )
    return (
        f'<div class="topboard-year">Top {n} · {year}</div>'
        f'<div class="topboard-list">' + "".join(items_html) + "</div>"
    )


def render_top_boards(df: pd.DataFrame, n: int = 5, years: tuple = (2026, 2025)) -> None:
    """Top-N boards by Pass %age per year — 2026 ranked list first, then
    2025 stacked right below it in the same space."""
    blocks = [_year_block(df, year, n) for year in years]
    blocks = [b for b in blocks if b]
    if not blocks:
        st.info("No pass-percentage rows available for the selected boards.")
        return

    st.markdown(
        '<div class="topboard-root">' + "".join(blocks) + "</div>",
        unsafe_allow_html=True,
    )
