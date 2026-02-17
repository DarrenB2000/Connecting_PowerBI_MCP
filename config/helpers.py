"""
Configuration helper utilities for PowerBI MCP CLI.

Provides functions for configuration validation, file generation, and setup.
"""
import json
import os
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .settings import Settings, get_settings


console = Console()


def check_env_file() -> bool:
    """
    Check if .env file exists in the current directory.

    Returns:
        bool: True if .env file exists, False otherwise
    """
    return Path(".env").exists()


def create_env_from_template() -> bool:
    """
    Create .env file from .env.example template if it doesn't exist.

    Returns:
        bool: True if .env was created, False if it already exists
    """
    env_path = Path(".env")
    example_path = Path(".env.example")

    if env_path.exists():
        return False

    if not example_path.exists():
        console.print(
            "[yellow]Warning: .env.example not found. Creating minimal .env file.[/yellow]"
        )
        create_minimal_env_file()
        return True

    # Copy example to .env
    content = example_path.read_text()
    env_path.write_text(content)

    console.print("[green]✓[/green] Created .env file from .env.example")
    console.print(
        "[yellow]Please edit .env and add your CLAUDE_API_KEY[/yellow]"
    )
    return True


def create_minimal_env_file() -> None:
    """Create a minimal .env file with required variables."""
    minimal_content = """# Required: Claude API Key
# Get your API key from: https://console.anthropic.com/
CLAUDE_API_KEY=sk-ant-...

# Optional: Azure App Registration (if not using device code flow)
# AZURE_TENANT_ID=
# AZURE_CLIENT_ID=

# Optional: Custom PowerBI MCP URL
# POWERBI_MCP_URL=https://api.fabric.microsoft.com/v1/mcp/powerbi

# Optional: Logging level
# LOG_LEVEL=INFO
"""
    Path(".env").write_text(minimal_content)


def validate_configuration() -> tuple[bool, list[str]]:
    """
    Validate the current configuration.

    Returns:
        tuple: (is_valid, list of error messages)
    """
    errors = []

    try:
        settings = get_settings()

        # Check Claude API key
        if not settings.claude.api_key or settings.claude.api_key == "sk-ant-...":
            errors.append("CLAUDE_API_KEY is not set or is using the example value")

        # Validate PowerBI URL
        if not settings.powerbi.mcp_url.startswith("https://"):
            errors.append("PowerBI MCP URL must use HTTPS")

        # Check if directories are accessible
        try:
            settings.app.ensure_directories()
        except Exception as e:
            errors.append(f"Cannot create required directories: {e}")

    except Exception as e:
        errors.append(f"Configuration error: {e}")

    return len(errors) == 0, errors


def display_configuration(settings: Optional[Settings] = None) -> None:
    """
    Display current configuration in a formatted table.

    Args:
        settings: Settings instance (if None, loads from environment)
    """
    if settings is None:
        settings = get_settings()

    # Create configuration table
    table = Table(title="PowerBI MCP Configuration", show_header=True)
    table.add_column("Setting", style="cyan", width=30)
    table.add_column("Value", style="white")

    # Claude settings
    table.add_section()
    table.add_row("[bold]Claude API[/bold]", "")
    api_key = settings.claude.api_key
    masked_key = f"{api_key[:10]}...{api_key[-4:]}" if len(api_key) > 14 else "***"
    table.add_row("  API Key", masked_key)
    table.add_row("  Model", settings.claude.model)
    table.add_row("  Max Tokens", str(settings.claude.max_tokens))

    # PowerBI settings
    table.add_section()
    table.add_row("[bold]PowerBI MCP[/bold]", "")
    table.add_row("  Server URL", settings.powerbi.mcp_url)

    # Azure settings
    table.add_section()
    table.add_row("[bold]Azure Authentication[/bold]", "")
    table.add_row(
        "  Tenant ID",
        settings.azure.tenant_id or "[dim]Not set (using common tenant)[/dim]"
    )
    table.add_row(
        "  Client ID",
        settings.azure.client_id or "[dim]Not set (using device code flow)[/dim]"
    )
    table.add_row(
        "  Auth Flow",
        "Device Code Flow" if settings.azure.use_device_code_flow else "App Registration"
    )

    # App settings
    table.add_section()
    table.add_row("[bold]Application[/bold]", "")
    table.add_row("  Token Cache", str(settings.app.token_cache_path))
    table.add_row("  Log Level", settings.app.log_level)
    table.add_row(
        "  Log File",
        str(settings.app.log_file) if settings.app.log_file else "[dim]Console only[/dim]"
    )

    console.print(table)


