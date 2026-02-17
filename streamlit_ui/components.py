"""
Streamlit UI components.

Provides reusable UI components for the PowerBI MCP chat interface,
including sidebar, authentication panel, chat display, and controls.
"""

import streamlit as st
import time
import json
from typing import Optional, Dict, Any
from datetime import datetime


def render_sidebar():
    """
    Render complete sidebar with all panels.

    Includes authentication, connection status, settings, and tools.
    """
    with st.sidebar:
        st.title("PowerBI MCP Assistant")

        # Authentication panel
        render_auth_panel()

        st.divider()

        # Connection status
        render_connection_status()

        st.divider()

        # Settings
        render_settings_panel()

        st.divider()

        # Tools
        render_tools_panel()


def render_auth_panel():
    """
    Render authentication panel in sidebar.

    Handles 4 states:
    - Not authenticated
    - Authenticating (device code flow)
    - Authenticated
    - Error
    """
    st.header("🔐 Authentication")

    # Check authentication state
    authenticated = st.session_state.get('authenticated', False)
    auth_error = st.session_state.get('auth_error')
    device_code_flow = st.session_state.get('device_code_flow')

    # State 1: Authenticated
    if authenticated:
        username = st.session_state.get('username', 'Unknown User')
        st.success(f"✅ Authenticated")
        st.text(f"User: {username}")

        if st.button("🚪 Logout", use_container_width=True):
            # Perform logout
            try:
                st.session_state.auth_manager.logout()
                st.session_state.authenticated = False
                st.session_state.username = None
                st.session_state.mcp_connected = False
                st.session_state.orchestrator = None
                st.session_state.messages = []
                st.success("Logged out successfully")
                st.rerun()
            except Exception as e:
                st.error(f"Logout failed: {e}")

    # State 2: Authenticating (device code flow in progress)
    elif device_code_flow is not None:
        st.info("🔄 Authentication in Progress")

        flow = device_code_flow
        st.markdown("**1. Visit the URL below:**")
        st.code(flow.get('verification_uri', 'N/A'), language=None)

        st.markdown("**2. Enter this code:**")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.code(flow.get('user_code', 'N/A'), language=None)
        with col2:
            if st.button("📋", help="Copy code"):
                st.toast("Code copied! (Use Ctrl+C from the code box)")

        st.caption("⏳ Waiting for authentication...")

        # Poll for authentication completion
        try:
            result = st.session_state.auth_manager.app.acquire_token_by_device_flow(
                flow,
                claims_challenge=None,
                timeout=1  # Non-blocking check
            )

            if "access_token" in result:
                # Authentication successful - cache token
                st.session_state.auth_manager._cache_token_result(result)

                # Extract user info
                username = None
                if "id_token_claims" in result:
                    claims = result["id_token_claims"]
                    username = claims.get("preferred_username") or claims.get("email")
                    st.session_state.auth_manager._current_user = username

                st.session_state.authenticated = True
                st.session_state.username = username or "Unknown User"
                st.session_state.device_code_flow = None
                st.session_state.auth_error = None
                st.success("✅ Authentication successful!")
                time.sleep(1)
                st.rerun()
            elif "error" in result:
                # Check if still pending
                if result["error"] == "authorization_pending":
                    # Still waiting - auto-refresh
                    time.sleep(2)
                    st.rerun()
                else:
                    # Error occurred
                    st.session_state.auth_error = result.get('error_description', 'Unknown error')
                    st.session_state.device_code_flow = None
                    st.rerun()
        except Exception as e:
            st.session_state.auth_error = str(e)
            st.session_state.device_code_flow = None
            st.rerun()

    # State 3: Error state
    elif auth_error is not None:
        st.error("❌ Authentication Error")
        st.text(auth_error)

        if st.button("🔄 Try Again", use_container_width=True):
            st.session_state.auth_error = None
            st.rerun()

    # State 4: Not authenticated
    else:
        st.info("Please authenticate to continue")

        if st.button("🔑 Login with Microsoft", use_container_width=True):
            # Initiate device code flow
            try:
                # Use MSAL app directly to initiate device flow
                flow = st.session_state.auth_manager.app.initiate_device_flow(
                    scopes=st.session_state.auth_manager.scopes
                )

                if "user_code" not in flow:
                    raise Exception(
                        f"Failed to initiate device code flow: {flow.get('error_description', 'Unknown error')}"
                    )

                st.session_state.device_code_flow = flow
                st.rerun()
            except Exception as e:
                st.session_state.auth_error = f"Failed to initiate login: {e}"
                st.rerun()


