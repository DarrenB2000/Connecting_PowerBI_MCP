"""
Claude API Client for PowerBI MCP CLI.

Handles communication with Anthropic's Claude API with MCP tool integration.
"""
from typing import List, Dict, Any, Optional, AsyncIterator
import anthropic
from anthropic.types import Message, MessageStreamEvent
import json

from rich.console import Console


console = Console()


class ClaudeClient:
    """
    Client for Anthropic's Claude API.

    Handles message sending, streaming, and tool use with MCP integration.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-5",
        max_tokens: int = 4096,
        temperature: float = 0.7
    ):
        """
        Initialize Claude client.

        Args:
            api_key: Anthropic API key
            model: Claude model to use
            max_tokens: Maximum tokens in response
            temperature: Response temperature (0-1)
        """
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

        # Create Anthropic client
        self.client = anthropic.Anthropic(api_key=api_key)
        self.async_client = anthropic.AsyncAnthropic(api_key=api_key)

    async def send_message(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None
    ) -> Message:
        """
        Send message to Claude.

        Args:
            messages: Conversation history
            tools: Available tools (MCP tools in Claude format)
            system: System prompt

        Returns:
            Claude message response
        """
        # Build request parameters
        params = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": messages
        }

        # Add system prompt if provided
        if system:
            params["system"] = system

        # Add tools if provided
        if tools:
            params["tools"] = tools

        # Send request
        console.print(f"[dim]Sending message to Claude ({self.model})...[/dim]")
        response = await self.async_client.messages.create(**params)

        console.print(
            f"[dim]Response received: {response.stop_reason}[/dim]"
        )

        return response

    async def send_message_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None
    ) -> AsyncIterator[MessageStreamEvent]:
        """
        Send message to Claude with streaming response.

        Args:
            messages: Conversation history
            tools: Available tools
            system: System prompt

        Yields:
            Stream events from Claude
        """
        # Build request parameters
        params = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": messages
        }

        if system:
            params["system"] = system

        if tools:
            params["tools"] = tools

        # Stream response
        console.print(f"[dim]Streaming message to Claude ({self.model})...[/dim]")

        async with self.async_client.messages.stream(**params) as stream:
            async for event in stream:
                yield event

    def extract_text_from_response(self, response: Message) -> str:
        """
        Extract text content from Claude response.

        Args:
            response: Claude message response

        Returns:
            Extracted text content
        """
        text_parts = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)

        return "\n".join(text_parts)

    def has_tool_use(self, response: Message) -> bool:
        """
        Check if response contains tool use requests.

        Args:
            response: Claude message response

        Returns:
            True if response has tool use
        """
        return any(block.type == "tool_use" for block in response.content)

    def get_tool_uses(self, response: Message) -> List[Dict[str, Any]]:
        """
        Extract tool use requests from response.

        Args:
            response: Claude message response

        Returns:
            List of tool use requests
        """
        tool_uses = []

        for block in response.content:
            if block.type == "tool_use":
                tool_uses.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })

        return tool_uses

    def format_response_for_history(self, response: Message) -> Dict[str, Any]:
        """
        Format Claude response for conversation history.

        Args:
            response: Claude message response

        Returns:
            Formatted message for history
        """
        content = []

        for block in response.content:
            if block.type == "text":
                content.append({
                    "type": "text",
                    "text": block.text
                })
            elif block.type == "tool_use":
                content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })

        return {
            "role": "assistant",
            "content": content
        }

    @staticmethod
    def create_tool_result_message(
        tool_use_id: str,
        result: Any,
        is_error: bool = False
    ) -> Dict[str, Any]:
        """
        Create tool result message for Claude.

        Args:
            tool_use_id: ID of tool use request
            result: Tool execution result
            is_error: Whether result is an error

        Returns:
            Formatted tool result message
        """
        # Convert result to string if needed
        if isinstance(result, dict):
            # PowerBI MCP returns structuredContent field with the actual data
            # Check structuredContent first, then fall back to content
            if "structuredContent" in result and result["structuredContent"]:
                # Format structuredContent as JSON
                try:
                    result_text = json.dumps(result["structuredContent"], indent=2)
                except (TypeError, ValueError):
                    result_text = str(result["structuredContent"])
            elif "content" in result:
                content_items = result["content"]
                if isinstance(content_items, list):
                    # Extract text from content items
                    text_parts = []
                    for item in content_items:
                        if isinstance(item, dict):
                            if "text" in item:
                                # Try to parse as JSON first for better formatting
                                text_content = item["text"]
                                try:
                                    # If it's a JSON string, parse and re-format it
                                    json_data = json.loads(text_content)
                                    text_parts.append(json.dumps(json_data, indent=2))
                                except (json.JSONDecodeError, TypeError):
                                    # Not JSON, use as-is
                                    text_parts.append(text_content)
                            else:
                                # Item is a dict but no "text" field, format as JSON
                                text_parts.append(json.dumps(item, indent=2))
                        else:
                            text_parts.append(str(item))
                    result_text = "\n".join(text_parts)
                else:
                    # Single content item
                    try:
                        result_text = json.dumps(content_items, indent=2)
                    except (TypeError, ValueError):
                        result_text = str(content_items)
            else:
                # Dict without content or structuredContent field - format as JSON
                try:
                    result_text = json.dumps(result, indent=2)
                except (TypeError, ValueError):
                    result_text = str(result)
        else:
            result_text = str(result)

        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result_text,
                    "is_error": is_error
                }
            ]
        }

    def __repr__(self) -> str:
        """String representation."""
        return f"ClaudeClient(model={self.model})"
