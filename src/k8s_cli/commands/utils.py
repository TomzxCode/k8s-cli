"""Common utilities for CLI commands"""
import json
from pathlib import Path
from typing import Optional

import httpx
import typer
from rich.console import Console

console = Console()

# Default API server URL
DEFAULT_API_URL = "http://localhost:8000"
# User config file
CONFIG_DIR = Path.home() / ".config" / "k8s-cli"
USER_CONFIG_FILE = CONFIG_DIR / "user.json"


def get_api_url() -> str:
    """Get API server URL from environment or use default"""
    import os

    return os.environ.get("SKY_K8S_API_URL", DEFAULT_API_URL)


def get_current_user() -> Optional[str]:
    """Get current logged-in user from config file"""
    if USER_CONFIG_FILE.exists():
        try:
            with open(USER_CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get('username')
        except:
            return None
    return None


def save_user(username: str) -> None:
    """Save username to config file"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(USER_CONFIG_FILE, 'w') as f:
        json.dump({'username': username}, f)


def get_user_header() -> dict:
    """Get user header for API requests"""
    user = get_current_user()
    if not user:
        console.print("[red]Error: Not logged in. Run 'k8s-cli auth login <username>' first[/red]")
        raise typer.Exit(1)
    return {"X-User": user}


def handle_api_error(e: Exception) -> None:
    """Handle API errors and exit"""
    if isinstance(e, httpx.HTTPStatusError):
        try:
            error_detail = e.response.json().get("detail", e.response.text)
        except Exception:
            error_detail = e.response.text
        console.print(f"[red]Error: {error_detail}[/red]")
    elif isinstance(e, httpx.HTTPError):
        console.print(f"[red]Error communicating with API server: {e}[/red]")
    else:
        console.print(f"[red]Error: {e}[/red]")
    raise typer.Exit(1)
