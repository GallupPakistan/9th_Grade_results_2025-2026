"""
charts/grade_charts.py

Charts for pages/8_Grade_Distribution.py

Convention: each chart is its own function, taking a pandas DataFrame
(already loaded via data/loader.py) and returning a plotly Figure.
The page file calls these functions and renders them inside a
components.chart_card.chart_card() block.

TODO: implement the chart functions listed below.
"""

import plotly.express as px
import plotly.graph_objects as go
from styles.theme import COLORS, BOARD_COLOR_SEQUENCE


# def chart_xxx(df) -> go.Figure:
#     fig = px.bar(df, x=..., y=..., color_discrete_sequence=BOARD_COLOR_SEQUENCE)
#     fig.update_layout(
#         plot_bgcolor="rgba(0,0,0,0)",
#         paper_bgcolor="rgba(0,0,0,0)",
#         font_color=COLORS["text_primary"],
#     )
#     return fig
