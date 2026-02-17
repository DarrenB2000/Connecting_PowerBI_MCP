"""
Async operation wrapper for Streamlit.

Provides a bridge between Streamlit's synchronous execution model
and the async backend components (orchestrator, clients).
"""

import asyncio
import threading
from typing import Awaitable, TypeVar, Optional

T = TypeVar('T')


class AsyncRunner:
    """
    Thread-safe async operation runner for Streamlit.

    Uses a single persistent event loop running in a dedicated daemon thread.
    This ensures that all async operations (MCP connection, tool calls, Claude API)
    share the same event loop, preventing "Event loop is closed" errors that
    occur when httpx.AsyncClient is created in one loop and reused in another.
    """

    _loop: Optional[asyncio.AbstractEventLoop] = None
    _thread: Optional[threading.Thread] = None
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def _get_loop(cls) -> asyncio.AbstractEventLoop:
        """
        Get or create the persistent event loop.

        Thread-safe: uses a lock to prevent race conditions during creation.
        The loop runs forever in a daemon thread until the process exits.
        """
        with cls._lock:
            if cls._loop is None or cls._loop.is_closed():
                cls._loop = asyncio.new_event_loop()
                cls._thread = threading.Thread(
                    target=cls._loop.run_forever,
                    daemon=True,
                    name="AsyncRunner-PersistentLoop"
                )
                cls._thread.start()
        return cls._loop

    def run(self, coro: Awaitable[T]) -> T:
        """
        Run async coroutine on the persistent event loop.

        Submits the coroutine to the shared persistent loop and blocks
        until completion. Safe to call from any thread.

        Args:
            coro: Async coroutine to execute

        Returns:
            Result from the coroutine

        Raises:
            Any exception raised by the coroutine
        """
        loop = self._get_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=300)  # 5 minute timeout
