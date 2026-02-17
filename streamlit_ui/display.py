"""
Display utilities for formatting messages and results.

Provides functions to format messages, tool results, and errors
for display in the Streamlit UI.
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Any, Optional


def format_message_for_display(role: str, content: str) -> Dict[str, Any]:
    """
    Convert orchestrator message to display format.

    Args:
        role: Message role ('user' or 'assistant')
        content: Message content

    Returns:
        Dict with display format: {type, content, timestamp}
    """
    return {
        'type': 'user' if role == 'user' else 'assistant',
        'content': content,
        'timestamp': datetime.now()
    }


def format_tool_result(
    tool_name: str,
    result: Any,
    status: str
) -> Dict[str, Any]:
    """
    Format tool execution result for display.

    Args:
        tool_name: Name of the tool that was executed
        result: Tool execution result or error
        status: 'success' or 'error'

    Returns:
        Dict with display format for tool execution
    """
    return {
        'type': 'tool',
        'name': tool_name,
        'status': status,
        'result': result if status == 'success' else None,
        'error': result if status == 'error' else None,
        'timestamp': datetime.now()
    }


def create_error_display(error: Exception) -> None:
    """
    Display error with proper formatting.

    Shows error message and optional debug details if debug mode enabled.

    Args:
        error: Exception to display
    """
    st.error(f"❌ Error: {str(error)}")

    if st.session_state.get('show_debug', False):
        with st.expander("Debug Details"):
            st.exception(error)
