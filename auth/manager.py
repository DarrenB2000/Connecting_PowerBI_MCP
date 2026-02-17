"""
Authentication manager for PowerBI MCP CLI.

Handles Microsoft OAuth authentication using MSAL device code flow.
"""
from pathlib import Path
from typing import Optional, Dict, Any

from msal import PublicClientApplication
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .token_cache import TokenCache


console = Console()


class AuthenticationError(Exception):
    """Exception raised for authentication errors."""
    pass


class AuthManager:
    """
    Manages Microsoft authentication for PowerBI access.

    Supports device code flow for CLI authentication with automatic
    token caching and refresh.
    """

    # Well-known client ID for PowerBI (public client)
    # This is a commonly used client ID for PowerBI access
    # Users can override with their own client ID if needed
    DEFAULT_CLIENT_ID = "ea0616ba-638b-4df5-95b9-636659ae5121"

    def __init__(
        self,
        client_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        scopes: Optional[list[str]] = None,
        cache_path: Optional[Path] = None,
        authority_host: str = "https://login.microsoftonline.com"
    ):
        """
        Initialize authentication manager.

        Args:
            client_id: Azure AD client ID (uses default if None)
            tenant_id: Azure AD tenant ID (uses 'common' if None)
            scopes: OAuth scopes (defaults to PowerBI scopes)
            cache_path: Path to token cache file
            authority_host: Microsoft authority host URL
        """
        self.client_id = client_id or self.DEFAULT_CLIENT_ID
        self.tenant_id = tenant_id or "common"
        self.scopes = scopes or ["https://analysis.windows.net/powerbi/api/.default"]
        self.authority_host = authority_host

        # Token cache
        if cache_path is None:
            cache_path = Path.home() / ".powerbi-mcp" / "token_cache.bin"
        self.token_cache = TokenCache(cache_path)

        # MSAL application
        self.authority = f"{self.authority_host}/{self.tenant_id}"
        self.app = PublicClientApplication(
            client_id=self.client_id,
            authority=self.authority
        )

        self._current_user = None

    def get_token(self, force_refresh: bool = False) -> str:
        """
        Get valid access token.

        Tries cached token first, then refresh token, then device code flow.

        Args:
            force_refresh: Force re-authentication even if token is cached

        Returns:
            Valid access token

        Raises:
            AuthenticationError: If authentication fails
        """
        # Check cache unless force refresh
        if not force_refresh:
            cached_token = self.token_cache.get_valid_token()
            if cached_token:
                console.print("[dim]Using cached authentication token[/dim]")
                return cached_token

        # Try to refresh token
        refresh_token = self.token_cache.get_refresh_token()
        if refresh_token and not force_refresh:
            console.print("[dim]Refreshing authentication token...[/dim]")
            try:
                refreshed_token = self._refresh_token(refresh_token)
                if refreshed_token:
                    return refreshed_token
            except Exception as e:
                console.print(f"[yellow]Token refresh failed: {e}[/yellow]")

        # Need to authenticate
        return self.authenticate_device_code_flow()

    def authenticate_device_code_flow(self) -> str:
        """
        Authenticate using device code flow.

        Returns:
            Access token

        Raises:
            AuthenticationError: If authentication fails
        """
        console.print(
            Panel.fit(
                "[bold cyan]Microsoft Authentication Required[/bold cyan]\n\n"
                "You'll need to sign in with your Microsoft account to access PowerBI.",
                border_style="cyan"
            )
        )

        try:
            # Initiate device code flow
            flow = self.app.initiate_device_flow(scopes=self.scopes)

            if "user_code" not in flow:
                raise AuthenticationError(
                    f"Failed to initiate device code flow: {flow.get('error_description', 'Unknown error')}"
                )

            # Display instructions to user
            console.print()
            console.print(
                f"[bold cyan]1.[/bold cyan] Open your browser and visit: "
                f"[bold blue]{flow['verification_uri']}[/bold blue]"
            )
            console.print(
                f"[bold cyan]2.[/bold cyan] Enter this code: "
                f"[bold yellow]{flow['user_code']}[/bold yellow]"
            )
            console.print()

            # Poll for completion with spinner
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task(
                    "Waiting for you to complete authentication in browser...",
                    total=None
                )

                result = self.app.acquire_token_by_device_flow(flow)

            console.print()

            # Check result
            if "access_token" not in result:
                error_msg = result.get("error_description", "Unknown error")
                raise AuthenticationError(f"Authentication failed: {error_msg}")

            # Extract user info
            if "id_token_claims" in result:
                claims = result["id_token_claims"]
                self._current_user = claims.get("preferred_username") or claims.get("email")

            # Cache token
            self._cache_token_result(result)

            # Success message
            if self._current_user:
                console.print(
                    f"[green]✓[/green] Successfully authenticated as: "
                    f"[bold]{self._current_user}[/bold]"
                )
            else:
                console.print("[green]✓[/green] Successfully authenticated!")

            return result["access_token"]

        except KeyboardInterrupt:
            console.print("\n[yellow]Authentication cancelled by user[/yellow]")
            raise AuthenticationError("Authentication cancelled")
        except Exception as e:
            if isinstance(e, AuthenticationError):
                raise
            raise AuthenticationError(f"Authentication error: {e}")

    def _refresh_token(self, refresh_token: str) -> Optional[str]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token

        Returns:
            New access token, or None if refresh failed
        """
        try:
            result = self.app.acquire_token_by_refresh_token(
                refresh_token=refresh_token,
                scopes=self.scopes
            )

            if "access_token" in result:
                # Cache new token
                self._cache_token_result(result)
                console.print("[green]✓[/green] Token refreshed successfully")
                return result["access_token"]

            return None

        except Exception as e:
            console.print(f"[yellow]Token refresh failed: {e}[/yellow]")
            return None

    def _cache_token_result(self, result: Dict[str, Any]) -> None:
        """
        Cache token result from MSAL.

        Args:
            result: Token result from MSAL
        """
        self.token_cache.save_token(
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token"),
            expires_in=result.get("expires_in"),
            token_type=result.get("token_type", "Bearer"),
            scope=result.get("scope"),
            id_token=result.get("id_token"),
        )

    def logout(self) -> bool:
        """
        Logout and clear cached tokens.

        Returns:
            True if logout successful, False otherwise
        """
        cleared = self.token_cache.clear_cache()

        if cleared:
            console.print("[green]✓[/green] Logged out successfully")
            console.print("[dim]Token cache cleared[/dim]")
            self._current_user = None
            return True
        else:
            console.print("[yellow]No cached tokens to clear[/yellow]")
            return False

    def get_token_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about cached token.

        Returns:
            Token info dict, or None if no token cached
        """
        return self.token_cache.get_token_info()

    def is_authenticated(self) -> bool:
        """
        Check if user is authenticated with a valid token.

        Returns:
            True if authenticated with valid token, False otherwise
        """
        token = self.token_cache.get_valid_token()
        return token is not None

    def get_current_user(self) -> Optional[str]:
        """
        Get current authenticated user.

        Returns:
            User email/username, or None if not authenticated
        """
        # Try to get from cached token
        token_data = self.token_cache.load_token()
        if token_data and "id_token" in token_data:
            # Would need to decode JWT to get user info
            # For now, return cached user from authentication
            pass

        return self._current_user

    @property
    def using_default_client_id(self) -> bool:
        """Check if using default client ID."""
        return self.client_id == self.DEFAULT_CLIENT_ID

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"AuthManager(client_id={self.client_id[:8]}..., "
            f"tenant={self.tenant_id}, "
            f"authenticated={self.is_authenticated()})"
        )