def render_connection_status():
    """Show MCP connection status."""
    st.header("🔌 MCP Server")

    mcp_connected = st.session_state.get('mcp_connected', False)
    connection_error = st.session_state.get('connection_error')

    if mcp_connected:
        st.success("✅ Connected")

        # Show tool count
        tools = st.session_state.get('available_tools', [])
        tool_count = len(tools)
        st.metric("Available Tools", tool_count)

    elif connection_error:
        st.error("❌ Connection Failed")
        with st.expander("Error Details"):
            st.text(connection_error)

        if st.button("🔄 Retry Connection", use_container_width=True):
            st.session_state.connection_error = None
            st.rerun()

    else:
        st.warning("⚠️ Not Connected")
        st.caption("Authenticate to connect")


def render_settings_panel():
    """Display current settings and controls."""
    with st.expander("⚙️ Settings"):
        settings = st.session_state.get('settings')

        if settings:
            st.text(f"Model: {settings.claude.model}")
            st.text(f"Max Tokens: {settings.claude.max_tokens}")
            st.text(f"Temperature: {settings.claude.temperature}")

            st.divider()

            # Debug toggle
            show_debug = st.checkbox(
                "Show Debug Info",
                value=st.session_state.get('show_debug', False),
                help="Display detailed debug information"
            )
            st.session_state.show_debug = show_debug

            st.divider()

            # Clear conversation button
            if st.button("🗑️ Clear Conversation", use_container_width=True):
                st.session_state.messages = []
                if st.session_state.get('orchestrator'):
                    st.session_state.orchestrator.conversation_history = []
                st.success("Conversation cleared")
                st.rerun()
        else:
            st.text("Settings not loaded")


def render_tools_panel():
    """Display available tools."""
    tools = st.session_state.get('available_tools', [])

    with st.expander(f"🔧 Tools ({len(tools)})"):
        if tools:
            for tool in tools:
                st.markdown(f"**{tool.get('name', 'Unknown')}**")
                description = tool.get('description', 'No description available')
                st.caption(description)
                st.divider()
        else:
            st.text("No tools available")
            st.caption("Connect to MCP server to see available tools")


def render_main_area():
    """
    Render main chat area.

    Includes title, welcome message, chat history, and input.
    """
    st.title("💬 PowerBI Chat Assistant")

    # Check authentication and connection status
    authenticated = st.session_state.get('authenticated', False)
    mcp_connected = st.session_state.get('mcp_connected', False)
    messages = st.session_state.get('messages', [])

    # Display appropriate welcome message based on state
    if not authenticated:
        st.info("👈 Please authenticate in the sidebar to start chatting")
        st.markdown("""
        ### Welcome to PowerBI MCP Assistant!

        This assistant helps you interact with your PowerBI Semantic Models using natural language.

        **To get started:**
        1. Click "Login with Microsoft" in the sidebar
        2. Follow the device code authentication flow
        3. Start asking questions about your PowerBI data!

        **Example queries:**
        - "Show me the schema for my semantic model"
        - "What tables are available?"
        - "Generate a query to get total revenue by region"
        """)
        return

    elif not mcp_connected:
        st.warning("⚠️ Connecting to PowerBI MCP server...")
        st.caption("This may take a moment...")
        return

    # Check if orchestrator is ready (extra safety check)
    elif not st.session_state.get('orchestrator'):
        st.warning("⚠️ Initializing orchestrator...")
        st.caption("Setting up conversation engine...")
        return

    # Show welcome message if no conversation yet
    if not messages:
        st.success("✅ Connected and ready!")
        st.markdown("""
        ### Ask me anything about your PowerBI data!

        **Example queries:**
        - "Show me the schema"
        - "What measures are available?"
        - "Generate a DAX query for total sales by product category"
        - "Execute a query to get the top 10 customers"
        """)

    # Render messages
    render_chat_messages()

    # Show elapsed time if available
    if st.session_state.get('last_query_time'):
        elapsed = st.session_state.last_query_time
        st.info(f"⏱️ Last query completed in {elapsed:.2f} seconds")

    # Render input
    render_chat_input()


