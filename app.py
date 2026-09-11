"""
app.py

Entry point. Streamlit treats this file as the app's ROOT page (what
opens at "/"), but the real Overview content lives in
pages/1_Overview.py — the sidebar's "Overview" link targets that file.
This file simply forwards the root URL to it, so both entry points show
the same, single Overview page (no duplicated/stale content).

Run with:
    streamlit run app.py
"""

import streamlit as st

st.switch_page("pages/1_Overview.py")