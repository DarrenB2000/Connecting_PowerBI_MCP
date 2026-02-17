"""
Tool format converter between MCP and Claude formats.

MCP and Claude use slightly different schemas for tools.
This module provides conversion utilities.
"""
from typing import Dict, Any, List


def convert_mcp_tool_to_claude(mcp_tool: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert MCP tool format to Claude tool format.

    MCP format uses 'inputSchema', Claude uses 'input_schema'.

    Args:
        mcp_tool: Tool in MCP format with keys: name, description, inputSchema

    Returns:
        Tool in Claude format with keys: name, description, input_schema

    Example:
        >>> mcp_tool = {
        ...     "name": "get_datasets",
        ...     "description": "Retrieve PowerBI datasets",
        ...     "inputSchema": {
        ...         "type": "object",
        ...         "properties": {"workspace_id": {"type": "string"}}
        ...     }
        ... }
        >>> claude_tool = convert_mcp_tool_to_claude(mcp_tool)
        >>> claude_tool["input_schema"]  # Note: input_schema not inputSchema
    """
    return {
        "name": mcp_tool["name"],
        "description": mcp_tool.get("description", ""),
        "input_schema": mcp_tool.get("inputSchema", {})
    }


def convert_mcp_tools_to_claude(mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert list of MCP tools to Claude format.

    Args:
        mcp_tools: List of tools in MCP format

    Returns:
        List of tools in Claude format
    """
    return [convert_mcp_tool_to_claude(tool) for tool in mcp_tools]


def convert_claude_tool_result_to_mcp(
    tool_use_id: str,
    content: Any,
    is_error: bool = False
) -> Dict[str, Any]:
    """
    Convert Claude tool result format to MCP format.

    Args:
        tool_use_id: Tool use ID from Claude
        content: Tool result content
        is_error: Whether this is an error result

    Returns:
        Tool result in format suitable for Claude API
    """
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content,
        "is_error": is_error
    }


def format_tool_result_for_claude(
    tool_use_id: str,
    mcp_result: Any
) -> Dict[str, Any]:
    """
    Format MCP tool execution result for Claude API.

    Args:
        tool_use_id: Tool use ID from Claude's tool_use content block
        mcp_result: Result from MCP tool execution

    Returns:
        Formatted tool result for Claude
    """
    # MCP results can be various types, convert to string for Claude
    if hasattr(mcp_result, 'content'):
        # MCP CallToolResult object
        content_items = []
        for item in mcp_result.content:
            if hasattr(item, 'text'):
                content_items.append(item.text)
            elif hasattr(item, 'data'):
                content_items.append(str(item.data))
            else:
                content_items.append(str(item))
        content = "\n".join(content_items) if content_items else str(mcp_result)
    else:
        content = str(mcp_result)

    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content
    }


def validate_mcp_tool_schema(tool: Dict[str, Any]) -> bool:
    """
    Validate that a tool has the required MCP schema fields.

    Args:
        tool: Tool definition to validate

    Returns:
        True if valid, False otherwise
    """
    required_fields = ["name", "description"]
    return all(field in tool for field in required_fields)


def get_tool_parameter_info(tool: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract parameter information from tool schema.

    Args:
        tool: Tool definition (MCP or Claude format)

    Returns:
        Dictionary with parameter details
    """
    # Works with both MCP (inputSchema) and Claude (input_schema) formats
    schema = tool.get("inputSchema") or tool.get("input_schema", {})

    properties = schema.get("properties", {})
    required = schema.get("required", [])

    return {
        "parameters": list(properties.keys()),
        "required": required,
        "optional": [p for p in properties.keys() if p not in required],
        "schema": schema
    }


def create_tool_summary(tools: List[Dict[str, Any]]) -> str:
    """
    Create human-readable summary of available tools.

    Args:
        tools: List of tool definitions

    Returns:
        Formatted string summarizing tools
    """
    if not tools:
        return "No tools available"

    lines = [f"Available Tools ({len(tools)}):"]
    lines.append("")

    for i, tool in enumerate(tools, 1):
        lines.append(f"{i}. {tool['name']}")
        lines.append(f"   {tool.get('description', 'No description')}")

        param_info = get_tool_parameter_info(tool)
        if param_info["parameters"]:
            params_str = ", ".join(param_info["parameters"])
            lines.append(f"   Parameters: {params_str}")
            if param_info["required"]:
                req_str = ", ".join(param_info["required"])
                lines.append(f"   Required: {req_str}")

        lines.append("")

    return "\n".join(lines)
