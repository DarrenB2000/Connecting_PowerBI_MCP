"""
Test script to verify Streamlit setup and configuration.

Run this before starting the Streamlit app to verify everything is configured correctly.
"""
import sys
from pathlib import Path

# Use ASCII-compatible characters for Windows console
CHECK = "[OK]"
CROSS = "[X]"
WARN = "[!]"


def test_imports():
    """Test that all required imports are available."""
    print("Testing imports...")

    try:
        import streamlit as st
        print(f"  {CHECK} Streamlit {st.__version__}")
    except ImportError as e:
        print(f"  {CROSS} Streamlit import failed: {e}")
        return False

    try:
        import anthropic
        print(f"  {CHECK} Anthropic {anthropic.__version__}")
    except ImportError as e:
        print(f"  {CROSS} Anthropic import failed: {e}")
        return False

    try:
        import msal
        print(f"  {CHECK} MSAL {msal.__version__}")
    except ImportError as e:
        print(f"  {CROSS} MSAL import failed: {e}")
        return False

    try:
        import httpx
        print(f"  {CHECK} HTTPX {httpx.__version__}")
    except ImportError as e:
        print(f"  {CROSS} HTTPX import failed: {e}")
        return False

    try:
        from rich.console import Console
        print(f"  {CHECK} Rich")
    except ImportError as e:
        print(f"  {CROSS} Rich import failed: {e}")
        return False

    return True


def test_module_structure():
    """Test that all required modules are present."""
    print("\nTesting module structure...")

    required_modules = [
        'streamlit_ui/__init__.py',
        'streamlit_ui/session_manager.py',
        'streamlit_ui/async_runner.py',
        'streamlit_ui/components.py',
        'streamlit_ui/display.py',
        'streamlit_app.py',
        'config/settings.py',
        'auth/manager.py',
        'clients/claude_client.py',
        'clients/simple_mcp_client.py',
        'clients/http_transport.py',
        'core/orchestrator.py',
    ]

    all_present = True
    for module_path in required_modules:
        path = Path(module_path)
        if path.exists():
            print(f"  {CHECK} {module_path}")
        else:
            print(f"  {CROSS} {module_path} - NOT FOUND")
            all_present = False

    return all_present


def test_configuration():
    """Test that configuration files are present."""
    print("\nTesting configuration...")

    config_files = [
        '.streamlit/config.toml',
        '.env',
    ]

    all_present = True
    for config_file in config_files:
        path = Path(config_file)
        if path.exists():
            print(f"  {CHECK} {config_file}")
        else:
            print(f"  {CROSS} {config_file} - NOT FOUND")
            all_present = False

    return all_present


def test_env_variables():
    """Test that required environment variables are set."""
    print("\nTesting environment variables...")

    try:
        from dotenv import load_dotenv
        import os

        load_dotenv()

        required_vars = ['CLAUDE_API_KEY']
        optional_vars = ['AZURE_TENANT_ID', 'AZURE_CLIENT_ID']

        all_set = True
        for var in required_vars:
            if os.getenv(var):
                print(f"  {CHECK} {var} is set")
            else:
                print(f"  {CROSS} {var} is NOT set")
                all_set = False

        for var in optional_vars:
            if os.getenv(var):
                print(f"  {CHECK} {var} is set (optional)")
            else:
                print(f"  {WARN} {var} is NOT set (optional - will use defaults)")

        return all_set
    except Exception as e:
        print(f"  {CROSS} Error checking environment variables: {e}")
        return False


def test_streamlit_config():
    """Test Streamlit configuration file."""
    print("\nTesting Streamlit configuration...")

    config_path = Path('.streamlit/config.toml')
    if not config_path.exists():
        print(f"  {CROSS} .streamlit/config.toml not found")
        return False

    try:
        import toml
        config = toml.load(config_path)

        # Check for required sections
        if 'server' in config:
            print(f"  {CHECK} Server config present (port: {config['server'].get('port', 'default')})")
        else:
            print(f"  {WARN} Server config section missing")

        if 'theme' in config:
            print(f"  {CHECK} Theme config present (primary: {config['theme'].get('primaryColor', 'default')})")
        else:
            print(f"  {WARN} Theme config section missing")

        return True
    except ImportError:
        print(f"  {WARN} toml package not installed, skipping detailed config check")
        print(f"  {CHECK} Config file exists")
        return True
    except Exception as e:
        print(f"  {CROSS} Error reading config: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("PowerBI MCP Streamlit Setup Verification")
    print("=" * 60)

    results = []

    results.append(("Imports", test_imports()))
    results.append(("Module Structure", test_module_structure()))
    results.append(("Configuration Files", test_configuration()))
    results.append(("Environment Variables", test_env_variables()))
    results.append(("Streamlit Config", test_streamlit_config()))

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = f"{CHECK} PASS" if passed else f"{CROSS} FAIL"
        print(f"{test_name:.<30} {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print(f"\n{CHECK} All tests passed! Ready to run: streamlit run streamlit_app.py")
        return 0
    else:
        print(f"\n{CROSS} Some tests failed. Please fix the issues above before running the app.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
