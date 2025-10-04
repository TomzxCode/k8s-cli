#!/usr/bin/env python3
import typer
import httpx
import yaml
from pathlib import Path
from rich.console import Console
from rich.table import Table
from typing import Optional

app = typer.Typer(
    name="sky-k8s",
    help="SkyPilot-compatible Kubernetes task launcher CLI"
)
console = Console()

# Default API server URL
DEFAULT_API_URL = "http://localhost:8000"


def get_api_url() -> str:
    """Get API server URL from environment or use default"""
    import os
    return os.environ.get("SKY_K8S_API_URL", DEFAULT_API_URL)


def handle_api_error(e: Exception) -> None:
    """Handle API errors and exit"""
    if isinstance(e, httpx.HTTPStatusError):
        try:
            error_detail = e.response.json().get('detail', e.response.text)
        except:
            error_detail = e.response.text
        console.print(f"[red]Error: {error_detail}[/red]")
    elif isinstance(e, httpx.HTTPError):
        console.print(f"[red]Error communicating with API server: {e}[/red]")
    else:
        console.print(f"[red]Error: {e}[/red]")
    raise typer.Exit(1)


@app.command()
def submit(
    task_file: Path = typer.Argument(..., help="Path to task YAML file"),
    api_url: Optional[str] = typer.Option(None, "--api-url", "-u", help="API server URL")
):
    """
    Submit a task from a YAML file

    Example:
        sky-k8s submit task.yaml
    """
    url = api_url or get_api_url()

    if not task_file.exists():
        console.print(f"[red]Error: Task file {task_file} not found[/red]")
        raise typer.Exit(1)

    try:
        # Load YAML file
        with open(task_file, 'r') as f:
            task_data = yaml.safe_load(f)

        # Validate run command exists
        if 'run' not in task_data:
            console.print("[red]Error: 'run' field is required in task definition[/red]")
            raise typer.Exit(1)

        # Submit task to API
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{url}/tasks/submit", json=task_data)
            response.raise_for_status()
            result = response.json()

        console.print(f"[green]✓ Task submitted successfully[/green]")
        console.print(f"  Task ID: [cyan]{result['task_id']}[/cyan]")
        console.print(f"  Status: {result['status']}")

    except yaml.YAMLError as e:
        console.print(f"[red]Error parsing YAML file: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        handle_api_error(e)


@app.command()
def stop(
    task_id: str = typer.Argument(..., help="Task ID to stop"),
    api_url: Optional[str] = typer.Option(None, "--api-url", "-u", help="API server URL")
):
    """
    Stop a running task

    Example:
        sky-k8s stop abc123
    """
    url = api_url or get_api_url()

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{url}/tasks/{task_id}/stop")
            response.raise_for_status()
            result = response.json()

        console.print(f"[green]✓ Task stopped successfully[/green]")
        console.print(f"  Task ID: [cyan]{result['task_id']}[/cyan]")
        console.print(f"  Status: {result['status']}")

    except Exception as e:
        handle_api_error(e)


@app.command()
def list(
    api_url: Optional[str] = typer.Option(None, "--api-url", "-u", help="API server URL"),
    show_details: bool = typer.Option(False, "--details", "-d", help="Show detailed information")
):
    """
    List all tasks

    Example:
        sky-k8s list
        sky-k8s list --details
    """
    url = api_url or get_api_url()

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{url}/tasks")
            response.raise_for_status()
            result = response.json()

        tasks = result.get('tasks', [])

        if not tasks:
            console.print("[yellow]No tasks found[/yellow]")
            return

        # Create table
        table = Table(title="Tasks")
        table.add_column("Task ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Created", style="blue")

        if show_details:
            table.add_column("Job Name", style="yellow")
            table.add_column("Namespace", style="white")

        for task in tasks:
            row = [
                task['task_id'],
                task.get('name') or '-',
                task['status'],
                task['created_at'][:19] if task.get('created_at') else '-'
            ]

            if show_details and task.get('metadata'):
                row.extend([
                    task['metadata'].get('job_name', '-'),
                    task['metadata'].get('namespace', '-')
                ])

            table.add_row(*row)

        console.print(table)
        console.print(f"\nTotal tasks: {len(tasks)}")

    except Exception as e:
        handle_api_error(e)


@app.command()
def status(
    task_id: str = typer.Argument(..., help="Task ID to check"),
    api_url: Optional[str] = typer.Option(None, "--api-url", "-u", help="API server URL")
):
    """
    Get status of a specific task

    Example:
        sky-k8s status abc123
    """
    url = api_url or get_api_url()

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{url}/tasks/{task_id}")
            response.raise_for_status()
            task = response.json()

        console.print(f"[bold]Task Details[/bold]")
        console.print(f"  Task ID: [cyan]{task['task_id']}[/cyan]")
        console.print(f"  Name: {task.get('name') or '-'}")
        console.print(f"  Status: [green]{task['status']}[/green]")
        console.print(f"  Created: {task.get('created_at', '-')}")
        console.print(f"  Updated: {task.get('updated_at', '-')}")

        if task.get('metadata'):
            console.print(f"\n[bold]Metadata[/bold]")
            for key, value in task['metadata'].items():
                console.print(f"  {key}: {value}")

    except Exception as e:
        handle_api_error(e)


if __name__ == "__main__":
    app()
