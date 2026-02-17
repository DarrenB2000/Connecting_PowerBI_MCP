"""
Session state management for Streamlit app.

Manages initialization and lifecycle of session state variables,
including authentication, MCP connection, and orchestrator.
"""

import streamlit as st
from typing import Optional

from config import get_settings
from auth import AuthManager
from clients import ClaudeClient, SimpleMCPClient
from core import AgentOrchestrator
from streamlit_ui.async_runner import AsyncRunner


class SessionManager:
    """Manages Streamlit session state initialization and lifecycle."""

    @staticmethod
    def initialize():
        """
        Initialize all session state variables.

        This should be called once at the start of the Streamlit app.
        Sets up settings, authentication, clients, and UI state.
        """
        if 'initialized' not in st.session_state:
            # Load settings from config
            settings = get_settings()
            st.session_state.settings = settings

            # Initialize auth manager
            st.session_state.auth_manager = AuthManager(
                client_id=settings.azure.client_id,
                tenant_id=settings.azure.tenant_id,
                scopes=settings.azure.scopes,
                cache_path=settings.app.token_cache_path
            )

            # Check if already authenticated (from cache)
            st.session_state.authenticated = st.session_state.auth_manager.is_authenticated()
            if st.session_state.authenticated:
                st.session_state.username = st.session_state.auth_manager.get_current_user()
            else:
                st.session_state.username = None

            # Initialize Claude client
            st.session_state.claude_client = ClaudeClient(
                api_key=settings.claude.api_key,
                model=settings.claude.model,
                max_tokens=settings.claude.max_tokens,
                temperature=settings.claude.temperature
            )

            # Initialize MCP client (not connected yet)
            st.session_state.mcp_client = SimpleMCPClient(
                server_url=settings.powerbi.mcp_url,
                auth_manager=st.session_state.auth_manager
            )

            # Initialize state variables
            st.session_state.mcp_connected = False
            st.session_state.mcp_connection_context = None
            st.session_state.mcp_connection = None
            st.session_state.available_tools = []
            st.session_state.orchestrator = None
            st.session_state.messages = []
            st.session_state.processing = False
            st.session_state.pending_message = None
            st.session_state.show_debug = False
            st.session_state.device_code_flow = None
            st.session_state.auth_error = None
            st.session_state.connection_error = None

            st.session_state.initialized = True

    @staticmethod
    def connect_mcp():
        """
        Establish MCP connection and store in session state.

        Creates MCP client, establishes connection, discovers tools,
        and initializes orchestrator.
        """
        if st.session_state.mcp_connected:
            return  # Already connected

        # Capture all values from session state BEFORE entering the async thread.
        # The persistent event loop runs in a background thread without Streamlit's
        # ScriptRunContext, so st.session_state is not accessible inside the coroutine.
        mcp_client = st.session_state.mcp_client
        claude_client = st.session_state.claude_client

        async def _connect(mcp_client, claude_client):
            """
            Async connection helper.

            Returns (connection_context, tools) instead of writing to session state,
            because this runs in a background thread without ScriptRunContext.
            """
            # Set manual connection mode to prevent auto-cleanup when loop closes
            mcp_client._manual_connection = True

            # Enter the context manager
            connection_context = mcp_client.connect()
            await connection_context.__aenter__()

            # Get available tools
            tools = mcp_client.get_tools()

            return connection_context, tools

        # Run async connection in the persistent event loop
        runner = AsyncRunner()
        try:
            connection_context, tools = runner.run(_connect(mcp_client, claude_client))

            # Set session state back in the main Streamlit thread (has ScriptRunContext)
            st.session_state.mcp_connection_context = connection_context
            st.session_state.available_tools = tools

            # Create orchestrator synchronously in the main thread
            orchestrator = AgentOrchestrator(
                claude_client=claude_client,
                mcp_client=mcp_client,
                max_iterations=10
            )
            orchestrator.set_tools(tools)
            st.session_state.orchestrator = orchestrator

            # Mark as connected
            st.session_state.mcp_connected = True
            st.session_state.connection_error = None

            # Verify orchestrator was created
            if not st.session_state.get('orchestrator'):
                raise RuntimeError("Orchestrator initialization failed - orchestrator is None after connection")

        except Exception as e:
            # Ensure clean state on failure
            st.session_state.connection_error = str(e)
            st.session_state.mcp_connected = False
            st.session_state.orchestrator = None
            st.session_state.available_tools = []
            raise

    @staticmethod
    def cleanup():
        """Cleanup connections on app shutdown."""
        connection_context = st.session_state.get('mcp_connection_context')
        mcp_client = st.session_state.get('mcp_client')

        if connection_context is not None:
            # Capture references before entering async thread (no ScriptRunContext there)
            async def _cleanup(connection_context, mcp_client):
                """Async cleanup helper."""
                if mcp_client is not None and hasattr(mcp_client, '_manual_connection'):
                    mcp_client._manual_connection = False
                await connection_context.__aexit__(None, None, None)

            runner = AsyncRunner()
            try:
                runner.run(_cleanup(connection_context, mcp_client))
            except Exception:
                pass  # Ignore cleanup errors

            st.session_state.mcp_connection_context = None
            st.session_state.mcp_connected = False


def initialize_session():
    """
    Convenience function to initialize session state.

    Wrapper around SessionManager.initialize() for easier imports.
    """
    SessionManager.initialize()
