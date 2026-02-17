"""
Simple test script to verify configuration setup.

This script tests the configuration system without requiring all dependencies.
Run: python test_config.py
"""
import sys
from pathlib import Path

# Ensure we can import from config
sys.path.insert(0, str(Path(__file__).parent))

try:
    from config import (
        check_env_file,
        create_env_from_template,
        validate_configuration,
        display_configuration,
        get_or_create_settings,
    )
    from rich.console import Console

    console = Console()

    def main():
        """Test configuration setup."""
        console.print("[bold cyan]PowerBI MCP Configuration Test[/bold cyan]\n")

        # Check for .env file
        console.print("[bold]1. Checking for .env file...[/bold]")
        if check_env_file():
            console.print("[green]✓[/green] .env file exists")
        else:
            console.print("[yellow]⚠[/yellow] .env file not found")
            console.print("Creating from template...")
            create_env_from_template()

        # Validate configuration
        console.print("\n[bold]2. Validating configuration...[/bold]")
        is_valid, errors = validate_configuration()

        if is_valid:
            console.print("[green]✓[/green] Configuration is valid")
        else:
            console.print("[red]✗[/red] Configuration has errors:")
            for error in errors:
                console.print(f"   • {error}")

        # Display configuration
        console.print("\n[bold]3. Current configuration:[/bold]")
        try:
            settings = get_or_create_settings()
            display_configuration(settings)

            console.print(
                f"\n[green]✓[/green] Configuration loaded successfully!"
            )
            console.print(
                f"\n[dim]Token cache directory: {settings.app.token_cache_dir}[/dim]"
            )

        except Exception as e:
            console.print(f"[red]Error loading configuration: {e}[/red]")
            console.print(
                "\n[yellow]Please update your .env file with valid values:[/yellow]"
            )
            console.print("  • CLAUDE_API_KEY=sk-ant-your-key-here")
            return 1

        return 0

    if __name__ == "__main__":
        sys.exit(main())

except ImportError as e:
    print(f"Import error: {e}")
    print("\nMissing dependencies. Install with:")
    print("  pip install -r requirements.txt")
    sys.exit(1)
