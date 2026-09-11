"""
pages/8_Grade_Distribution.py

TODO: build this page's charts in charts/grade_charts.py
"""

import streamlit as st
from config.settings import APP_NAME, PAGE_ICON
from styles.css import inject_css
from components.sidebar import render_sidebar
from components.topbar import render_topbar

st.set_page_config(page_title="Grade Distribution - " + APP_NAME, page_icon=PAGE_ICON, layout="wide")
inject_css()
render_sidebar()

render_topbar(
    active_page="Grade Distribution",
    subtitle="Letter-grade (A1-E) distribution, for boards that publish grade breakdowns.",
)

# TODO: charts go here — import from charts/grade_charts.py
st.info("Grade Distribution page content coming next.")
