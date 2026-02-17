"""
HTTP POST transport for MCP.

PowerBI MCP server uses HTTP POST with JSON-RPC, not SSE.
"""
import asyncio
import json
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager

import httpx
from mcp.types import JSONRPCMessage


class HTTPTransport:
    """
    HTTP POST transport for MCP servers that use JSON-RPC over HTTP.

    Unlike SSE which uses GET for server-sent events, this transport
    uses POST requests for bidirectional JSON-RPC communication.
    """

    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0
    ):
        """
        Initialize HTTP transport.

        Args:
            url: MCP server URL
            headers: HTTP headers (including authentication)
            timeout: Request timeout in seconds
        """
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}

    async def connect(self):
        """Establish HTTP client connection."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers=self.headers
        )

    async def close(self):
        """Close HTTP client connection."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _parse_sse_response(self, sse_text: str) -> Dict[str, Any]:
        """
        Parse SSE (Server-Sent Events) formatted response.

        SSE format:
            event: message
            data: {"jsonrpc":"2.0",...}

        Args:
            sse_text: Raw SSE response text

        Returns:
            Parsed JSON data from the SSE event

        Raises:
            ValueError: If SSE format is invalid
        """
        lines = sse_text.strip().split('\n')
        data_lines = []

        for line in lines:
            line = line.strip()
            if line.startswith('data:'):
                # Extract JSON after "data:"
                json_str = line[5:].strip()
                data_lines.append(json_str)

        if not data_lines:
            raise ValueError(f"No data found in SSE response: {sse_text[:200]}")

        # Join all data lines (SSE can have multi-line data)
        json_str = ''.join(data_lines)

        # Parse JSON
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse JSON from SSE data: {e}\n"
                f"JSON string: {json_str[:200]}"
            )

    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send JSON-RPC message and receive response.

        Args:
            message: JSON-RPC message to send

        Returns:
            JSON-RPC response

        Raises:
            httpx.HTTPError: If request fails
            ValueError: If response is invalid
        """
        if not self._client:
            raise RuntimeError("Transport not connected")

        # Check if client is usable (not closed/from different event loop)
        # If there's an issue, recreate the client
        try:
            # Test if client is usable by checking if it's closed
            if self._client.is_closed:
                # Recreate client
                self._client = httpx.AsyncClient(
                    timeout=httpx.Timeout(self.timeout),
                    headers=self.headers
                )
        except RuntimeError:
            # Event loop issue - recreate client
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers=self.headers
            )

        # Ensure message has required JSON-RPC fields
        if "jsonrpc" not in message:
            message["jsonrpc"] = "2.0"

        # Add ID if not present (for requests)
        if "id" not in message and message.get("method"):
            self._request_id += 1
            message["id"] = self._request_id

        # Send POST request
        response = await self._client.post(
            self.url,
            json=message,
            headers={"Content-Type": "application/json"}
        )

        # Check for HTTP errors
        response.raise_for_status()

        # Debug: Check response content
        response_text = response.text
        if not response_text:
            raise ValueError(f"Empty response from server (status {response.status_code})")

        # Check if response is SSE format (text/event-stream)
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            # Parse SSE format: "event: message\ndata: {...}\n\n"
            response_data = self._parse_sse_response(response_text)
        else:
            # Parse as regular JSON
            try:
                response_data = response.json()
            except Exception as e:
                raise ValueError(
                    f"Failed to parse JSON response: {e}\n"
                    f"Response text: {response_text[:500]}"
                )

        # Check for JSON-RPC error
        if "error" in response_data:
            error = response_data["error"]
            raise RuntimeError(
                f"MCP error {error.get('code')}: {error.get('message')}"
            )

        return response_data

    def __aiter__(self):
        """
        Async iterator for compatibility with MCP SDK.

        Note: HTTP POST transport doesn't stream, but MCP SDK expects
        an async iterable. We'll yield messages as they come.
        """
        return self

    async def __anext__(self):
        """
        Get next message.

        For HTTP POST, this is called by the SDK to receive messages.
        Since HTTP is request-response, we don't have a continuous stream.
        """
        # This won't be used for HTTP POST as we handle send/receive directly
        raise StopAsyncIteration


class HTTPSession:
    """
    Session wrapper for HTTP POST transport.

    Provides read/write streams compatible with MCP ClientSession.
    """

    def __init__(self, transport: HTTPTransport):
        """
        Initialize session.

        Args:
            transport: HTTP transport instance
        """
        self.transport = transport
        self._write_queue: asyncio.Queue = asyncio.Queue()
        self._read_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    async def _write_loop(self):
        """Process outgoing messages."""
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._write_queue.get(),
                    timeout=0.1
                )
                response = await self.transport.send(message)
                await self._read_queue.put(response)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                if self._running:
                    await self._read_queue.put({"error": str(e)})

    async def start(self):
        """Start session loops."""
        self._running = True
        self._write_task = asyncio.create_task(self._write_loop())

    async def stop(self):
        """Stop session loops."""
        self._running = False
        if hasattr(self, '_write_task'):
            self._write_task.cancel()
            try:
                await self._write_task
            except asyncio.CancelledError:
                pass

    async def send(self, message: Dict[str, Any]):
        """Send message to server."""
        await self._write_queue.put(message)

    async def receive(self) -> Dict[str, Any]:
        """Receive message from server."""
        return await self._read_queue.get()

    def __aiter__(self):
        """Async iterator over received messages."""
        return self

    async def __anext__(self):
        """Get next received message."""
        try:
            message = await asyncio.wait_for(self._read_queue.get(), timeout=30.0)
            return message
        except asyncio.TimeoutError:
            raise StopAsyncIteration


@asynccontextmanager
async def http_mcp_client(
    url: str,
    headers: Optional[Dict[str, str]] = None
):
    """
    Create HTTP POST MCP client connection.

    Args:
        url: MCP server URL
        headers: HTTP headers (including Authorization)

    Yields:
        Tuple of (read_stream, write_stream) compatible with MCP ClientSession

    Example:
        async with http_mcp_client(url, headers) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
    """
    transport = HTTPTransport(url, headers)

    try:
        await transport.connect()
        session = HTTPSession(transport)
        await session.start()

        # Yield read and write streams
        yield (session, session)

    finally:
        await session.stop()
        await transport.close()
