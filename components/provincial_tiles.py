"""
components/provincial_tiles.py

Provincial Comparison tiles — one silhouette-style stat card per province
that actually has board data in the dataset (Punjab / Khyber Pakhtunkhwa /
Federal). Toggle between "Appeared" (2026 candidate count) and "Pass %"
(2026 passed / appeared, recomputed from raw counts). Provinces without
any board data are never fabricated — they're simply absent here.

Styling lives in styles/css.py (_prov_tiles_css).
"""

import pandas as pd
import streamlit as st
from data.availability import PROVINCE_BOARD_MAP


def _province_rows(overall_df: pd.DataFrame, year: int) -> list[dict]:
    """Per-province 2026 aggregates (real summed counts, never guessed)."""
    rows = overall_df[overall_df["Year"] == year].copy()
    out = []
    for province, boards in PROVINCE_BOARD_MAP.items():
        sub = rows[rows["Board"].isin(boards)]
        appeared = int(sub["Appeared"].sum())
        if appeared == 0:
            continue
        passed = int(sub["Passed"].sum())
        out.append(
            {
                "name": province,
                "appeared": appeared,
                "passed": passed,
                "pass_pct": passed / appeared,
            }
        )
    return out


def render_province_tiles(overall_df: pd.DataFrame, metric: str = "Appeared") -> None:
    """metric: 'Appeared' shows candidate counts; 'Pass %' shows pass rates."""
    tiles = _province_rows(overall_df, 2026)
    if not tiles:
        st.info("No province-level data available for 2026.")
        return

    use_pct = metric == "Pass %"
    values = [t["pass_pct"] if use_pct else t["appeared"] for t in tiles]
    mx = max(values) or 1.0

    items = []
    for t in tiles:
        v = t["pass_pct"] if use_pct else t["appeared"]
        display = f"{v * 100:.1f}%" if use_pct else f"{v:,}"
        sub = "Pass % · 2026" if use_pct else "Appeared · 2026"
        icon = "percent" if use_pct else "groups"
        width = max(6.0, v / mx * 100.0)
        items.append(
            f'<div class="prov-tile">'
            f'<div class="prov-tile-name"><span class="material-symbols-outlined">{icon}</span>{t["name"]}</div>'
            f'<div class="prov-tile-value">{display}</div>'
            f'<div class="prov-tile-sub">{sub}</div>'
            f'<div class="prov-tile-bar"><div class="prov-tile-fill" style="width:{width:.1f}%"></div></div>'
            f"</div>"
        )

    st.markdown(
        '<div class="prov-grid">' + "".join(items) + "</div>",
        unsafe_allow_html=True,
    )