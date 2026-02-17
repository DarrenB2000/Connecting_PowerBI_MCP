"""Chart rendering with Altair.

This module creates interactive Altair visualizations from pandas DataFrames.
Phase 1 (MVP) supports bar charts. Future phases will add line, pie, and metric cards.
"""

import altair as alt
import pandas as pd
from .detector import ChartConfig


def create_bar_chart(df: pd.DataFrame, config: ChartConfig) -> alt.Chart:
    """
    Create interactive Altair bar chart.

    Features:
    - Automatic formatting (currency, numbers)
    - Interactive tooltips
    - Color-coded bars
    - Sorted by value (descending)
    - Responsive width

    Args:
        df: pandas DataFrame with data
        config: ChartConfig with chart specifications

    Returns:
        Altair Chart object
    """
    # Determine y-axis formatting
    if config.format_as_currency:
        y_format = '$,.0f'
    else:
        y_format = ',.0f'

    # Create bar chart
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X(
            config.x_column,
            sort='-y',  # Sort by y value (descending)
            axis=alt.Axis(
                labelAngle=-45 if len(df) > 5 else 0,  # Angle labels for many categories
                title=config.x_column
            )
        ),
        y=alt.Y(
            config.y_columns[0],
            axis=alt.Axis(
                format=y_format,
                title=config.y_columns[0]
            )
        ),
        color=alt.Color(
            config.x_column,
            legend=None,  # No legend (x-axis labels are sufficient)
            scale=alt.Scale(scheme=config.color_scheme)
        ),
        tooltip=[
            alt.Tooltip(config.x_column, title=config.x_column),
            alt.Tooltip(
                config.y_columns[0],
                title=config.y_columns[0],
                format=y_format
            )
        ]
    ).properties(
        title=config.title,
        width="container",
        height=400
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14
    ).configure_title(
        fontSize=16,
        anchor='start'
    ).interactive()

    return chart


def create_line_chart(df: pd.DataFrame, config: ChartConfig) -> alt.Chart:
    """
    Create interactive Altair line chart.

    For Phase 2. Currently raises NotImplementedError.

    Args:
        df: pandas DataFrame with data
        config: ChartConfig with chart specifications

    Returns:
        Altair Chart object
    """
    # TODO: Implement in Phase 2
    raise NotImplementedError("Line charts will be implemented in Phase 2")


def create_pie_chart(df: pd.DataFrame, config: ChartConfig) -> alt.Chart:
    """
    Create interactive Altair pie/donut chart using mark_arc().

    Features:
    - Hover tooltips with values and formatting
    - Color legend for categories
    - Responsive width

    Args:
        df: pandas DataFrame with data
        config: ChartConfig with chart specifications

    Returns:
        Altair Chart object
    """
    if config.format_as_currency:
        value_format = '$,.0f'
    elif config.format_as_percentage:
        value_format = '.1f'
    else:
        value_format = ',.2f'

    chart = alt.Chart(df).mark_arc().encode(
        theta=alt.Theta(
            config.y_columns[0],
            type='quantitative'
        ),
        color=alt.Color(
            config.x_column,
            type='nominal',
            legend=alt.Legend(title=config.x_column),
            scale=alt.Scale(scheme=config.color_scheme)
        ),
        tooltip=[
            alt.Tooltip(config.x_column, title=config.x_column),
            alt.Tooltip(
                config.y_columns[0],
                title=config.y_columns[0],
                format=value_format
            )
        ]
    ).properties(
        title=config.title,
        width="container",
        height=400
    ).configure_title(
        fontSize=16,
        anchor='start'
    )

    return chart


def create_metric_card(df: pd.DataFrame, config: ChartConfig) -> alt.Chart:
    """
    Create metric card for single-value display.

    For Phase 2. Currently raises NotImplementedError.

    Args:
        df: pandas DataFrame with data
        config: ChartConfig with chart specifications

    Returns:
        Altair Chart object
    """
    # TODO: Implement in Phase 2
    raise NotImplementedError("Metric cards will be implemented in Phase 2")


def create_chart(df: pd.DataFrame, config: ChartConfig) -> alt.Chart:
    """
    Route to appropriate chart type based on configuration.

    This is the main entry point for chart rendering.

    Args:
        df: pandas DataFrame with data
        config: ChartConfig with chart specifications

    Returns:
        Altair Chart object

    Raises:
        NotImplementedError: For chart types not yet implemented
    """
    if config.chart_type == 'bar':
        return create_bar_chart(df, config)
    elif config.chart_type == 'line':
        return create_line_chart(df, config)
    elif config.chart_type == 'pie':
        return create_pie_chart(df, config)
    elif config.chart_type == 'metric':
        return create_metric_card(df, config)
    else:
        # Default to bar chart for unknown types
        return create_bar_chart(df, config)
