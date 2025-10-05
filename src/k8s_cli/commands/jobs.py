"""Job management commands"""
from pathlib import Path
from typing import Optional

import httpx
import typer
import yaml
from rich.table import Table

from .utils import console, get_api_url, get_user_header, handle_api_error

jobs_app = typer.Typer(help="Manage jobs (tasks)")


@jobs_app.command()
def submit(
    task_file: Path = typer.Argument(..., help="Path to task YAML file"),
    api_url: Optional[str] = typer.Option(
        None, "--api-url", "-u", help="API server URL"
    ),
    detach: bool = typer.Option(
        False, "--detach", "-d", help="Submit job without tailing logs"
    ),
):
    """
    Submit a task from a YAML file

    Example:
        k8s-cli jobs submit task.yaml
        k8s-cli jobs submit task.yaml --detach
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

        # Tail logs unless detached
        if not detach:
            _tail_task_logs(result['task_id'], url)

    except yaml.YAMLError as e:
        console.print(f"[red]Error parsing YAML file: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        handle_api_error(e)


def _tail_task_logs(task_id: str, api_url: str):
    """Internal helper to tail logs for a task"""
    try:
        console.print(f"\n[blue]Tailing logs for task {task_id}...[/blue]")
        console.print("[dim]Press Ctrl+C to stop tailing logs[/dim]\n")

        with httpx.Client(timeout=None) as client:
            with client.stream("GET", f"{api_url}/tasks/{task_id}/logs", headers=get_user_header()) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        console.print(line)

    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped tailing logs[/yellow]")
    except Exception as e:
        console.print(f"[yellow]Warning: Could not tail logs: {e}[/yellow]")


@jobs_app.command()
def stop(
    task_id: Optional[str] = typer.Argument(None, help="Task ID to stop"),
    api_url: Optional[str] = typer.Option(
        None, "--api-url", help="API server URL"
    ),
    all_tasks: bool = typer.Option(
        False, "--all", "-a", help="Stop all tasks for current user"
    ),
    all_users: bool = typer.Option(
        False, "--all-users", "-u", help="Stop tasks for all users (requires --all)"
    ),
):
    """
    Stop a running task or all tasks

    Examples:
        k8s-cli jobs stop abc123              # Stop a specific task
        k8s-cli jobs stop --all               # Stop all tasks for current user
        k8s-cli jobs stop --all --all-users   # Stop all tasks for all users
    """
    url = api_url or get_api_url()

    # Validate arguments
    if all_users and not all_tasks:
        console.print("[red]Error: --all-users requires --all flag[/red]")
        raise typer.Exit(1)

    if not all_tasks and not task_id:
        console.print("[red]Error: Either provide a task ID or use --all flag[/red]")
        raise typer.Exit(1)

    if all_tasks and task_id:
        console.print("[red]Error: Cannot specify task ID with --all flag[/red]")
        raise typer.Exit(1)

    try:
        with httpx.Client(timeout=30.0) as client:
            if all_tasks:
                # Stop all tasks
                params = {"all_users": "true"} if all_users else {}
                response = client.post(f"{url}/tasks/stop", headers=get_user_header(), params=params)
                response.raise_for_status()
                result = response.json()

                console.print("[green]✓ Tasks stopped successfully[/green]")
                console.print(f"  Count: [cyan]{result['count']}[/cyan]")
                console.print(f"  Status: {result['status']}")
            else:
                # Stop single task
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


@jobs_app.command()
def logs(
    task_id: str = typer.Argument(..., help="Task ID to view logs for"),
    api_url: Optional[str] = typer.Option(
        None, "--api-url", "-u", help="API server URL"
    ),
):
    """
    Tail logs from a running or completed task

    Example:
        k8s-cli jobs logs abc123
    """
    url = api_url or get_api_url()
    _tail_task_logs(task_id, url)
