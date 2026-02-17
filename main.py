"""
PowerBI MCP CLI - Main Entry Point

Interactive command-line application for querying PowerBI using Claude AI.
"""
import sys
import asyncio
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import get_settings
from auth import AuthManager
from clients import ClaudeClient, SimpleMCPClient
from core import AgentOrchestrator
from cli import output, run_cli


async def main():
    """Main application entry point."""
    auth_manager = None  # Initialize to None for cleanup in finally block

    try:
        # Load settings
        output.print_info("Loading configuration...")
        settings = get_settings()

        # Create Claude client
        output.print_info(f"Initializing Claude ({settings.claude.model})...")
        claude_client = ClaudeClient(
            api_key=settings.claude.api_key,
            model=settings.claude.model,
            max_tokens=settings.claude.max_tokens,
            temperature=settings.claude.temperature
        )

        # Setup authentication
        output.print_info("Setting up authentication...")
        auth_manager = AuthManager(
            client_id=settings.azure.client_id,
            tenant_id=settings.azure.tenant_id,
            scopes=settings.azure.scopes,
            cache_path=settings.app.token_cache_path
        )

        # Check if already authenticated
        is_cached = auth_manager.is_authenticated()
        if is_cached:
            output.print_auth_status(username="user", cached=True)
        else:
            output.print_auth_status(username=None)

        # Create MCP client
        output.print_info("Connecting to PowerBI MCP server...")
        mcp_client = SimpleMCPClient(
            server_url=settings.powerbi.mcp_url,
            auth_manager=auth_manager
        )

        # Connect to PowerBI MCP server
        async with mcp_client.connect():
            # Get server info and tools
            tools = mcp_client.get_tools()
            output.print_connection_status(
                server_name="PowerBI MCP",
                tool_count=len(tools)
            )

            # Create orchestrator
            output.print_info("Initializing agent orchestrator...")
            orchestrator = AgentOrchestrator(
                claude_client=claude_client,
                mcp_client=mcp_client,
                max_iterations=10
            )

            # Set available tools
            orchestrator.set_tools(tools)

            # Start interactive CLI
            await run_cli(orchestrator)

        return 0

    except KeyboardInterrupt:
        output.print_info("\nInterrupted by user")
        return 0

    except Exception as e:
        output.print_error(
            f"Failed to start application: {e}\n\n"
            "Please check your configuration and try again.\n"
            "Run 'python test_config.py' to verify settings.",
            title="Startup Error"
        )
        import traceback
        output.print_info("\nFull error:")
        traceback.print_exc()
        return 1

    finally:
        # Always logout and clear cached tokens when exiting
        if auth_manager is not None:
            output.print_info("\nCleaning up...")
            auth_manager.logout()


if __name__ == "__main__":
    """
    Usage:
        python main.py

    First run will require browser authentication.
    Subsequent runs use cached tokens.
    """
    sys.exit(asyncio.run(main()))
