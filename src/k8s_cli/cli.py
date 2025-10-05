#!/usr/bin/env python3
import typer

from .commands.auth import auth_app
from .commands.jobs import jobs_app
from .commands.volumes import volumes_app

app = typer.Typer(name="k8s-cli", help="SkyPilot-compatible Kubernetes task launcher CLI", no_args_is_help=True)
app.add_typer(auth_app, name="auth", no_args_is_help=True)
app.add_typer(jobs_app, name="jobs", no_args_is_help=True)
app.add_typer(volumes_app, name="volumes", no_args_is_help=True)


if __name__ == "__main__":
    app()
