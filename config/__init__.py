"""
Configuration module for PowerBI MCP CLI.

Provides type-safe configuration management with environment variable support.
"""

from .settings import (
    Settings,
    ClaudeConfig,
    PowerBIConfig,
    AzureConfig,
    AppConfig,
    get_settings,
    reload_settings,
)

from .helpers import (
    check_env_file,
    create_env_from_template,
    validate_configuration,
    display_configuration,
    save_config_to_json,
    load_config_from_json,
    interactive_setup,
    get_or_create_settings,
)

__all__ = [
    # Settings classes
    "Settings",
    "ClaudeConfig",
    "PowerBIConfig",
    "AzureConfig",
    "AppConfig",
    "get_settings",
    "reload_settings",
    # Helper functions
    "check_env_file",
    "create_env_from_template",
    "validate_configuration",
    "display_configuration",
    "save_config_to_json",
    "load_config_from_json",
    "interactive_setup",
    "get_or_create_settings",
]
