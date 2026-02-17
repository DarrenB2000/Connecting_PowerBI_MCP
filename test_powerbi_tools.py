"""
Test PowerBI MCP Tools Directly

Diagnostic script to test MCP tool calls and troubleshoot schema retrieval issues.

Usage:
    python test_powerbi_tools.py
    python test_powerbi_tools.py --artifact-id <guid>
    python test_powerbi_tools.py -a <guid>
"""
import sys
import asyncio
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from clients import SimpleMCPClient
from auth import AuthManager
from config import get_settings
from rich.console import Console
from rich.panel import Panel
from rich.json import JSON
from rich.table import Table

console = Console()


async def test_tools(artifact_id=None):
    """Test PowerBI MCP tools directly."""
    console.print(
        Panel.fit(
            "[bold cyan]PowerBI MCP Tools Diagnostic Test[/bold cyan]\n\n"
            "This will test each PowerBI tool to identify issues.",
            border_style="cyan"
        )
    )

    try:
        # Load settings
        console.print("\n[bold]Step 1: Loading configuration...[/bold]")
        settings = get_settings()
        console.print("[green]✓[/green] Configuration loaded")

        # Setup auth
        console.print("\n[bold]Step 2: Setting up authentication...[/bold]")
        auth_manager = AuthManager(
            client_id=settings.azure.client_id,
            tenant_id=settings.azure.tenant_id,
            scopes=settings.azure.scopes,
            cache_path=settings.app.token_cache_path
        )

        is_cached = auth_manager.is_authenticated()
        if is_cached:
            console.print("[green]✓[/green] Using cached authentication")
        else:
            console.print("[yellow]![/yellow] Will need to authenticate")

        # Connect to MCP
        console.print("\n[bold]Step 3: Connecting to PowerBI MCP...[/bold]")
        mcp_client = SimpleMCPClient(
            server_url=settings.powerbi.mcp_url,
            auth_manager=auth_manager
        )

        async with mcp_client.connect():
            console.print("[green]✓[/green] Connected to PowerBI MCP")

            # List available tools
            console.print("\n[bold]Step 4: Discovering available tools...[/bold]")
            tools = mcp_client.get_tools()
            console.print(f"[green]✓[/green] Found {len(tools)} tools")

            # Display tools table
            table = Table(title="Available PowerBI Tools", show_header=True)
            table.add_column("No", style="cyan", width=4)
            table.add_column("Name", style="green", width=30)
            table.add_column("Description", style="white")
            table.add_column("Has Schema", style="yellow", width=12)

            for i, tool in enumerate(tools, 1):
                has_schema = "✓" if tool.get("inputSchema") else "✗"
                table.add_row(
                    str(i),
                    tool.get("name", "Unknown"),
                    tool.get("description", "No description")[:50],
                    has_schema
                )

            console.print(table)

            # Test specific artifact if ID provided
            if artifact_id:
                console.print("\n[bold]Step 5: Testing specific artifact...[/bold]")
                console.print(f"  Artifact ID (GUID): [cyan]{artifact_id}[/cyan]\n")

                # Simple DAX query for testing ExecuteQuery
                test_dax_query = """EVALUATE
ROW(
    "Total Revenue", [Total Revenue],
    "Total Units Sold", [Total Units Sold]
)"""

                # Natural language query and schema selection for GenerateQuery
                test_user_input = "What is the total revenue by product category?"

                # Try simplified schema selection with lowercase keys and string arrays
                test_schema_selection = {
                    "tables": [
                        {
                            "name": "Machine Tools Products",
                            "columns": ["Product Category"]
                        }
                    ],
                    "measures": ["Total Revenue"]
                }

                # Find GetSemanticModelSchema tool
                schema_tool = next((t for t in tools if t.get("name") == "GetSemanticModelSchema"), None)

                if schema_tool:
                    console.print("[cyan]Testing: GetSemanticModelSchema[/cyan]")
                    console.print("─" * 60)

                    # Show what parameters the tool expects
                    input_schema = schema_tool.get("inputSchema", {})
                    properties = input_schema.get("properties", {})
                    required = input_schema.get("required", [])

                    console.print(f"  Tool expects parameters:")
                    for param_name, param_info in properties.items():
                        req_marker = "[red]*[/red]" if param_name in required else " "
                        param_type = param_info.get("type", "unknown")
                        param_desc = param_info.get("description", "No description")
                        console.print(f"    {req_marker} {param_name} ({param_type}): {param_desc}")

                    console.print(f"\n  Calling with artifact ID as parameter...\n")

                    try:
                        # Try calling with artifact ID - will use the first parameter name found
                        param_name = list(properties.keys())[0] if properties else "artifactId"

                        result = await mcp_client.call_tool(
                            name="GetSemanticModelSchema",
                            arguments={
                                param_name: artifact_id
                            }
                        )

                        console.print("[green]✓[/green] Schema retrieved successfully!")
                        console.print(f"\nResult type: {type(result).__name__}")

                        # Display schema
                        if result:
                            try:
                                if isinstance(result, str):
                                    # Try to parse as JSON
                                    try:
                                        result_json = json.loads(result)
                                        console.print("\n[bold]Schema Data:[/bold]")
                                        console.print(JSON(json.dumps(result_json, indent=2)))

                                        # Try to extract useful info
                                        if isinstance(result_json, dict):
                                            if "tables" in result_json:
                                                console.print(f"\n[green]Found {len(result_json['tables'])} tables in schema[/green]")
                                            if "model" in result_json:
                                                console.print(f"Model info: {result_json.get('model', {}).get('name', 'Unknown')}")
                                    except json.JSONDecodeError:
                                        # Not JSON, display as string
                                        console.print("\n[bold]Schema Data (text):[/bold]")
                                        console.print(result[:2000])  # First 2000 chars
                                        if len(result) > 2000:
                                            console.print(f"\n[dim]... ({len(result) - 2000} more characters)[/dim]")
                                elif isinstance(result, dict):
                                    console.print("\n[bold]Schema Data:[/bold]")
                                    console.print(JSON(json.dumps(result, indent=2)))
                                else:
                                    console.print(f"\n{result}")
                            except Exception as e:
                                console.print(f"[yellow]Could not format result: {e}[/yellow]")
                                console.print(f"Raw result: {result}")
                        else:
                            console.print("[yellow]![/yellow] No schema data returned")

                    except Exception as e:
                        console.print(f"[red]✗[/red] Error: {e}")
                        console.print("\n[yellow]Troubleshooting tips:[/yellow]")
                        console.print("  1. Verify the artifact GUID is correct")
                        console.print("  2. Check you have access to this artifact in PowerBI portal")
                        console.print("  3. Ensure the semantic model exists and is published")
                        console.print("  4. Verify Azure app has Dataset.Read.All permission")
                        console.print("  5. Try listing available artifacts first")

                    console.print("\n" + "=" * 60)

                else:
                    console.print("[red]GetSemanticModelSchema tool not found![/red]")

                # Test ExecuteQuery with simple DAX
                console.print("\n[bold]Step 5b: Testing ExecuteQuery with sample DAX...[/bold]\n")

                execute_tool = next((t for t in tools if t.get("name") == "ExecuteQuery"), None)

                if execute_tool:
                    console.print("[cyan]Testing: ExecuteQuery[/cyan]")
                    console.print("─" * 60)

                    console.print("  DAX Query:")
                    console.print(f"[dim]{test_dax_query}[/dim]\n")

                    try:
                        result = await mcp_client.call_tool(
                            name="ExecuteQuery",
                            arguments={
                                "artifactId": artifact_id,
                                "daxQuery": test_dax_query
                            }
                        )

                        console.print("[green]✓[/green] Query executed successfully!")
                        console.print(f"\nResult type: {type(result).__name__}")

                        # Display result
                        if result:
                            try:
                                if isinstance(result, str):
                                    try:
                                        result_json = json.loads(result)
                                        console.print("\n[bold]Query Results:[/bold]")
                                        console.print(JSON(json.dumps(result_json, indent=2)))
                                    except json.JSONDecodeError:
                                        console.print("\n[bold]Query Results (text):[/bold]")
                                        console.print(result[:2000])
                                elif isinstance(result, dict):
                                    console.print("\n[bold]Query Results:[/bold]")
                                    console.print(JSON(json.dumps(result, indent=2)))

                                    # Try to extract structured content
                                    if "structuredContent" in result:
                                        structured = result["structuredContent"]
                                        if "Rows" in structured:
                                            console.print(f"\n[green]✓ Got {len(structured['Rows'])} rows[/green]")
                                            if structured["Rows"]:
                                                console.print("\nFirst row data:")
                                                console.print(JSON(json.dumps(structured["Rows"][0], indent=2)))
                                else:
                                    console.print(f"\n{result}")
                            except Exception as e:
                                console.print(f"[yellow]Could not format result: {e}[/yellow]")
                                console.print(f"Raw result: {result}")
                        else:
                            console.print("[yellow]![/yellow] No query results returned")

                    except Exception as e:
                        console.print(f"[red]✗[/red] Error: {e}")
                        console.print("\n[yellow]Troubleshooting tips:[/yellow]")
                        console.print("  1. Verify the DAX query syntax is correct")
                        console.print("  2. Check that the measures exist in the semantic model")
                        console.print("  3. Ensure you have ExecuteQuery permission")
                        console.print("  4. Try a simpler query like: EVALUATE { [Total Revenue] }")

                    console.print("\n" + "=" * 60)
                else:
                    console.print("[red]ExecuteQuery tool not found![/red]")

                # Test GenerateQuery with natural language
                console.print("\n[bold]Step 5c: Testing GenerateQuery with natural language...[/bold]\n")

                generate_tool = next((t for t in tools if t.get("name") == "GenerateQuery"), None)

                if generate_tool:
                    console.print("[cyan]Testing: GenerateQuery[/cyan]")
                    console.print("─" * 60)

                    console.print("  User Input (natural language):")
                    console.print(f"[dim]  \"{test_user_input}\"[/dim]\n")

                    console.print("  Schema Selection:")
                    console.print(JSON(json.dumps(test_schema_selection, indent=2)))
                    console.print()

                    try:
                        result = await mcp_client.call_tool(
                            name="GenerateQuery",
                            arguments={
                                "artifactId": artifact_id,
                                "userInput": test_user_input,
                                "schemaSelection": test_schema_selection
                            }
                        )

                        console.print("[green]✓[/green] DAX query generated successfully!")
                        console.print(f"\nResult type: {type(result).__name__}")

                        # Display result
                        if result:
                            try:
                                if isinstance(result, str):
                                    try:
                                        result_json = json.loads(result)
                                        console.print("\n[bold]Generated DAX Query:[/bold]")
                                        console.print(JSON(json.dumps(result_json, indent=2)))

                                        # Try to extract the DAX query
                                        if isinstance(result_json, dict):
                                            if "daxQuery" in result_json:
                                                console.print("\n[bold green]Generated DAX:[/bold green]")
                                                console.print(f"[cyan]{result_json['daxQuery']}[/cyan]")
                                            elif "structuredContent" in result_json:
                                                structured = result_json["structuredContent"]
                                                if "GeneratedQuery" in structured:
                                                    console.print("\n[bold green]Generated DAX:[/bold green]")
                                                    console.print(f"[cyan]{structured['GeneratedQuery']}[/cyan]")
                                    except json.JSONDecodeError:
                                        console.print("\n[bold]Generated Result (text):[/bold]")
                                        console.print(result[:2000])
                                elif isinstance(result, dict):
                                    console.print("\n[bold]Generated Query Result:[/bold]")
                                    console.print(JSON(json.dumps(result, indent=2)))

                                    # Try to extract the DAX query from dict
                                    if "structuredContent" in result:
                                        structured = result["structuredContent"]
                                        if "GeneratedQuery" in structured:
                                            console.print("\n[bold green]Generated DAX:[/bold green]")
                                            console.print(f"[cyan]{structured['GeneratedQuery']}[/cyan]")
                                    elif "daxQuery" in result:
                                        console.print("\n[bold green]Generated DAX:[/bold green]")
                                        console.print(f"[cyan]{result['daxQuery']}[/cyan]")
                                else:
                                    console.print(f"\n{result}")
                            except Exception as e:
                                console.print(f"[yellow]Could not format result: {e}[/yellow]")
                                console.print(f"Raw result: {result}")
                        else:
                            console.print("[yellow]![/yellow] No query generated")

                    except Exception as e:
                        console.print(f"[red]✗[/red] Error: {e}")
                        console.print("\n[yellow]Troubleshooting tips:[/yellow]")
                        console.print("  1. Verify the schema selection includes relevant tables/columns")
                        console.print("  2. Check that the user input is clear and answerable with the schema")
                        console.print("  3. Ensure you have GenerateQuery permission")
                        console.print("  4. Try a simpler query like: 'Show me total revenue'")

                    console.print("\n" + "=" * 60)
                else:
                    console.print("[red]GenerateQuery tool not found![/red]")

            # Only do general testing if no specific artifact was provided
            if not artifact_id:
                # Test each tool
                console.print("\n[bold]Step 6: Testing all tools (general)...[/bold]\n")
                console.print("[dim]Note: These will likely fail because they require parameters.[/dim]")
                console.print("[dim]This test shows what parameters each tool needs.[/dim]\n")

                for tool in tools:
                    tool_name = tool.get("name")
                    console.print(f"\n[cyan]Testing: {tool_name}[/cyan]")
                    console.print("─" * 60)

                    # Display tool schema
                    input_schema = tool.get("inputSchema", {})
                    properties = input_schema.get("properties", {})
                    required = input_schema.get("required", [])

                    if properties:
                        console.print(f"  Parameters ({len(properties)}):")
                        for param_name, param_info in properties.items():
                            req_marker = "[red]*[/red]" if param_name in required else " "
                            param_type = param_info.get("type", "unknown")
                            param_desc = param_info.get("description", "No description")
                            console.print(f"    {req_marker} {param_name} ({param_type}): {param_desc}")
                    else:
                        console.print("  [dim]No parameters[/dim]")

                    # Attempt to call tool with minimal/empty params
                    console.print(f"\n  Attempting to call [yellow]{tool_name}[/yellow]...")

                    try:
                        # Try calling with empty arguments first
                        result = await mcp_client.call_tool(
                            name=tool_name,
                            arguments={}
                        )

                        console.print(f"  [green]✓[/green] Tool executed")

                        # Display result
                        if result:
                            console.print(f"  Result type: {type(result).__name__}")
                            console.print(f"  Result preview:")

                            # Try to display as JSON if possible
                            try:
                                if isinstance(result, str):
                                    # Try to parse as JSON
                                    try:
                                        result_json = json.loads(result)
                                        console.print(JSON(json.dumps(result_json, indent=2)))
                                    except:
                                        # Not JSON, display as string
                                        preview = result[:500] + "..." if len(result) > 500 else result
                                        console.print(f"  [dim]{preview}[/dim]")
                                elif isinstance(result, dict):
                                    console.print(JSON(json.dumps(result, indent=2)))
                                else:
                                    console.print(f"  [dim]{str(result)[:500]}[/dim]")
                            except Exception as e:
                                console.print(f"  [dim]Could not display result: {e}[/dim]")
                        else:
                            console.print("  [yellow]![/yellow] No result returned")

                    except Exception as e:
                        error_msg = str(e)
                        console.print(f"  [red]✗[/red] Error: {error_msg}")

                        # Provide guidance based on error
                        if "required" in error_msg.lower():
                            console.print(f"  [yellow]→[/yellow] This tool requires parameters")
                            console.print(f"  [dim]  Required: {', '.join(required)}[/dim]")
                        elif "unauthorized" in error_msg.lower() or "403" in error_msg:
                            console.print(f"  [yellow]→[/yellow] Permission issue - check API permissions")
                        elif "404" in error_msg or "not found" in error_msg.lower():
                            console.print(f"  [yellow]→[/yellow] Resource not found - may need workspace/dataset ID")
            else:
                console.print("\n[green]✓[/green] Skipping general tool tests since specific artifact was provided")
                console.print("[dim]  (General tests would fail anyway without required parameters)[/dim]")

            # Summary
            console.print("\n" + "=" * 60)
            console.print("\n[bold green]Diagnostic test complete![/bold green]\n")

            console.print("[bold]Next Steps:[/bold]")
            console.print("1. Check which tools executed successfully")
            console.print("2. For tools requiring parameters, note what's needed")
            console.print("3. Verify you have PowerBI Pro/Premium license")
            console.print("4. Ensure you have access to at least one workspace")
            console.print("5. Check Azure app permissions include PowerBI scopes")

            return 0

    except KeyboardInterrupt:
        console.print("\n[yellow]Test interrupted by user[/yellow]")
        return 1

    except Exception as e:
        console.print(f"\n[red]Test failed: {e}[/red]")
        import traceback
        console.print("\n[dim]Full traceback:[/dim]")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Test PowerBI MCP tools, optionally with a specific artifact GUID"
    )
    parser.add_argument(
        "-a", "--artifact-id",
        help="PowerBI artifact GUID (semantic model/dataset ID) to test with"
    )

    args = parser.parse_args()

    # Display usage info if no args
    if not args.artifact_id:
        console.print("[dim]Tip: You can test a specific semantic model with:[/dim]")
        console.print("[dim]  python test_powerbi_tools.py -a <artifact-guid>[/dim]")
        console.print("[dim]  python test_powerbi_tools.py --artifact-id xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx[/dim]\n")

    sys.exit(asyncio.run(test_tools(artifact_id=args.artifact_id)))
