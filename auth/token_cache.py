"""
Token cache management for PowerBI MCP CLI.

Handles secure storage and retrieval of OAuth tokens.
"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

from rich.console import Console

console = Console()


class TokenCache:
    """
    Manages OAuth token caching and retrieval.

    Tokens are stored as JSON with metadata including expiry time.
    """

    def __init__(self, cache_path: Path):
        """
        Initialize token cache.

        Args:
            cache_path: Path to token cache file
        """
        self.cache_path = Path(cache_path)
        self._ensure_cache_directory()

    def _ensure_cache_directory(self) -> None:
        """Ensure cache directory exists."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

    def save_token(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: Optional[int] = None,
        token_type: str = "Bearer",
        scope: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Save token to cache.

        Args:
            access_token: OAuth access token
            refresh_token: OAuth refresh token (optional)
            expires_in: Token expiry in seconds from now
            token_type: Token type (default: Bearer)
            scope: Token scope
            **kwargs: Additional token metadata
        """
        # Calculate expiry timestamp
        if expires_in:
            expires_at = int(time.time()) + expires_in
        else:
            # Default to 1 hour if not specified
            expires_at = int(time.time()) + 3600

        token_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": token_type,
            "expires_at": expires_at,
            "expires_in": expires_in,
            "scope": scope,
            "cached_at": int(time.time()),
            "cached_at_readable": datetime.now().isoformat(),
            **kwargs
        }

        # Write to cache file
        try:
            with open(self.cache_path, "w") as f:
                json.dump(token_data, f, indent=2)

            # Set restrictive permissions (owner read/write only)
            self.cache_path.chmod(0o600)

        except Exception as e:
            console.print(f"[yellow]Warning: Could not save token cache: {e}[/yellow]")

    def load_token(self) -> Optional[Dict[str, Any]]:
        """
        Load token from cache.

        Returns:
            Token data dict if available, None if cache doesn't exist or is invalid
        """
        if not self.cache_path.exists():
            return None

        try:
            with open(self.cache_path, "r") as f:
                token_data = json.load(f)

            return token_data

        except (json.JSONDecodeError, IOError) as e:
            console.print(f"[yellow]Warning: Could not load token cache: {e}[/yellow]")
            return None

    def get_valid_token(self) -> Optional[str]:
        """
        Get valid access token from cache.

        Returns:
            Access token if valid and not expired, None otherwise
        """
        token_data = self.load_token()

        if not token_data:
            return None

        # Check if token has expired
        if self.is_token_expired(token_data):
            return None

        return token_data.get("access_token")

    def is_token_expired(
        self,
        token_data: Optional[Dict[str, Any]] = None,
        buffer_seconds: int = 300
    ) -> bool:
        """
        Check if token is expired or will expire soon.

        Args:
            token_data: Token data dict (if None, loads from cache)
            buffer_seconds: Safety buffer - consider token expired this many seconds early

        Returns:
            True if token is expired or will expire within buffer, False otherwise
        """
        if token_data is None:
            token_data = self.load_token()

        if not token_data:
            return True

        expires_at = token_data.get("expires_at")
        if not expires_at:
            # No expiry info, consider expired
            return True

        # Check if expired (with safety buffer)
        current_time = int(time.time())
        return current_time >= (expires_at - buffer_seconds)

    def get_refresh_token(self) -> Optional[str]:
        """
        Get refresh token from cache.

        Returns:
            Refresh token if available, None otherwise
        """
        token_data = self.load_token()

        if not token_data:
            return None

        return token_data.get("refresh_token")

    def clear_cache(self) -> bool:
        """
        Clear token cache.

        Returns:
            True if cache was cleared, False if cache didn't exist
        """
        if not self.cache_path.exists():
            return False

        try:
            self.cache_path.unlink()
            return True
        except Exception as e:
            console.print(f"[red]Error clearing token cache: {e}[/red]")
            return False

    def get_token_info(self) -> Optional[Dict[str, Any]]:
        """
        Get token information for display (without sensitive data).

        Returns:
            Dict with token metadata (excluding actual tokens)
        """
        token_data = self.load_token()

        if not token_data:
            return None

        expires_at = token_data.get("expires_at")
        if expires_at:
            expires_dt = datetime.fromtimestamp(expires_at)
            time_until_expiry = expires_dt - datetime.now()
            is_expired = time_until_expiry.total_seconds() <= 0
        else:
            expires_dt = None
            time_until_expiry = None
            is_expired = True

        return {
            "cached_at": token_data.get("cached_at_readable"),
            "expires_at": expires_dt.isoformat() if expires_dt else None,
            "time_until_expiry": str(time_until_expiry) if time_until_expiry else None,
            "is_expired": is_expired,
            "token_type": token_data.get("token_type"),
            "scope": token_data.get("scope"),
            "has_refresh_token": bool(token_data.get("refresh_token")),
        }

    def get_time_until_expiry(self) -> Optional[timedelta]:
        """
        Get time until token expires.

        Returns:
            timedelta until expiry, or None if no valid token
        """
        token_data = self.load_token()

        if not token_data:
            return None

        expires_at = token_data.get("expires_at")
        if not expires_at:
            return None

        expires_dt = datetime.fromtimestamp(expires_at)
        return expires_dt - datetime.now()

    def __repr__(self) -> str:
        """String representation."""
        return f"TokenCache(path={self.cache_path})"
