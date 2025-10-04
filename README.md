# k8s-cli

A lightweight SkyPilot-compatible Kubernetes task launcher that uses the SkyPilot YAML specification.

## Components

- **API Server** (`src/k8s_cli/api/`): FastAPI server that handles task operations
  - `main.py`: Application initialization and configuration
  - `tasks.py`: Task-related endpoints
  - `volumes.py`: Volume-related endpoints
- **CLI** (`src/k8s_cli/cli.py`): Command-line interface for interacting with the API server
- **Kubernetes Executor** (`src/k8s_cli/k8s_executor.py`): Executes tasks on Kubernetes using kr8s
- **Task Models** (`src/k8s_cli/task_models.py`): Pydantic models for task definitions and responses

## Installation

```bash
uv sync
```

## Usage

### Start the API Server

```bash
uv run python -m k8s_cli.api.main
```

The server will start on `http://localhost:8000`.

### CLI Commands

#### Submit a Task

Create a task YAML file (e.g., `example_task.yaml`):

```yaml
name: my-training-job
num_nodes: 1
resources:
  cpus: "2"
  memory: "4Gi"
  accelerators: "1"
envs:
  BATCH_SIZE: "32"
  EPOCHS: "10"
setup: |
  pip install numpy pandas torch
run: |
  python train.py
```

Submit the task:

```bash
uv run k8s-cli submit example_task.yaml
```

#### List Tasks

```bash
uv run k8s-cli list
```

With details:

```bash
uv run k8s-cli list --details
```

#### Check Task Status

```bash
uv run k8s-cli status <task-id>
```

#### Stop a Task

```bash
uv run k8s-cli stop <task-id>
```

### Environment Variables

- `SKY_K8S_API_URL`: API server URL (default: `http://localhost:8000`)

## API Endpoints

- `POST /tasks/submit` - Submit a new task
- `GET /tasks` - List all tasks
- `GET /tasks/{task_id}` - Get task status
- `POST /tasks/{task_id}/stop` - Stop a task

## SkyPilot YAML Support

Supported fields:

- `name` - Task name (optional)
- `num_nodes` - Number of nodes (default: 1)
- `workdir` - Working directory
- `resources` - Resource requirements
  - `cpus` - CPU requirements
  - `memory` - Memory requirements
  - `accelerators` - GPU requirements
  - `image_id` - Container image (default: python:3.11-slim)
- `envs` - Environment variables
- `setup` - Setup commands (run before main command)
- `run` - Main command to execute (required)

## Example Task

```yaml
name: data-processing
resources:
  cpus: "4"
  memory: "8Gi"
  image_id: "python:3.11"
envs:
  DATA_PATH: "/data/input"
  OUTPUT_PATH: "/data/output"
setup: |
  pip install pandas scikit-learn
run: |
  python process_data.py --input $DATA_PATH --output $OUTPUT_PATH
```

## Requirements

- Kubernetes cluster access
- Python 3.11+
- kr8s configured with cluster credentials
