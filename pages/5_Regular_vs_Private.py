"""
pages/5_Regular_vs_Private.py

TODO: build this page's charts in charts/regular_private_charts.py
"""

import streamlit as st
from config.settings import APP_NAME, PAGE_ICON
from styles.css import inject_css
from components.sidebar import render_sidebar
from components.topbar import render_topbar

st.set_page_config(page_title="Regular vs Private - " + APP_NAME, page_icon=PAGE_ICON, layout="wide")
inject_css()
render_sidebar()

render_topbar(
    active_page="Regular vs Private",
    subtitle="Regular vs Private candidate performance, for boards that report it.",
)

# TODO: charts go here — import from charts/regular_private_charts.py
st.info("Regular vs Private page content coming next.")
