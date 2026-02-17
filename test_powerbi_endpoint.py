"""
Simple HTTP test for PowerBI MCP endpoint.

Tests basic HTTP connectivity and server responses.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import httpx
from auth import AuthManager
from config import get_settings
from rich.console import Console
from rich.syntax import Syntax
import json

console = Console()

def test_endpoint():
    """Test PowerBI MCP endpoint with basic HTTP."""
    try:
        # Load config
        settings = get_settings()
        console.print(f"Testing endpoint: {settings.powerbi.mcp_url}\n")

        # Setup auth
        auth_manager = AuthManager(
            client_id=settings.azure.client_id,
            tenant_id=settings.azure.tenant_id,
            scopes=settings.azure.scopes,
            cache_path=settings.app.token_cache_path
        )

        # Get token
        token = auth_manager.get_token()
        console.print(f"Token: {token[:20]}...\n")

        # Test 1: Basic GET request
        console.print("[bold]Test 1: Basic GET request[/bold]")
        try:
            response = httpx.get(
                settings.powerbi.mcp_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "*/*"
                },
                timeout=10.0
            )
            console.print(f"Status: {response.status_code}")
            console.print(f"Headers: {dict(response.headers)}\n")

            if response.text:
                console.print("Response body:")
                try:
                    json_data = response.json()
                    syntax = Syntax(json.dumps(json_data, indent=2), "json")
                    console.print(syntax)
                except:
                    console.print(response.text[:500])
        except Exception as e:
            console.print(f"[red]GET failed: {e}[/red]\n")

        # Test 2: Check if it's an SSE endpoint
        console.print("\n[bold]Test 2: SSE endpoint test[/bold]")
        try:
            response = httpx.get(
                settings.powerbi.mcp_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "text/event-stream",
                    "Cache-Control": "no-cache"
                },
                timeout=10.0
            )
            console.print(f"Status: {response.status_code}")
            console.print(f"Content-Type: {response.headers.get('content-type')}")

            if response.text:
                console.print(f"Response preview: {response.text[:200]}\n")
        except Exception as e:
            console.print(f"[red]SSE test failed: {e}[/red]\n")

        # Test 3: Check for MCP protocol metadata
        console.print("\n[bold]Test 3: MCP metadata endpoint[/bold]")
        metadata_urls = [
            f"{settings.powerbi.mcp_url}/.well-known/oauth-protected-resource",
            f"{settings.powerbi.mcp_url}/metadata",
            f"{settings.powerbi.mcp_url}/mcp",
        ]

        for url in metadata_urls:
            try:
                console.print(f"Trying: {url}")
                response = httpx.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json"
                    },
                    timeout=5.0
                )
                if response.status_code == 200:
                    console.print(f"[green]✓ Found at {url}[/green]")
                    console.print(f"Response: {response.text[:300]}\n")
                else:
                    console.print(f"Status: {response.status_code}\n")
            except Exception as e:
                console.print(f"Failed: {e}\n")

        # Test 4: POST request (MCP might use POST)
        console.print("\n[bold]Test 4: POST request test[/bold]")
        try:
            response = httpx.post(
                settings.powerbi.mcp_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={"jsonrpc": "2.0", "method": "initialize", "id": 1},
                timeout=10.0
            )
            console.print(f"Status: {response.status_code}")
            console.print(f"Response: {response.text[:500]}\n")
        except Exception as e:
            console.print(f"[red]POST failed: {e}[/red]\n")

    except Exception as e:
        console.print(f"\n[red]Test failed: {e}[/red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_endpoint()
