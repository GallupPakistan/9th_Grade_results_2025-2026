"""
pages/4_Group_Wise.py

TODO: build this page's charts in charts/group_charts.py
"""

import streamlit as st
from config.settings import APP_NAME, PAGE_ICON
from styles.css import inject_css
from components.sidebar import render_sidebar
from components.topbar import render_topbar

st.set_page_config(page_title="Group Wise - " + APP_NAME, page_icon=PAGE_ICON, layout="wide")
inject_css()
render_sidebar()

render_topbar(
    active_page="Group Wise",
    subtitle="Science vs Humanities/Arts group performance, for boards that report it.",
)

# TODO: charts go here — import from charts/group_charts.py
st.info("Group Wise page content coming next.")
