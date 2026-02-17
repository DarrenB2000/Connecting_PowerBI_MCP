"""
Client modules for PowerBI MCP CLI.

Includes MCP client for PowerBI server connection and tool format converters.
"""

from .mcp_client import MCPClient, MCPClientError
from .simple_mcp_client import SimpleMCPClient
from .claude_client import ClaudeClient
from .http_transport import HTTPTransport, http_mcp_client
from .tool_converter import (
    convert_mcp_tool_to_claude,
    convert_mcp_tools_to_claude,
    convert_claude_tool_result_to_mcp,
    format_tool_result_for_claude,
    validate_mcp_tool_schema,
    get_tool_parameter_info,
    create_tool_summary,
)

__all__ = [
    # MCP Client
    "MCPClient",
    "MCPClientError",
    "SimpleMCPClient",
    # Claude Client
    "ClaudeClient",
    # HTTP Transport
    "HTTPTransport",
    "http_mcp_client",
    # Tool Converters
    "convert_mcp_tool_to_claude",
    "convert_mcp_tools_to_claude",
    "convert_claude_tool_result_to_mcp",
    "format_tool_result_for_claude",
    "validate_mcp_tool_schema",
    "get_tool_parameter_info",
    "create_tool_summary",
]
