from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


TEMPLATE = "plotly_white"
COLOR_SEQUENCE = ["#2563eb", "#16a34a", "#dc2626", "#9333ea", "#ea580c", "#0891b2", "#4f46e5"]


def empty_figure(title: str, message: str = "No data for the selected filters") -> go.Figure:
    figure = go.Figure()
    figure.add_annotation(text=message, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
    figure.update_layout(template=TEMPLATE, title=title, height=360, margin={"l": 24, "r": 24, "t": 56, "b": 24})
    return figure


def _finish(figure: go.Figure, height: int = 360) -> go.Figure:
    figure.update_layout(
        template=TEMPLATE,
        height=height,
        colorway=COLOR_SEQUENCE,
        margin={"l": 24, "r": 24, "t": 56, "b": 24},
        legend_title_text="",
    )
    return figure


def bar_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: str | None = None,
    orientation: str = "v",
    height: int = 360,
) -> go.Figure:
    if data.empty:
        return empty_figure(title)
    figure = px.bar(data, x=x, y=y, color=color, title=title, orientation=orientation, color_discrete_sequence=COLOR_SEQUENCE)
    return _finish(figure, height)


def line_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: str | None = None,
    height: int = 360,
) -> go.Figure:
    if data.empty:
        return empty_figure(title)
    figure = px.line(data, x=x, y=y, color=color, title=title, markers=True, color_discrete_sequence=COLOR_SEQUENCE)
    return _finish(figure, height)


def donut_chart(data: pd.DataFrame, names: str, values: str, title: str, height: int = 360) -> go.Figure:
    if data.empty:
        return empty_figure(title)
    figure = px.pie(data, names=names, values=values, title=title, hole=0.48, color_discrete_sequence=COLOR_SEQUENCE)
    return _finish(figure, height)


def scatter_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: str | None = None,
    size: str | None = None,
    hover_name: str | None = None,
    height: int = 420,
) -> go.Figure:
    if data.empty:
        return empty_figure(title)
    figure = px.scatter(
        data,
        x=x,
        y=y,
        color=color,
        size=size,
        hover_name=hover_name,
        title=title,
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    return _finish(figure, height)


def map_chart(data: pd.DataFrame, title: str, height: int = 500) -> go.Figure:
    if data.empty:
        return empty_figure(title, "No geocoded venues for the selected filters")
    figure = px.scatter_mapbox(
        data,
        lat="latitude",
        lon="longitude",
        color="rating",
        size="votes",
        hover_name="name",
        hover_data=["city", "category", "rating", "votes"],
        title=title,
        zoom=1,
        height=height,
        color_continuous_scale="Viridis",
    )
    figure.update_layout(mapbox_style="open-street-map")
    return _finish(figure, height)
