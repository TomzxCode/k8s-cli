# SkyPilot-Compatible Kubernetes Task Launcher

A lightweight alternative to SkyPilot that launches tasks on Kubernetes using the SkyPilot YAML specification.

## Components

- **API Server** (`api_server.py`): FastAPI server that handles task operations
- **CLI** (`cli.py`): Command-line interface for interacting with the API server
- **Kubernetes Executor** (`k8s_executor.py`): Executes tasks on Kubernetes using kr8s
- **Task Models** (`task_models.py`): Pydantic models for task definitions and responses

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Start the API Server

```bash
python api_server.py
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
python cli.py submit example_task.yaml
```

#### List Tasks

```bash
python cli.py list
```

With details:

```bash
python cli.py list --details
```

#### Check Task Status

```bash
python cli.py status <task-id>
```

#### Stop a Task

```bash
python cli.py stop <task-id>
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
