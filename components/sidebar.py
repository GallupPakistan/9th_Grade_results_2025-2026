"""
components/sidebar.py

Custom branded sidebar: logo + app name at top, then a flat list of
page names as rounded "capsule" nav links (styles/css.py -> _sidebar_css
handles the pill shape + active-page highlight).

Streamlit's own auto-generated page nav (built from the pages/ folder)
is hidden via CSS so page names don't appear twice - this list is the
ONLY nav rendered. Add/remove/reorder pages ONLY in the `PAGES` list
below - nothing else needs touching.
"""

import streamlit as st
from config.settings import APP_NAME, APP_SUBTITLE, APP_ICON

# (page_path, link_label, icon) - flat list, in the order they should
# appear in the sidebar. No section grouping - just the page names.
PAGES = [
    ("pages/1_Overview.py", "Overview", "🏠"),
    ("pages/2_Board_Comparison.py", "Board Comparison", "📊"),
    ("pages/3_Gender_Analysis.py", "Gender Analysis", "🚻"),
    ("pages/4_Group_Wise.py", "Group Wise", "🧪"),
    ("pages/5_Regular_vs_Private.py", "Regular vs Private", "🏫"),
    ("pages/6_Subject_Wise.py", "Subject Wise", "📚"),
    ("pages/7_District_Wise.py", "District Wise", "🗺️"),
    ("pages/8_Grade_Distribution.py", "Grade Distribution", "🏅"),
]


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            f"""<div class="sidebar-brand">
<div class="sidebar-brand-icon"><span class="material-symbols-outlined">{APP_ICON}</span></div>
<div class="sidebar-brand-text">{APP_NAME}<br><span style="font-weight:400;opacity:0.7;font-size:0.78rem;">{APP_SUBTITLE}</span></div>
</div>""",
            unsafe_allow_html=True,
        )

        for page_path, link_label, icon in PAGES:
            st.page_link(page_path, label=link_label, icon=icon)

        st.markdown(
            '<div class="sidebar-tagline">9th Class Results<br>'
            "2025 vs 2026 · 15 BISE Boards</div>",
            unsafe_allow_html=True,
        )
