"""
Simple MCP Client for PowerBI using HTTP POST request-response.

This bypasses the MCP SDK's streaming ClientSession since PowerBI
uses HTTP POST request-response, not streaming.
"""
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from rich.console import Console

from auth import AuthManager
from .http_transport import HTTPTransport


console = Console()


class SimpleMCPClient:
    """
    Simple MCP client for HTTP POST request-response protocol.

    Unlike the MCP SDK's ClientSession which expects streaming,
    this client works with PowerBI's request-response HTTP POST.
    """

    def __init__(
        self,
        server_url: str,
        auth_manager: AuthManager
    ):
        """
        Initialize simple MCP client.

        Args:
            server_url: PowerBI MCP server URL
            auth_manager: Authentication manager
        """
        self.server_url = server_url
        self.auth_manager = auth_manager
        self._transport: Optional[HTTPTransport] = None
        self._tools: List[Dict[str, Any]] = []
        self._connected = False
        self._request_id = 0
        self._manual_connection = False  # Flag to prevent auto-cleanup

    @asynccontextmanager
    async def connect(self):
        """
        Connect to PowerBI MCP server.

        Yields:
            SimpleMCPClient instance
        """
        try:
            # Get access token
            console.print("[dim]Acquiring authentication token...[/dim]")
            access_token = self.auth_manager.get_token()

            console.print(f"[dim]Connecting to MCP server: {self.server_url}[/dim]")

            # Create HTTP transport
            self._transport = HTTPTransport(
                url=self.server_url,
                headers={"Authorization": f"Bearer {access_token}"}
            )

            await self._transport.connect()
            self._connected = True

            # Initialize MCP session
            console.print("[dim]Initializing MCP session...[/dim]")
            init_result = await self._initialize()

            console.print(
                f"[green]✓[/green] Connected to MCP server"
            )
            console.print(
                f"[dim]Server: {init_result['serverInfo']['name']} "
                f"v{init_result['serverInfo']['version']}[/dim]"
            )

            # Discover tools
            await self._discover_tools()

            try:
                yield self
            finally:
                # Only auto-cleanup if not manually managed
                if not self._manual_connection:
                    console.print("[yellow]⚠️  MCP connection finally block triggered - auto cleanup[/yellow]")
                    self._connected = False
                    if self._transport:
                        await self._transport.close()
                        self._transport = None
                else:
                    console.print("[dim]MCP connection finally block triggered - skipping cleanup (manual mode)[/dim]")

        except Exception as e:
            self._connected = False
            raise Exception(f"Failed to connect to MCP server: {e}")

    async def _initialize(self) -> Dict[str, Any]:
        """
        Send MCP initialize request.

        Returns:
            Initialize response result
        """
        self._request_id += 1
        message = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "powerbi-mcp-cli",
                    "version": "0.1.0"
                }
            },
            "id": self._request_id
        }

        response = await self._transport.send(message)
        return response.get("result", {})

    async def _discover_tools(self) -> None:
        """Discover available tools from server."""
        console.print("[dim]Discovering available tools...[/dim]")

        self._request_id += 1
        message = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": self._request_id
        }

        response = await self._transport.send(message)
        result = response.get("result", {})
        tools = result.get("tools", [])

        self._tools = [
            {
                "name": tool.get("name"),
                "description": tool.get("description"),
                "inputSchema": tool.get("inputSchema", {})
            }
            for tool in tools
        ]

        console.print(
            f"[green]✓[/green] Discovered {len(self._tools)} tools"
        )

    async def call_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute a tool.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        # Debug logging
        console.print(f"[dim]call_tool debug: _connected={self._connected}, _transport={self._transport is not None}[/dim]")
        if self._transport:
            console.print(f"[dim]  _transport._client={self._transport._client is not None}[/dim]")

        if not self._connected or not self._transport:
            raise Exception("Not connected to MCP server")

        if arguments is None:
            arguments = {}

        console.print(f"[dim]Executing tool: {name}[/dim]")

        self._request_id += 1
        message = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            },
            "id": self._request_id
        }

        response = await self._transport.send(message)

        # Debug: Show response structure
        console.print(f"[dim]  Response keys: {list(response.keys()) if isinstance(response, dict) else 'not a dict'}[/dim]")

        result = response.get("result", {})

        # Debug: Show result structure
        if isinstance(result, dict):
            console.print(f"[dim]  Result keys: {list(result.keys())}[/dim]")

        console.print(f"[green]✓[/green] Tool executed successfully")

        return result

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools."""
        return self._tools.copy()

    def get_tool_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get tool by name."""
        for tool in self._tools:
            if tool["name"] == name:
                return tool.copy()
        return None

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    @property
    def tool_count(self) -> int:
        """Get tool count."""
        return len(self._tools)
