"""
pages/6_Subject_Wise.py

TODO: build this page's charts in charts/subject_charts.py
"""

import streamlit as st
from config.settings import APP_NAME, PAGE_ICON
from styles.css import inject_css
from components.sidebar import render_sidebar
from components.topbar import render_topbar

st.set_page_config(page_title="Subject Wise - " + APP_NAME, page_icon=PAGE_ICON, layout="wide")
inject_css()
render_sidebar()

render_topbar(
    active_page="Subject Wise",
    subtitle="Subject-level pass percentage, for boards that publish subject-wise tables.",
)

# TODO: charts go here — import from charts/subject_charts.py
st.info("Subject Wise page content coming next.")
