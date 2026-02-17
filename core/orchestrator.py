"""
Agent Orchestrator - Agentic loop coordinator.

Manages conversation flow between user, Claude, and PowerBI MCP tools.
"""
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from clients import ClaudeClient, SimpleMCPClient, convert_mcp_tools_to_claude


console = Console()


class AgentOrchestrator:
    """
    Coordinates the agentic loop between user, Claude API, and MCP tools.

    Manages conversation history, tool execution, and response formatting.
    """

    def __init__(
        self,
        claude_client: ClaudeClient,
        mcp_client: SimpleMCPClient,
        system_prompt: Optional[str] = None,
        max_iterations: int = 10
    ):
        """
        Initialize orchestrator.

        Args:
            claude_client: Claude API client
            mcp_client: MCP client for PowerBI
            system_prompt: System prompt for Claude
            max_iterations: Maximum agentic loop iterations
        """
        self.claude_client = claude_client
        self.mcp_client = mcp_client
        self.max_iterations = max_iterations

        # Default system prompt
        self.system_prompt = system_prompt or (
            "You are a helpful PowerBI assistant. "
            "You have access to PowerBI tools to help users query and analyze their data.\n\n"
            "IMPORTANT GUIDELINES:\n"
            "1. When you receive schema results from GetSemanticModelSchema, always display them to the user in a clear, organized format.\n"
            "2. The schema includes Tables (with Columns), Measures, and Relationships - summarize the key elements.\n"
            "3. When presenting schema data, use markdown tables or bullet lists for readability.\n"
            "4. After displaying schema, suggest what analyses or queries the user can perform.\n"
            "5. Tool results are provided in JSON format - parse and present them clearly.\n"
            "6. Be concise but complete - don't skip displaying important data that was successfully retrieved.\n\n"
            "CHART AND VISUALIZATION RULES:\n"
            "- The UI automatically renders interactive charts from query results. Do NOT generate chart code, JSON specs, Vega-Lite specs, or HTML in your responses.\n"
            "- Do NOT output JSON, code blocks, or markup of any kind for visualizations.\n"
            "- Simply describe the data and provide insights in plain text. The chart will appear automatically above your response.\n\n"
            "When using tools, explain what you're doing and present results clearly."
        )

        # Conversation history
        self.conversation_history: List[Dict[str, Any]] = []

        # Available tools
        self._mcp_tools: List[Dict[str, Any]] = []
        self._claude_tools: List[Dict[str, Any]] = []

        # Track tool executions from last turn (for UI display)
        self.last_tool_executions: List[Dict[str, Any]] = []

    def set_tools(self, mcp_tools: List[Dict[str, Any]]) -> None:
        """
        Set available MCP tools and convert to Claude format.

        Args:
            mcp_tools: List of MCP tool definitions
        """
        self._mcp_tools = mcp_tools
        self._claude_tools = convert_mcp_tools_to_claude(mcp_tools)

        console.print(
            f"[dim]Orchestrator ready with {len(self._claude_tools)} tools[/dim]"
        )

    async def run_conversation_turn(self, user_message: str) -> str:
        """
        Run one conversation turn with agentic loop.

        Args:
            user_message: User's input message

        Returns:
            Claude's final response text
        """
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Agentic loop
        iteration = 0
        final_response_text = ""

        # Reset tool executions for this turn
        self.last_tool_executions = []

        while iteration < self.max_iterations:
            iteration += 1

            console.print(
                f"[dim]Agent iteration {iteration}/{self.max_iterations}[/dim]"
            )

            # Send to Claude with available tools
            response = await self.claude_client.send_message(
                messages=self.conversation_history,
                tools=self._claude_tools,
                system=self.system_prompt
            )

            # Add Claude's response to history
            self.conversation_history.append(
                self.claude_client.format_response_for_history(response)
            )

            # Extract text from response
            response_text = self.claude_client.extract_text_from_response(response)
            if response_text:
                final_response_text = response_text

            # Check stop reason
            if response.stop_reason == "end_turn":
                # Claude finished - exit loop
                console.print("[dim]Claude finished turn[/dim]")
                break

            elif response.stop_reason == "tool_use":
                # Claude wants to use tools
                console.print("[yellow]Claude requesting tool use...[/yellow]")

                tool_uses = self.claude_client.get_tool_uses(response)

                # Execute each tool
                tool_results = []

                for tool_use in tool_uses:
                    tool_name = tool_use["name"]
                    tool_input = tool_use["input"]
                    tool_id = tool_use["id"]

                    console.print(f"[cyan]  → Executing: {tool_name}[/cyan]")

                    try:
                        # Call MCP tool
                        result = await self.mcp_client.call_tool(
                            name=tool_name,
                            arguments=tool_input
                        )

                        # Debug: Show raw result structure
                        console.print(f"[dim]  Raw result type: {type(result).__name__}[/dim]")
                        if isinstance(result, dict):
                            console.print(f"[dim]  Raw result keys: {list(result.keys())}[/dim]")
                            if "content" in result:
                                console.print(f"[dim]  Content field type: {type(result['content']).__name__}[/dim]")
                                if isinstance(result["content"], list):
                                    console.print(f"[dim]  Content items: {len(result['content'])}[/dim]")
                            if "structuredContent" in result:
                                console.print(f"[dim]  structuredContent type: {type(result['structuredContent']).__name__}[/dim]")
                                if isinstance(result["structuredContent"], dict):
                                    console.print(f"[dim]  structuredContent keys: {list(result['structuredContent'].keys())}[/dim]")

                        # Track tool execution for UI display
                        self.last_tool_executions.append({
                            'name': tool_name,
                            'status': 'success',
                            'result': result
                        })

                        # Create tool result message
                        tool_result_msg = self.claude_client.create_tool_result_message(
                            tool_use_id=tool_id,
                            result=result,
                            is_error=False
                        )

                        tool_results.append(tool_result_msg)

                        console.print(f"[green]  ✓ Tool executed successfully[/green]")

                        # Debug: Show result size for troubleshooting
                        result_content = tool_result_msg["content"][0]["content"]
                        result_size = len(result_content)
                        console.print(f"[dim]  Result size: {result_size:,} characters[/dim]")

                    except Exception as e:
                        console.print(f"[red]  ✗ Tool error: {e}[/red]")

                        # Track tool execution error for UI display
                        self.last_tool_executions.append({
                            'name': tool_name,
                            'status': 'error',
                            'error': str(e)
                        })

                        # Send error back to Claude
                        error_msg = self.claude_client.create_tool_result_message(
                            tool_use_id=tool_id,
                            result=f"Error executing tool: {str(e)}",
                            is_error=True
                        )

                        tool_results.append(error_msg)

                # Add all tool results to history
                for tool_result in tool_results:
                    self.conversation_history.append(tool_result)

                # Continue loop - Claude will process results
                continue

            elif response.stop_reason == "max_tokens":
                console.print("[yellow]Warning: Response hit max tokens[/yellow]")
                break

            else:
                # Unknown stop reason
                console.print(
                    f"[yellow]Unknown stop reason: {response.stop_reason}[/yellow]"
                )
                break

        # Check if we hit max iterations
        if iteration >= self.max_iterations:
            console.print(
                "[yellow]Warning: Hit maximum agentic loop iterations[/yellow]"
            )

        return final_response_text

    def display_response(self, response_text: str) -> None:
        """
        Display Claude's response with rich formatting.

        Args:
            response_text: Response text to display
        """
        if not response_text:
            console.print("[dim]No response text[/dim]")
            return

        console.print(
            Panel(
                Markdown(response_text),
                title="🤖 Claude",
                border_style="green",
                padding=(1, 2)
            )
        )

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []
        console.print("[dim]Conversation history cleared[/dim]")

    def get_history_length(self) -> int:
        """Get conversation history length."""
        return len(self.conversation_history)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"AgentOrchestrator("
            f"tools={len(self._claude_tools)}, "
            f"history={len(self.conversation_history)})"
        )
