"""
CLI Interface - Interactive REPL for PowerBI MCP Assistant.

Provides prompt-toolkit based REPL for conversational interaction.
"""
import asyncio
from typing import Optional
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style

from core import AgentOrchestrator
from . import output


# Custom prompt style
prompt_style = Style.from_dict({
    'prompt': '#00aa00 bold',
})


class PowerBICLI:
    """
    Interactive CLI for PowerBI MCP Assistant.

    Manages REPL session and command handling.
    """

    def __init__(self, orchestrator: AgentOrchestrator):
        """
        Initialize CLI.

        Args:
            orchestrator: Agent orchestrator instance
        """
        self.orchestrator = orchestrator
        self.session: Optional[PromptSession] = None
        self.running = False

    async def start(self):
        """Start interactive REPL session."""
        # Create prompt session with history
        self.session = PromptSession(
            history=InMemoryHistory(),
            style=prompt_style
        )

        # Display welcome
        output.print_welcome()
        output.print_ready()

        self.running = True

        # Main REPL loop
        while self.running:
            try:
                # Get user input
                user_input = await self.session.prompt_async(
                    "You: ",
                    style=prompt_style
                )

                # Skip empty input
                if not user_input.strip():
                    continue

                # Handle commands
                if user_input.startswith('/'):
                    await self.handle_command(user_input)
                    continue

                # Process message with orchestrator
                await self.process_message(user_input)

            except KeyboardInterrupt:
                # Handle Ctrl+C gracefully
                if await self.confirm_exit():
                    break
                continue

            except EOFError:
                # Handle Ctrl+D
                break

            except Exception as e:
                output.print_error(f"Unexpected error: {e}")
                continue

        # Cleanup
        await self.stop()

    async def process_message(self, message: str):
        """
        Process user message through orchestrator.

        Args:
            message: User's message
        """
        try:
            # Display user message
            output.print_user_message(message)

            # Show thinking indicator
            output.print_thinking()

            # Run conversation turn
            response = await self.orchestrator.run_conversation_turn(message)

            # Display response
            if response:
                output.print_assistant_message(response)
            else:
                output.print_warning("No response received from Claude")

            # Print separator
            print()  # Empty line for spacing

        except Exception as e:
            output.print_error(
                f"Error processing message: {e}",
                title="Processing Error"
            )

    async def handle_command(self, command: str):
        """
        Handle special commands.

        Args:
            command: Command string starting with /
        """
        cmd = command.lower().strip()

        if cmd in ['/exit', '/quit', '/q']:
            self.running = False
            output.print_info("Goodbye! 👋")

        elif cmd == '/clear':
            self.orchestrator.clear_history()
            output.clear_screen()
            output.print_welcome()
            output.print_info("Conversation history cleared")
            output.print_ready()

        elif cmd == '/help':
            output.print_help()

        elif cmd == '/tools':
            # Display available tools
            tools = self.orchestrator._mcp_tools
            output.print_tools_table(tools)

        elif cmd == '/history':
            # Show conversation history length
            length = self.orchestrator.get_history_length()
            output.print_info(f"Conversation history: {length} messages")

        else:
            output.print_warning(f"Unknown command: {command}")
            output.print_info("Type /help for available commands")

    async def confirm_exit(self) -> bool:
        """
        Confirm exit with user.

        Returns:
            True if user confirms exit
        """
        try:
            response = await self.session.prompt_async(
                "\nAre you sure you want to exit? (y/n): "
            )
            return response.lower().strip() in ['y', 'yes']
        except:
            return True

    async def stop(self):
        """Stop CLI and cleanup."""
        self.running = False
        output.print_info("Session ended")


async def run_cli(orchestrator: AgentOrchestrator):
    """
    Run interactive CLI session.

    Args:
        orchestrator: Configured agent orchestrator

    Example:
        >>> async with mcp_client.connect():
        ...     orchestrator = AgentOrchestrator(claude_client, mcp_client)
        ...     orchestrator.set_tools(mcp_client.get_tools())
        ...     await run_cli(orchestrator)
    """
    cli = PowerBICLI(orchestrator)
    await cli.start()
