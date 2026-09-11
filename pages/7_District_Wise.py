"""
pages/7_District_Wise.py

TODO: build this page's charts in charts/district_charts.py
"""

import streamlit as st
from config.settings import APP_NAME, PAGE_ICON
from styles.css import inject_css
from components.sidebar import render_sidebar
from components.topbar import render_topbar

st.set_page_config(page_title="District Wise - " + APP_NAME, page_icon=PAGE_ICON, layout="wide")
inject_css()
render_sidebar()

render_topbar(
    active_page="District Wise",
    subtitle="District-level pass percentage, for boards that publish district-wise tables.",
)

# TODO: charts go here — import from charts/district_charts.py
st.info("District Wise page content coming next.")
