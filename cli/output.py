"""
CLI output formatting utilities.

Provides rich terminal formatting for the PowerBI MCP CLI.
"""
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text


console = Console()


def print_welcome():
    """Display welcome message with branding."""
    welcome_text = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║           🤖 PowerBI MCP Assistant                        ║
║           Powered by Claude                               ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

    Chat naturally with your PowerBI data using AI.

    Commands:
      • Type your question and press Enter
      • /clear    - Clear conversation history
      • /help     - Show help
      • /exit     - Exit application (or Ctrl+C)
"""
    console.print(welcome_text, style="cyan")


def print_auth_status(username: Optional[str] = None, cached: bool = False):
    """
    Display authentication status.

    Args:
        username: Authenticated username
        cached: Whether auth was from cache
    """
    if username:
        status = "✅ Authenticated"
        if cached:
            status += " (cached)"
        console.print(f"{status} as: [bold]{username}[/bold]")
    else:
        console.print("🔐 Authentication required", style="yellow")


def print_connection_status(server_name: Optional[str] = None, tool_count: int = 0):
    """
    Display MCP connection status.

    Args:
        server_name: MCP server name
        tool_count: Number of discovered tools
    """
    if server_name:
        console.print(f"🔌 Connected to: [bold]{server_name}[/bold]")
        console.print(f"📦 Available tools: [bold]{tool_count}[/bold]")
    else:
        console.print("⚠️  Not connected to MCP server", style="yellow")


def print_ready():
    """Display ready status."""
    console.print("\n✨ Ready to help with PowerBI queries!\n", style="bold green")


def print_user_message(message: str):
    """
    Display user message.

    Args:
        message: User's message
    """
    console.print(
        Panel(
            Text(message, style="white"),
            title="👤 You",
            border_style="blue",
            padding=(0, 2)
        )
    )


def print_assistant_message(message: str):
    """
    Display assistant message with markdown formatting.

    Args:
        message: Assistant's response
    """
    console.print(
        Panel(
            Markdown(message),
            title="🤖 Claude",
            border_style="green",
            padding=(1, 2)
        )
    )


def print_tool_execution(tool_name: str, status: str = "running"):
    """
    Display tool execution status.

    Args:
        tool_name: Name of tool being executed
        status: Status (running, success, error)
    """
    if status == "running":
        console.print(f"[cyan]  → Executing: {tool_name}...[/cyan]")
    elif status == "success":
        console.print(f"[green]  ✓ {tool_name} completed[/green]")
    elif status == "error":
        console.print(f"[red]  ✗ {tool_name} failed[/red]")


def print_error(message: str, title: str = "Error"):
    """
    Display error message.

    Args:
        message: Error message
        title: Error panel title
    """
    console.print(
        Panel(
            Text(message, style="red"),
            title=f"❌ {title}",
            border_style="red",
            padding=(1, 2)
        )
    )


def print_warning(message: str):
    """
    Display warning message.

    Args:
        message: Warning message
    """
    console.print(f"[yellow]⚠️  {message}[/yellow]")


def print_info(message: str):
    """
    Display info message.

    Args:
        message: Info message
    """
    console.print(f"[dim]{message}[/dim]")


def print_help():
    """Display help information."""
    help_text = """
# PowerBI MCP Assistant Help

## Available Commands

- `/clear` - Clear conversation history and start fresh
- `/help` - Show this help message
- `/exit` - Exit the application

## Usage Tips

1. **Ask questions naturally**:
   - "Show me all my datasets"
   - "What reports are in my workspace?"

2. **Request data**:
   - "Query the Sales dataset for last month's revenue"
   - "Get the schema for the Customer dataset"

3. **Explore**:
   - "What can you help me with?"
   - "List available workspaces"

## Examples

```
You: Show me all datasets in my workspace

Claude will use PowerBI tools to fetch and display your datasets.
```

```
You: Tell me about the Sales Dashboard dataset

Claude will retrieve details about that specific dataset.
```

## Authentication

- First run requires browser authentication (device code flow)
- Subsequent runs use cached tokens
- Tokens auto-refresh when expired
"""
    console.print(Panel(Markdown(help_text), border_style="cyan", padding=(1, 2)))


def print_tools_table(tools: list):
    """
    Display available tools in a table.

    Args:
        tools: List of tool definitions
    """
    if not tools:
        console.print("[yellow]No tools available[/yellow]")
        return

    table = Table(
        title=f"Available PowerBI Tools ({len(tools)})",
        show_header=True,
        header_style="bold cyan"
    )

    table.add_column("No", style="cyan", width=4)
    table.add_column("Tool Name", style="green", width=30)
    table.add_column("Description", style="white")

    for i, tool in enumerate(tools, 1):
        table.add_row(
            str(i),
            tool.get("name", "Unknown"),
            tool.get("description", "No description")[:60]
        )

    console.print(table)


def print_separator():
    """Print a separator line."""
    console.print("─" * 60, style="dim")


def print_thinking():
    """Display thinking indicator."""
    console.print("[dim]🤔 Thinking...[/dim]")


def clear_screen():
    """Clear the console screen."""
    console.clear()
