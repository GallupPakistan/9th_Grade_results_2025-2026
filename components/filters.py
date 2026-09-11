"""
components/filters.py

Reusable filter widgets. The key rule for this dashboard: a dropdown for
a specific comparison type (gender / district / grade / trend) must only
ever offer the boards that actually have that data — pull the options
list from data/availability.py, never hardcode ALL_BOARDS here.
"""

import streamlit as st
from config.settings import ALL_BOARDS


def board_multiselect(
    label: str,
    available_boards: list[str],
    key: str,
    default_all: bool = True,
) -> list[str]:
    """
    A multiselect whose `options` are restricted to `available_boards`
    (e.g. data.availability.GENDER_AVAILABLE_BOARDS). Never pass
    ALL_BOARDS here for a comparison type that isn't universal.
    """
    default = available_boards if default_all else available_boards[:5]
    return st.multiselect(label, options=available_boards, default=default, key=key)


def board_selectbox(label: str, available_boards: list[str], key: str) -> str:
    """Single-board picker restricted to boards that have the relevant data."""
    return st.selectbox(label, options=available_boards, key=key)


def year_selectbox(label: str, key: str, years: list[int] | None = None) -> int:
    from config.settings import YEARS
    return st.selectbox(label, options=years or YEARS, index=len(years or YEARS) - 1, key=key)


def data_availability_note(comparison_type: str, available_boards: list[str]) -> None:
    """
    Small caption to render under any filter whose options are a subset
    of ALL_BOARDS, so the user understands why some boards are missing
    rather than assuming it's a bug.
    """
    st.caption(
        f"ℹ️ {comparison_type} data available for **{len(available_boards)} of "
        f"{len(ALL_BOARDS)}** boards: {', '.join(available_boards)}"
    )
