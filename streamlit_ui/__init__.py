"""
Streamlit UI components for PowerBI MCP CLI.

This module provides a web-based chat interface using Streamlit that reuses
the existing backend components (orchestrator, clients, auth, config).
"""

from .session_manager import SessionManager, initialize_session
from .async_runner import AsyncRunner
from .components import (
    render_sidebar,
    render_main_area,
    render_auth_panel,
    render_chat_messages,
)
from .display import (
    format_message_for_display,
    format_tool_result,
    create_error_display,
)

__all__ = [
    "SessionManager",
    "initialize_session",
    "AsyncRunner",
    "render_sidebar",
    "render_main_area",
    "render_auth_panel",
    "render_chat_messages",
    "format_message_for_display",
    "format_tool_result",
    "create_error_display",
]
