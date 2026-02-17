"""
Streamlit Chat Interface for PowerBI MCP CLI

Run with: streamlit run streamlit_app.py

This provides a browser-based chat interface that reuses all existing
backend components (orchestrator, clients, auth) from the CLI version.
"""

import streamlit as st
from streamlit_ui import (
    SessionManager,
    AsyncRunner,
    render_sidebar,
    render_main_area,
    format_message_for_display,
    create_error_display,
)


def process_pending_message():
    """
    Process pending user message through orchestrator.

    This is called after the user message has been displayed.
    """
    if 'pending_message' not in st.session_state or not st.session_state.pending_message:
        return

    # Check if orchestrator is available (connection must be established)
    if not st.session_state.get('orchestrator'):
        st.error("❌ Connection not established. Please wait for MCP connection to complete.")
        st.session_state.pending_message = None
        st.session_state.processing = False
        st.rerun()
        return

    message = st.session_state.pending_message
    st.session_state.pending_message = None  # Clear immediately

    # CRITICAL: Capture orchestrator reference BEFORE threading
    # Background threads cannot access st.session_state (missing ScriptRunContext)
    orchestrator = st.session_state.orchestrator

    # Set processing state
    st.session_state.processing = True

    try:
        import time
        import threading

        # Create UI elements for progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Shared state for thread communication
        query_state = {
            'done': False,
            'result': None,
            'error': None,
            'start_time': time.time()
        }

        def run_query_background():
            """Background thread to execute the query."""
            try:
                runner = AsyncRunner()
                # Use captured orchestrator reference, NOT st.session_state
                result = runner.run(
                    orchestrator.run_conversation_turn(message)
                )
                query_state['result'] = result
            except Exception as e:
                query_state['error'] = e
            finally:
                query_state['done'] = True

        # Start background thread
        thread = threading.Thread(target=run_query_background, daemon=True)
        thread.start()

        # Progress stages (percent, message)
        stages = [
            (10, "🚀 Initializing request..."),
            (25, "🤖 Sending message to Claude..."),
            (40, "⏳ Waiting for response..."),
            (55, "🔄 Processing request..."),
            (70, "🔧 Executing PowerBI tools..."),
            (85, "📥 Receiving response...")
        ]

        current_stage = 0

        # Update progress while query is running
        while not query_state['done']:
            if current_stage < len(stages):
                percent, msg = stages[current_stage]
                progress_bar.progress(percent)
                status_text.text(msg)
                time.sleep(0.5)  # Pause between stages
                current_stage += 1
            else:
                # Keep last message visible
                time.sleep(0.2)

        # Query complete - show 100%
        progress_bar.progress(100)
        elapsed = time.time() - query_state['start_time']
        status_text.text(f"✅ Complete in {elapsed:.1f}s")

        # Small delay to show completion
        time.sleep(0.5)

        # Check for errors
        if query_state['error']:
            raise query_state['error']

        # Get result
        response = query_state['result']

        # Add tool execution messages (if any tools were executed)
        if hasattr(orchestrator, 'last_tool_executions'):
            for tool_exec in orchestrator.last_tool_executions:
                from streamlit_ui.display import format_tool_result
                tool_msg = format_tool_result(
                    tool_name=tool_exec['name'],
                    result=tool_exec.get('result') or tool_exec.get('error'),
                    status=tool_exec['status']
                )
                # Store the user query so the chart renderer can respect
                # explicit chart type requests (e.g. "show as pie chart")
                tool_msg['user_query'] = message
                st.session_state.messages.append(tool_msg)

        # Add assistant response to display
        st.session_state.messages.append(
            format_message_for_display('assistant', response)
        )

        # Store elapsed time to display at bottom
        st.session_state.last_query_time = elapsed

    except Exception as e:
        # Display error
        create_error_display(e)
        st.session_state.messages.append({
            'type': 'error',
            'content': str(e)
        })

    finally:
        st.session_state.processing = False
        # Rerun to display the response
        st.rerun()


def main():
    """Main application entry point."""

    # Page configuration
    st.set_page_config(
        page_title="PowerBI MCP Assistant",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize session state
    SessionManager.initialize()

    # Connect to MCP if authenticated
    if st.session_state.authenticated and not st.session_state.mcp_connected:
        with st.spinner("Connecting to PowerBI MCP server..."):
            try:
                SessionManager.connect_mcp()
                # Verify orchestrator was created
                if not st.session_state.get('orchestrator'):
                    st.warning("⚠️ Connection established but orchestrator not initialized. Please refresh the page.")
            except Exception as e:
                st.error(f"Failed to connect to MCP server: {e}")
                st.session_state.mcp_connected = False
                st.session_state.orchestrator = None
                if st.session_state.show_debug:
                    st.exception(e)

    # Render UI
    render_sidebar()
    render_main_area()

    # Process pending message if any (after UI is rendered so message is visible)
    process_pending_message()


if __name__ == "__main__":
    main()
