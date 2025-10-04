#!/usr/bin/env python3
import json
from pathlib import Path
from typing import Optional

import httpx
import typer
import yaml
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="k8s-cli", help="SkyPilot-compatible Kubernetes task launcher CLI"
)
jobs_app = typer.Typer(help="Manage jobs (tasks)")
app.add_typer(jobs_app, name="jobs")
volumes_app = typer.Typer(help="Manage volumes (PVCs)")
app.add_typer(volumes_app, name="volumes")
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
        console.print("[red]Error: Not logged in. Run 'k8s-cli login <username>' first[/red]")
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


@app.command()
def login(username: str = typer.Argument(..., help="Username to log in as")):
    """
    Log in as a user

    Example:
        k8s-cli login myusername
    """
    try:
        save_user(username)
        console.print(f"[green]✓ Logged in as: [cyan]{username}[/cyan][/green]")
    except Exception as e:
        console.print(f"[red]Error: Failed to save user: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def whoami():
    """
    Show current logged-in user

    Example:
        k8s-cli whoami
    """
    user = get_current_user()
    if user:
        console.print(f"Logged in as: [cyan]{user}[/cyan]")
    else:
        console.print("[yellow]Not logged in[/yellow]")


@jobs_app.command()
def submit(
    task_file: Path = typer.Argument(..., help="Path to task YAML file"),
    api_url: Optional[str] = typer.Option(
        None, "--api-url", "-u", help="API server URL"
    ),
):
    """
    Submit a task from a YAML file

    Example:
        k8s-cli jobs submit task.yaml
    """
    url = api_url or get_api_url()

    if not task_file.exists():
        console.print(f"[red]Error: Task file {task_file} not found[/red]")
        raise typer.Exit(1)

    try:
        # Load YAML file
        with open(task_file, "r") as f:
            task_data = yaml.safe_load(f)

        # Validate run command exists
        if "run" not in task_data:
            console.print(
                "[red]Error: 'run' field is required in task definition[/red]"
            )
            raise typer.Exit(1)

        # Submit task to API
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{url}/tasks/submit", json=task_data, headers=get_user_header())
            response.raise_for_status()
            result = response.json()

        console.print("[green]✓ Task submitted successfully[/green]")
        console.print(f"  Task ID: [cyan]{result['task_id']}[/cyan]")
        console.print(f"  Status: {result['status']}")

    except yaml.YAMLError as e:
        console.print(f"[red]Error parsing YAML file: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        handle_api_error(e)


@jobs_app.command()
def stop(
    task_id: str = typer.Argument(..., help="Task ID to stop"),
    api_url: Optional[str] = typer.Option(
        None, "--api-url", "-u", help="API server URL"
    ),
):
    """
    Stop a running task

    Example:
        k8s-cli jobs stop abc123
    """
    url = api_url or get_api_url()

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{url}/tasks/{task_id}/stop", headers=get_user_header())
            response.raise_for_status()
            result = response.json()

        console.print("[green]✓ Task stopped successfully[/green]")
        console.print(f"  Task ID: [cyan]{result['task_id']}[/cyan]")
        console.print(f"  Status: {result['status']}")

    except Exception as e:
        handle_api_error(e)


@jobs_app.command()
def list(
    api_url: Optional[str] = typer.Option(
        None, "--api-url", help="API server URL"
    ),
    show_details: bool = typer.Option(
        False, "--details", "-d", help="Show detailed information"
    ),
    all_users: bool = typer.Option(
        False, "--all-users", "-u", help="List tasks from all users"
    ),
):
    """
    List all tasks

    Example:
        k8s-cli jobs list
        k8s-cli jobs list --details
        k8s-cli jobs list -u  # List tasks from all users
    """
    url = api_url or get_api_url()

    try:
        with httpx.Client(timeout=30.0) as client:
            params = {"all_users": "true"} if all_users else {}
            response = client.get(f"{url}/tasks", headers=get_user_header(), params=params)
            response.raise_for_status()
            result = response.json()

        tasks = result.get("tasks", [])

        if not tasks:
            console.print("[yellow]No tasks found[/yellow]")
            return

        # Create table
        table = Table(title="Tasks")
        table.add_column("Task ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Created", style="blue")

        if all_users:
            table.add_column("User", style="yellow")

        if show_details:
            table.add_column("Job Name", style="yellow")
            table.add_column("Namespace", style="white")

        for task in tasks:
            row = [
                task["task_id"],
                task.get("name") or "-",
                task["status"],
                task["created_at"][:19] if task.get("created_at") else "-",
            ]

            if all_users:
                row.append(task.get("username", "-"))

            if show_details and task.get("metadata"):
                row.extend(
                    [
                        task["metadata"].get("job_name", "-"),
                        task["metadata"].get("namespace", "-"),
                    ]
                )

            table.add_row(*row)

        console.print(table)
        console.print(f"\nTotal tasks: {len(tasks)}")

    except Exception as e:
        handle_api_error(e)


@jobs_app.command()
def status(
    task_id: str = typer.Argument(..., help="Task ID to check"),
    api_url: Optional[str] = typer.Option(
        None, "--api-url", "-u", help="API server URL"
    ),
):
    """
    Get status of a specific task

    Example:
        k8s-cli jobs status abc123
    """
    url = api_url or get_api_url()

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{url}/tasks/{task_id}", headers=get_user_header())
            response.raise_for_status()
            task = response.json()

        console.print("[bold]Task Details[/bold]")
        console.print(f"  Task ID: [cyan]{task['task_id']}[/cyan]")
        console.print(f"  Name: {task.get('name') or '-'}")
        console.print(f"  Status: [green]{task['status']}[/green]")
        console.print(f"  Created: {task.get('created_at', '-')}")
        console.print(f"  Updated: {task.get('updated_at', '-')}")

        if task.get("metadata"):
            console.print("\n[bold]Metadata[/bold]")
            for key, value in task["metadata"].items():
                console.print(f"  {key}: {value}")

    except Exception as e:
        handle_api_error(e)


@volumes_app.command("create")
def volumes_create(
    name: str = typer.Argument(..., help="Volume name"),
    size: str = typer.Argument(..., help="Volume size (e.g., '10Gi', '1Ti')"),
    storage_class: Optional[str] = typer.Option(
        None, "--storage-class", "-s", help="Storage class name"
    ),
    access_modes: Optional[str] = typer.Option(
        "ReadWriteOnce", "--access-modes", "-a", help="Access modes (comma-separated)"
    ),
    api_url: Optional[str] = typer.Option(
        None, "--api-url", help="API server URL"
    ),
):
    """
    Create a new volume (PVC)

    Example:
        k8s-cli volumes create my-volume 10Gi
        k8s-cli volumes create data-vol 5Gi --storage-class fast-ssd
        k8s-cli volumes create shared 20Gi -a ReadWriteMany
    """
    url = api_url or get_api_url()

    try:
        volume_data = {
            "name": name,
            "size": size,
        }

        if storage_class:
            volume_data["storage_class"] = storage_class

        if access_modes:
            volume_data["access_modes"] = [mode.strip() for mode in access_modes.split(",")]

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{url}/volumes/create",
                json=volume_data,
                headers=get_user_header()
            )
            response.raise_for_status()
            result = response.json()

        console.print("[green]✓ Volume created successfully[/green]")
        console.print(f"  Volume ID: [cyan]{result['volume_id']}[/cyan]")
        console.print(f"  Status: {result['status']}")

    except Exception as e:
        handle_api_error(e)


@volumes_app.command("list")
def volumes_list(
    api_url: Optional[str] = typer.Option(
        None, "--api-url", help="API server URL"
    ),
    show_details: bool = typer.Option(
        False, "--details", "-d", help="Show detailed information"
    ),
    all_users: bool = typer.Option(
        False, "--all-users", "-u", help="List volumes from all users"
    ),
):
    """
    List all volumes

    Example:
        k8s-cli volumes list
        k8s-cli volumes list --details
        k8s-cli volumes list -u  # List volumes from all users
    """
    url = api_url or get_api_url()

    try:
        with httpx.Client(timeout=30.0) as client:
            params = {"all_users": "true"} if all_users else {}
            response = client.get(f"{url}/volumes", headers=get_user_header(), params=params)
            response.raise_for_status()
            result = response.json()

        volumes = result.get("volumes", [])

        if not volumes:
            console.print("[yellow]No volumes found[/yellow]")
            return

        # Create table
        table = Table(title="Volumes")
        table.add_column("Volume ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Size", style="blue")
        table.add_column("Status", style="green")
        table.add_column("Created", style="yellow")

        if all_users:
            table.add_column("User", style="yellow")

        if show_details:
            table.add_column("Storage Class", style="white")
            table.add_column("Access Modes", style="white")
            table.add_column("PVC Name", style="white")

        for volume in volumes:
            row = [
                volume["volume_id"],
                volume.get("name") or "-",
                volume.get("size", "-"),
                volume["status"],
                volume["created_at"][:19] if volume.get("created_at") else "-",
            ]

            if all_users:
                row.append(volume.get("username", "-"))

            if show_details:
                row.extend([
                    volume.get("storage_class") or "-",
                    ", ".join(volume.get("access_modes", [])),
                    volume.get("metadata", {}).get("pvc_name", "-"),
                ])

            table.add_row(*row)

        console.print(table)
        console.print(f"\nTotal volumes: {len(volumes)}")

    except Exception as e:
        handle_api_error(e)


@volumes_app.command("delete")
def volumes_delete(
    volume_id: str = typer.Argument(..., help="Volume ID to delete"),
    api_url: Optional[str] = typer.Option(
        None, "--api-url", help="API server URL"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Skip confirmation"
    ),
):
    """
    Delete a volume

    Example:
        k8s-cli volumes delete abc123
        k8s-cli volumes delete abc123 --force
    """
    url = api_url or get_api_url()

    if not force:
        confirm = typer.confirm(f"Are you sure you want to delete volume {volume_id}?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            return

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.delete(
                f"{url}/volumes/{volume_id}",
                headers=get_user_header()
            )
            response.raise_for_status()
            result = response.json()

        console.print("[green]✓ Volume deleted successfully[/green]")
        console.print(f"  Volume ID: [cyan]{result['volume_id']}[/cyan]")
        console.print(f"  Status: {result['status']}")

    except Exception as e:
        handle_api_error(e)


if __name__ == "__main__":
    app()
