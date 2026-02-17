"""
MCP Client for PowerBI MCP server.

Handles connection, tool discovery, and tool execution via HTTP POST transport.
"""
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.session import ClientSession as MCPClientSession
from rich.console import Console

from auth import AuthManager
from .http_transport import http_mcp_client


console = Console()


class MCPClientError(Exception):
    """Exception raised for MCP client errors."""
    pass


class MCPClient:
    """
    Client for connecting to PowerBI MCP server.

    Manages SSE connection, tool discovery, and execution with authentication.
    """

    def __init__(
        self,
        server_url: str,
        auth_manager: AuthManager
    ):
        """
        Initialize MCP client.

        Args:
            server_url: PowerBI MCP server URL
            auth_manager: Authentication manager for token acquisition
        """
        self.server_url = server_url
        self.auth_manager = auth_manager
        self._session: Optional[MCPClientSession] = None
        self._tools: List[Dict[str, Any]] = []
        self._resources: List[Dict[str, Any]] = []
        self._connected = False

    @asynccontextmanager
    async def connect(self):
        """
        Connect to PowerBI MCP server via HTTP POST.

        Context manager for managing connection lifecycle.

        Yields:
            MCPClient instance

        Raises:
            MCPClientError: If connection fails
        """
        try:
            # Get access token
            console.print("[dim]Acquiring authentication token...[/dim]")
            access_token = self.auth_manager.get_token()

            console.print(f"[dim]Connecting to MCP server: {self.server_url}[/dim]")

            # Create HTTP POST client with authentication
            async with http_mcp_client(
                url=self.server_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
            ) as (read_stream, write_stream):
                # Create MCP session
                async with ClientSession(read_stream, write_stream) as session:
                    self._session = session
                    self._connected = True

                    # Initialize connection
                    console.print("[dim]Initializing MCP session...[/dim]")
                    init_result = await session.initialize()

                    console.print(
                        f"[green]✓[/green] Connected to MCP server"
                    )
                    console.print(
                        f"[dim]Server: {init_result.server_info.name} "
                        f"v{init_result.server_info.version}[/dim]"
                    )

                    # Discover tools and resources
                    await self._discover_capabilities()

                    try:
                        yield self
                    finally:
                        self._connected = False
                        self._session = None

        except Exception as e:
            self._connected = False
            raise MCPClientError(f"Failed to connect to MCP server: {e}")

    async def _discover_capabilities(self) -> None:
        """
        Discover available tools and resources from MCP server.

        Raises:
            MCPClientError: If discovery fails
        """
        if not self._session:
            raise MCPClientError("Not connected to MCP server")

        try:
            # Discover tools
            console.print("[dim]Discovering available tools...[/dim]")
            tools_response = await self._session.list_tools()
            self._tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                }
                for tool in tools_response.tools
            ]

            console.print(
                f"[green]✓[/green] Discovered {len(self._tools)} tools"
            )

            # Discover resources (optional - PowerBI may or may not have resources)
            try:
                resources_response = await self._session.list_resources()
                self._resources = [
                    {
                        "uri": resource.uri,
                        "name": resource.name,
                        "description": resource.description,
                        "mimeType": resource.mimeType
                    }
                    for resource in resources_response.resources
                ]

                if self._resources:
                    console.print(
                        f"[green]✓[/green] Discovered {len(self._resources)} resources"
                    )
            except Exception as e:
                console.print(
                    f"[dim]No resources available or discovery failed: {e}[/dim]"
                )

        except Exception as e:
            raise MCPClientError(f"Failed to discover capabilities: {e}")

    async def call_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute a tool on the MCP server.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            MCPClientError: If tool execution fails
        """
        if not self._session or not self._connected:
            raise MCPClientError("Not connected to MCP server")

        if arguments is None:
            arguments = {}

        try:
            console.print(
                f"[dim]Executing tool: {name}[/dim]"
            )

            result = await self._session.call_tool(
                name=name,
                arguments=arguments
            )

            console.print(
                f"[green]✓[/green] Tool executed successfully"
            )

            return result

        except Exception as e:
            raise MCPClientError(f"Tool execution failed ({name}): {e}")

    async def read_resource(self, uri: str) -> Any:
        """
        Read a resource from the MCP server.

        Args:
            uri: Resource URI

        Returns:
            Resource content

        Raises:
            MCPClientError: If resource read fails
        """
        if not self._session or not self._connected:
            raise MCPClientError("Not connected to MCP server")

        try:
            console.print(f"[dim]Reading resource: {uri}[/dim]")

            result = await self._session.read_resource(uri=uri)

            console.print(f"[green]✓[/green] Resource read successfully")

            return result

        except Exception as e:
            raise MCPClientError(f"Resource read failed ({uri}): {e}")

    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of available tools.

        Returns:
            List of tool definitions

        Raises:
            MCPClientError: If not connected or tools not discovered
        """
        if not self._connected:
            raise MCPClientError("Not connected to MCP server")

        return self._tools.copy()

    def get_resources(self) -> List[Dict[str, Any]]:
        """
        Get list of available resources.

        Returns:
            List of resource definitions

        Raises:
            MCPClientError: If not connected or resources not discovered
        """
        if not self._connected:
            raise MCPClientError("Not connected to MCP server")

        return self._resources.copy()

    def get_tool_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get tool definition by name.

        Args:
            name: Tool name

        Returns:
            Tool definition or None if not found
        """
        for tool in self._tools:
            if tool["name"] == name:
                return tool.copy()
        return None

    @property
    def is_connected(self) -> bool:
        """Check if connected to MCP server."""
        return self._connected

    @property
    def tool_count(self) -> int:
        """Get number of available tools."""
        return len(self._tools)

    @property
    def resource_count(self) -> int:
        """Get number of available resources."""
        return len(self._resources)

    def __repr__(self) -> str:
        """String representation."""
        status = "connected" if self._connected else "disconnected"
        return (
            f"MCPClient(url={self.server_url}, "
            f"status={status}, "
            f"tools={self.tool_count}, "
            f"resources={self.resource_count})"
        )
