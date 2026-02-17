"""
Configuration management for PowerBI MCP CLI application.

Uses Pydantic for type-safe configuration with environment variable support.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ClaudeConfig(BaseModel):
    """Configuration for Claude API."""

    api_key: str = Field(..., description="Claude API key from Anthropic")
    model: str = Field(
        default="claude-opus-4-6",
        description="Claude model to use"
    )
    max_tokens: int = Field(
        default=4096,
        ge=1,
        le=200000,
        description="Maximum tokens for Claude responses"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Temperature for Claude responses"
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate Claude API key format."""
        if not v or v == "sk-ant-...":
            raise ValueError(
                "Claude API key is required. Please set CLAUDE_API_KEY in your .env file"
            )
        if not v.startswith("sk-ant-"):
            raise ValueError("Claude API key must start with 'sk-ant-'")
        return v


class PowerBIConfig(BaseModel):
    """Configuration for PowerBI MCP server."""

    mcp_url: str = Field(
        default="https://api.fabric.microsoft.com/v1/mcp/powerbi",
        description="PowerBI MCP server URL"
    )

    @field_validator("mcp_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate MCP server URL format."""
        if not v.startswith("https://"):
            raise ValueError("PowerBI MCP URL must use HTTPS")
        return v


class AzureConfig(BaseModel):
    """Configuration for Microsoft Azure authentication."""

    tenant_id: Optional[str] = Field(
        default=None,
        description="Azure AD Tenant ID (optional for device code flow)"
    )
    client_id: Optional[str] = Field(
        default=None,
        description="Azure AD Client ID (optional for device code flow)"
    )
    scopes: list[str] = Field(
        default_factory=lambda: ["https://analysis.windows.net/powerbi/api/.default"],
        description="OAuth scopes for PowerBI access"
    )

    # Common tenant for multi-tenant apps
    authority_host: str = Field(
        default="https://login.microsoftonline.com",
        description="Microsoft authority host"
    )

    @property
    def authority(self) -> str:
        """Get the full authority URL."""
        tenant = self.tenant_id or "common"
        return f"{self.authority_host}/{tenant}"

    @property
    def use_device_code_flow(self) -> bool:
        """Determine if device code flow should be used."""
        # If no client_id is provided, we'll use device code flow with common tenant
        return self.client_id is None or self.tenant_id is None


class AppConfig(BaseModel):
    """Application-level configuration."""

    token_cache_dir: Path = Field(
        default_factory=lambda: Path.home() / ".powerbi-mcp",
        description="Directory for token cache and app data"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    log_file: Optional[Path] = Field(
        default=None,
        description="Log file path (if None, logs to console only)"
    )
    conversation_history_limit: int = Field(
        default=50,
        ge=1,
        description="Maximum conversation history items to maintain"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v_upper

    @property
    def token_cache_path(self) -> Path:
        """Get the full token cache file path."""
        return self.token_cache_dir / "token_cache.bin"

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.token_cache_dir.mkdir(parents=True, exist_ok=True)
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Nested configuration sections (populated in __init__)
    claude: Optional[ClaudeConfig] = Field(default=None)
    powerbi: Optional[PowerBIConfig] = Field(default=None)
    azure: Optional[AzureConfig] = Field(default=None)
    app: Optional[AppConfig] = Field(default=None)

    def __init__(self, **kwargs):
        """Initialize settings with environment variable support."""
        # Load environment variables first (this loads .env file)
        super().__init__(**kwargs)

        # Load dotenv explicitly to ensure .env is loaded
        from dotenv import load_dotenv
        load_dotenv()

        # Create Claude config
        self.claude = ClaudeConfig(
            api_key=os.getenv("CLAUDE_API_KEY", ""),
            model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5"),
            max_tokens=int(os.getenv("CLAUDE_MAX_TOKENS", "4096")),
            temperature=float(os.getenv("CLAUDE_TEMPERATURE", "0.7"))
        )

        # Create PowerBI config
        self.powerbi = PowerBIConfig(
            mcp_url=os.getenv(
                "POWERBI_MCP_URL",
                "https://api.fabric.microsoft.com/v1/mcp/powerbi"
            )
        )

        # Create Azure config
        scopes_env = os.getenv("AZURE_SCOPES")
        self.azure = AzureConfig(
            tenant_id=os.getenv("AZURE_TENANT_ID"),
            client_id=os.getenv("AZURE_CLIENT_ID"),
            scopes=scopes_env.split(",") if scopes_env else ["https://analysis.windows.net/powerbi/api/.default"]
        )

        # Create App config
        token_cache_dir = os.getenv("TOKEN_CACHE_DIR")
        self.app = AppConfig(
            token_cache_dir=Path(token_cache_dir) if token_cache_dir else Path.home() / ".powerbi-mcp",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=Path(os.getenv("LOG_FILE")) if os.getenv("LOG_FILE") else None,
            conversation_history_limit=int(os.getenv("CONVERSATION_HISTORY_LIMIT", "50"))
        )

        # Ensure required directories exist
        self.app.ensure_directories()

    @classmethod
    def load_from_env(cls) -> "Settings":
        """Load settings from environment variables and .env file."""
        return cls()

    def model_dump_json_safe(self) -> dict:
        """Export settings to dict, excluding sensitive data."""
        data = self.model_dump()
        # Mask API key
        if "claude" in data and "api_key" in data["claude"]:
            api_key = data["claude"]["api_key"]
            data["claude"]["api_key"] = f"{api_key[:10]}...{api_key[-4:]}"
        return data


# Global settings instance (lazy loaded)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings.load_from_env()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global _settings
    _settings = Settings.load_from_env()
    return _settings