def save_config_to_json(
    settings: Settings,
    filepath: Optional[Path] = None
) -> Path:
    """
    Save configuration to a JSON file.

    Args:
        settings: Settings instance to save
        filepath: Path to save to (default: ~/.powerbi-mcp/config.json)

    Returns:
        Path: Path where config was saved
    """
    if filepath is None:
        filepath = settings.app.token_cache_dir / "config.json"

    # Ensure directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Get safe dump (with masked API key)
    config_data = settings.model_dump_json_safe()

    # Write to file
    with open(filepath, "w") as f:
        json.dump(config_data, f, indent=2)

    return filepath


def load_config_from_json(filepath: Path) -> dict:
    """
    Load configuration from a JSON file.

    Args:
        filepath: Path to config file

    Returns:
        dict: Configuration data
    """
    if not filepath.exists():
        raise FileNotFoundError(f"Config file not found: {filepath}")

    with open(filepath, "r") as f:
        return json.load(f)


def interactive_setup() -> Settings:
    """
    Interactive setup wizard for first-time configuration.

    Returns:
        Settings: Configured settings instance
    """
    console.print(
        Panel.fit(
            "[bold cyan]PowerBI MCP CLI - Configuration Setup[/bold cyan]\n"
            "This wizard will help you set up your environment.",
            border_style="cyan"
        )
    )

    # Check for .env file
    if not check_env_file():
        console.print("\n[yellow]No .env file found.[/yellow]")
        create_env_from_template()

    # Get Claude API key
    console.print("\n[bold]Step 1: Claude API Configuration[/bold]")
    current_key = os.getenv("CLAUDE_API_KEY", "")

    if current_key and current_key != "sk-ant-...":
        console.print(f"[green]✓[/green] Claude API key found: {current_key[:10]}...")
    else:
        console.print(
            "[yellow]Please set your CLAUDE_API_KEY in the .env file.[/yellow]\n"
            "Get your API key from: https://console.anthropic.com/"
        )
        console.print(
            "\n[dim]Edit .env and add: CLAUDE_API_KEY=sk-ant-your-key-here[/dim]"
        )

    # Azure configuration
    console.print("\n[bold]Step 2: Azure Authentication[/bold]")
    console.print(
        "For device code flow (recommended), you can leave Azure settings empty.\n"
        "For custom app registration, set AZURE_TENANT_ID and AZURE_CLIENT_ID in .env"
    )

    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")

    if tenant_id and client_id:
        console.print("[green]✓[/green] Azure app registration configured")
    else:
        console.print(
            "[blue]ℹ[/blue]  Will use device code flow with common tenant"
        )

    # Validate configuration
    console.print("\n[bold]Step 3: Validation[/bold]")
    is_valid, errors = validate_configuration()

    if is_valid:
        console.print("[green]✓ Configuration is valid![/green]")
        settings = get_settings()
        display_configuration(settings)
        return settings
    else:
        console.print("[red]✗ Configuration has errors:[/red]")
        for error in errors:
            console.print(f"  [red]•[/red] {error}")
        console.print(
            "\n[yellow]Please fix the errors in your .env file and try again.[/yellow]"
        )
        raise ValueError("Invalid configuration")


def get_or_create_settings() -> Settings:
    """
    Get existing settings or run interactive setup if configuration is invalid.

    Returns:
        Settings: Configured settings instance
    """
    # Check if .env exists
    if not check_env_file():
        console.print(
            "[yellow]No .env file found. Running setup wizard...[/yellow]\n"
        )
        return interactive_setup()

    # Try to load settings
    try:
        settings = get_settings()

        # Validate
        is_valid, errors = validate_configuration()
        if not is_valid:
            console.print("[yellow]Configuration errors detected:[/yellow]")
            for error in errors:
                console.print(f"  [red]•[/red] {error}")
            console.print("\n[yellow]Running setup wizard...[/yellow]\n")
            return interactive_setup()

        return settings

    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        console.print("\n[yellow]Running setup wizard...[/yellow]\n")
        return interactive_setup()