def render_chat_messages():
    """Render message history in main area."""
    messages = st.session_state.get('messages', [])

    for msg_idx, msg in enumerate(messages):
        msg_type = msg.get('type')
        content = msg.get('content', '')
        timestamp = msg.get('timestamp')

        # Format timestamp if available
        time_str = ""
        if timestamp:
            if isinstance(timestamp, datetime):
                time_str = timestamp.strftime("%H:%M:%S")
            else:
                time_str = str(timestamp)

        # Render based on message type
        if msg_type == 'user':
            with st.chat_message("user"):
                st.markdown(content)
                if time_str:
                    st.caption(f"🕐 {time_str}")

        elif msg_type == 'assistant':
            with st.chat_message("assistant"):
                st.markdown(content)
                if time_str:
                    st.caption(f"🕐 {time_str}")

        elif msg_type == 'tool':
            # Tool execution result
            tool_name = msg.get('name', 'Unknown Tool')
            status = msg.get('status', 'unknown')
            result = msg.get('result')
            error = msg.get('error')
            show_debug = st.session_state.get('show_debug', False)

            if status == 'error':
                # Always show tool errors
                with st.chat_message("assistant"):
                    st.error(f"🔧 Tool: {tool_name} - ❌ Error")
                    if error:
                        st.text(error)
                    if time_str:
                        st.caption(f"🕐 {time_str}")

            elif status == 'success':
                # Pre-compute chart so we only open a chat bubble when there's something to show
                chart_obj = None       # Altair chart object (non-metric types)
                chart_df = None
                chart_config = None
                chart_error = None
                is_metric = False      # True when single-value metric card should be shown

                if result:
                    try:
                        from streamlit_ui.charts import (
                            detect_chart_opportunity,
                            extract_rows_from_result,
                            rows_to_dataframe,
                            create_chart
                        )
                        user_query = msg.get('user_query', '')
                        chart_config = detect_chart_opportunity(result, user_query=user_query)
                        if chart_config:
                            rows = extract_rows_from_result(result)
                            chart_df = rows_to_dataframe(rows)
                            if chart_config.chart_type == 'metric':
                                # Metric cards are rendered with st.metric(), not Altair
                                is_metric = True
                            else:
                                chart_obj = create_chart(chart_df, chart_config)
                    except Exception as e:
                        chart_error = e

                # Only render a chat bubble if there is something to show
                has_content = chart_obj is not None or is_metric or chart_error is not None or show_debug
                if has_content:
                    with st.chat_message("assistant"):
                        if is_metric and chart_df is not None:
                            # Render each numeric column as a Streamlit metric card
                            numeric_cols = chart_df.select_dtypes(include=['number']).columns.tolist()
                            cols = st.columns(max(len(numeric_cols), 1))
                            for i, col_name in enumerate(numeric_cols):
                                value = chart_df[col_name].iloc[0]
                                if chart_config.format_as_currency:
                                    formatted = f"${value:,.0f}"
                                elif isinstance(value, float):
                                    formatted = f"{value:,.2f}"
                                else:
                                    formatted = f"{value:,}"
                                cols[i].metric(label=col_name, value=formatted)

                        elif chart_obj is not None:
                            st.altair_chart(chart_obj)

                        if (is_metric or chart_obj is not None) and chart_df is not None:
                            show_table_key = f"show_table_{msg_idx}"
                            if st.checkbox(f"Show data table ({len(chart_df)} rows)", key=show_table_key):
                                st.dataframe(chart_df)

                                csv = chart_df.to_csv(index=False).encode('utf-8')
                                st.download_button(
                                    label="⬇️ Download CSV",
                                    data=csv,
                                    file_name=f"{tool_name}_data.csv",
                                    mime="text/csv",
                                    key=f"download_{msg_idx}"
                                )

                        if chart_error is not None:
                            import traceback
                            st.error(f"❌ Chart rendering error: {chart_error}")
                            if show_debug:
                                st.code(traceback.format_exc())

                        if show_debug:
                            if chart_config is None and result:
                                st.caption("ℹ️ Data not suitable for charting")
                            if result:
                                with st.expander(f"Tool Result: {tool_name} (JSON)"):
                                    if isinstance(result, (dict, list)):
                                        st.json(result)
                                    else:
                                        st.code(str(result))

                        if time_str:
                            st.caption(f"🕐 {time_str}")

        elif msg_type == 'error':
            with st.chat_message("assistant"):
                st.error(f"❌ Error: {content}")
                if time_str:
                    st.caption(f"🕐 {time_str}")


def render_chat_input():
    """Render chat input area."""
    # Check if ready for input
    authenticated = st.session_state.get('authenticated', False)
    mcp_connected = st.session_state.get('mcp_connected', False)
    orchestrator_ready = st.session_state.get('orchestrator') is not None
    processing = st.session_state.get('processing', False)

    # Disable input if not ready or processing
    disabled = not (authenticated and mcp_connected and orchestrator_ready) or processing

    # Chat input
    user_input = st.chat_input(
        "Ask about your PowerBI data...",
        disabled=disabled,
        key="chat_input"
    )

    # Handle message submission
    if user_input:
        # Add user message to display immediately
        from streamlit_ui import format_message_for_display
        st.session_state.messages.append(
            format_message_for_display('user', user_input)
        )
        # Mark message as pending processing
        st.session_state.pending_message = user_input
        # Rerun to show the message and trigger processing
        st.rerun()
