from __future__ import annotations

from datetime import date
from typing import Any

import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from frontend.i18n import format_date_value, format_number


def apply_ui() -> None:
    st.markdown(
        """
        <style>
        :root { --mt-teal:#187a78; --mt-blue:#3f6fa8; --mt-amber:#c38a20; --mt-red:#c44747; --mt-line:#d9e0e7; }
        .block-container { max-width: 1500px; padding-top: 1.4rem; padding-bottom: 3rem; }
        h1 { font-size: 2rem !important; letter-spacing: 0 !important; }
        h2 { font-size: 1.35rem !important; letter-spacing: 0 !important; margin-top: 1.5rem !important; }
        h3 { font-size: 1.05rem !important; letter-spacing: 0 !important; }
        [data-testid="stMetric"] { border: 1px solid var(--mt-line); padding: .8rem .9rem; background: white; }
        [data-testid="stMetricValue"] { font-size: 1.65rem; }
        div[data-testid="stForm"] { border: 1px solid var(--mt-line); border-radius: 4px; padding: 1rem; }
        .mt-caption { color:#667085; font-size:.86rem; margin-top:-.35rem; margin-bottom:1rem; overflow-wrap:anywhere; }
        [data-testid="stCaptionContainer"] { white-space:normal; overflow-wrap:anywhere; }
        .mt-note { border-left:4px solid var(--mt-amber); background:#fff7e8; padding:.7rem .9rem; color:#5f513d; }
        .mt-ok { border-left:4px solid var(--mt-teal); background:#edf7f6; padding:.7rem .9rem; }
        .stPlotlyChart { border: 1px solid var(--mt-line); }
        button[kind="primary"] { border-radius: 4px; }
        [data-testid="stAppDeployButton"] { display:none; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, description: str) -> None:
    st.title(title)
    st.markdown(f'<p class="mt-caption">{description}</p>', unsafe_allow_html=True)


def format_decimal(value: float | None, digits: int = 1) -> str:
    return format_number(value, digits)


def format_date(value: date | None) -> str:
    return format_date_value(value)


def chart_config() -> dict[str, Any]:
    return {"displaylogo": False, "responsive": True, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


def scrollable_plotly_chart(figure: go.Figure, *, width: int = 1000, height: int = 455) -> None:
    fixed_figure = go.Figure(figure)
    fixed_figure.update_layout(width=width, height=height - 24, autosize=False)
    config = {**chart_config(), "responsive": False}
    figure_html = fixed_figure.to_html(
        full_html=False,
        include_plotlyjs=True,
        config=config,
        default_width=f"{width}px",
        default_height=f"{height - 24}px",
    )
    components.html(
        f"""
        <style>
        html, body {{ margin:0; padding:0; width:{width}px; background:white; }}
        .chart-frame {{ width:{width}px; box-sizing:border-box; border:1px solid #d9e0e7; }}
        </style>
        <div class="chart-frame">{figure_html}</div>
        """,
        height=height,
        scrolling=True,
    )
