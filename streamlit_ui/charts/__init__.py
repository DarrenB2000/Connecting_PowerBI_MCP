"""Chart visualization module for PowerBI MCP Streamlit interface.

This module provides automatic chart detection and rendering for PowerBI tool results.
Charts are rendered inline in the chat interface using Altair.
"""

from .detector import detect_chart_opportunity, extract_rows_from_result, ChartConfig
from .transformers import rows_to_dataframe, validate_dataframe
from .renderer import create_chart

__all__ = [
    'detect_chart_opportunity',
    'extract_rows_from_result',
    'rows_to_dataframe',
    'validate_dataframe',
    'create_chart',
    'ChartConfig'
]
