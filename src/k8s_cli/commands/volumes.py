"""Volume management commands"""
from typing import Optional

import httpx
import typer
from rich.table import Table

from .utils import console, get_api_url, get_user_header, handle_api_error

volumes_app = typer.Typer(help="Manage volumes (PVCs)")


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
