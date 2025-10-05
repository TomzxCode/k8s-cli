"""Authentication commands"""

import typer

from .utils import console, get_current_user, save_user

auth_app = typer.Typer(help="Authentication commands")


@auth_app.command()
def login(username: str = typer.Argument(..., help="Username to log in as")):
    """
    Log in as a user

    Example:
        k8s-cli auth login myusername
    """
    try:
        save_user(username)
        console.print(f"[green]✓ Logged in as: [cyan]{username}[/cyan][/green]")
    except Exception as e:
        console.print(f"[red]Error: Failed to save user: {e}[/red]")
        raise typer.Exit(1)


@auth_app.command()
def whoami():
    """
    Show current logged-in user

    Example:
        k8s-cli auth whoami
    """
    user = get_current_user()
    if user:
        console.print(f"Logged in as: [cyan]{user}[/cyan]")
    else:
        console.print("[yellow]Not logged in[/yellow]")
