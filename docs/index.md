# k8s-cli Documentation

Welcome to k8s-cli, a lightweight SkyPilot-compatible Kubernetes task launcher that enables running computational tasks on Kubernetes clusters using the familiar SkyPilot YAML specification format.

## What is k8s-cli?

k8s-cli is a command-line tool and API server that simplifies running computational workloads on Kubernetes. It provides:

- **Simple Task Submission**: Submit jobs using familiar SkyPilot YAML syntax
- **Multi-Node Support**: Run distributed workloads across multiple nodes
- **Persistent Storage**: Create and manage volumes for data persistence
- **Resource Management**: Configure CPU, memory, and GPU requirements
- **User Isolation**: Multi-tenant support with user-scoped resources
- **Real-Time Monitoring**: Track task status and stream logs

## Quick Start

### Installation

```bash
# Clone the repository and install dependencies
uv sync
```

### Start the API Server

```bash
uv run python -m k8s_cli.api.main
```

The server starts on `http://localhost:8000` by default.

### Submit Your First Task

1. **Login** (set your username):

```bash
uv run k8s-cli auth login myuser
```

2. **Create a task definition** (`hello.yaml`):

```yaml
name: hello-world
resources:
  cpus: "1"
  memory: "1Gi"
  image_id: "python:3.11-slim"

run: |
  echo "Hello from k8s-cli!"
  python -c "print('Task completed successfully')"
```

3. **Submit the task**:

```bash
uv run k8s-cli jobs submit hello.yaml
```

The task will be submitted, and logs will be tailed automatically. You'll receive a unique task ID (e.g., `abc12345`).

4. **Check task status**:

```bash
uv run k8s-cli jobs list
uv run k8s-cli jobs status abc12345
```

## Key Features

### Tasks

Tasks are computational jobs that run on Kubernetes. Each task can:

- Run on one or more nodes (for distributed workloads)
- Request specific resources (CPU, memory, GPUs)
- Use custom container images
- Mount persistent volumes for data storage
- Define setup and run commands
- Access environment variables

Learn more in the [Task Management Guide](tasks.md).

### Volumes

Volumes provide persistent storage for your tasks. You can:

- Create PersistentVolumeClaims with custom sizes and storage classes
- Mount volumes in tasks for reading and writing data
- Share data between multiple tasks
- Choose from different access modes (ReadWriteOnce, ReadWriteMany, ReadOnlyMany)

Learn more in the [Volume Management Guide](volumes.md).

### Multi-Tenancy

k8s-cli supports multiple users working on the same cluster:

- User-scoped resources (tasks and volumes)
- Automatic resource isolation using Kubernetes labels
- Optional admin operations to view all users' resources

## Core Concepts

### Task Lifecycle

1. **Submit**: Create a task from a YAML definition
2. **Pending**: Kubernetes schedules the task pods
3. **Running**: Task executes on one or more nodes
4. **Completed/Failed**: Task finishes with success or failure
5. **Optional**: Stop running tasks manually

### Volume Lifecycle

1. **Create**: Provision a PersistentVolumeClaim
2. **Bind**: Kubernetes binds the PVC to storage
3. **Mount**: Use the volume in one or more tasks
4. **Delete**: Remove the volume and its data

### Multi-Node Tasks

For distributed workloads, specify `num_nodes` in your task definition:

- Each node gets a unique `NODE_RANK` (0, 1, 2, ...)
- All nodes receive `NUM_NODES` environment variable
- Kubernetes creates one Job per node
- Task is complete only when all nodes succeed

## Architecture

k8s-cli consists of four main components:

### 1. API Server

FastAPI-based REST API that handles task and volume operations:
- Task submission, listing, status, logs, and stopping
- Volume creation, listing, and deletion
- User authentication via headers

### 2. CLI

Typer-based command-line interface with command groups:
- `auth`: User login and identity management
- `jobs`: Task operations (submit, list, status, logs, stop)
- `volumes`: Volume operations (create, list, delete)

### 3. Kubernetes Executor

Core engine that manages Kubernetes resources:
- Creates and manages Jobs for tasks
- Creates and manages PersistentVolumeClaims for volumes
- Aggregates status across multi-node tasks
- Streams logs from pods

### 4. Task Models

Pydantic models for data validation:
- Task definitions and configurations
- API request/response schemas
- Status tracking and metadata

## Example Workflows

### Machine Learning Training

```bash
# 1. Create volume for datasets
uv run k8s-cli volumes create training-data 50Gi

# 2. Create volume for model checkpoints
uv run k8s-cli volumes create checkpoints 20Gi

# 3. Submit training task
cat > train.yaml <<EOF
name: model-training
resources:
  cpus: "8"
  memory: "32Gi"
  accelerators: "2"
  image_id: "pytorch/pytorch:2.0.0-cuda11.7-cudnn8-runtime"

volumes:
  /data: training-data
  /checkpoints: checkpoints

setup: |
  pip install transformers datasets

run: |
  python train.py --data /data --output /checkpoints
EOF

uv run k8s-cli jobs submit train.yaml

# 4. Monitor progress
uv run k8s-cli jobs list
uv run k8s-cli jobs logs <task-id>
```

### Distributed Computing

```bash
# Submit multi-node task
cat > distributed.yaml <<EOF
name: distributed-job
num_nodes: 4

resources:
  cpus: "4"
  memory: "8Gi"

run: |
  echo "Node \$NODE_RANK of \$NUM_NODES"
  python distributed_compute.py --rank \$NODE_RANK --world-size \$NUM_NODES
EOF

uv run k8s-cli jobs submit distributed.yaml
```

### Data Processing Pipeline

```bash
# Step 1: Download data
uv run k8s-cli volumes create raw-data 100Gi
uv run k8s-cli jobs submit download_data.yaml

# Step 2: Process data
uv run k8s-cli volumes create processed-data 200Gi
uv run k8s-cli jobs submit process_data.yaml

# Step 3: Run analysis
uv run k8s-cli jobs submit analyze.yaml
```

## Documentation Structure

This documentation is organized into the following sections:

- **[index.md](index.md)** (this page) - Introduction and overview
- **[tasks.md](tasks.md)** - Complete guide to task management
- **[volumes.md](volumes.md)** - Complete guide to volume management
- **[../SPEC.md](../SPEC.md)** - Technical specification with API details

## Requirements

- **Kubernetes cluster** with configured access (kubeconfig)
- **Python 3.11+**
- **kr8s** library for Kubernetes API access
- **Storage provisioner** (for dynamic volume creation)
- **GPU support** (optional, for accelerator workloads)

## Configuration

### Environment Variables

- `K8S_CLI_API_URL`: API server URL (default: `http://localhost:8000`)
- `K8S_CLI_API_PORT`: Server port for API server (default: `8000`)

### Kubernetes Configuration

- Uses your default kubeconfig context
- All resources created in the `default` namespace
- Requires appropriate RBAC permissions for creating Jobs and PVCs

## Getting Help

### CLI Help

```bash
# General help
uv run k8s-cli --help

# Command group help
uv run k8s-cli jobs --help
uv run k8s-cli volumes --help
uv run k8s-cli auth --help

# Specific command help
uv run k8s-cli jobs submit --help
```

### API Documentation

Once the API server is running, visit:
- `http://localhost:8000/docs` - Interactive Swagger UI
- `http://localhost:8000/redoc` - ReDoc documentation

### Health Check

Check if the API server is running:

```bash
curl http://localhost:8000/
# Response: {"status": "ok", "service": "k8s-cli-api"}
```

## Common Use Cases

### 1. Interactive Development

Submit tasks with `--detach` to continue working:

```bash
uv run k8s-cli jobs submit task.yaml --detach
# Check logs later
uv run k8s-cli jobs logs <task-id>
```

### 2. Batch Processing

Submit multiple tasks and monitor:

```bash
for file in tasks/*.yaml; do
  uv run k8s-cli jobs submit "$file" --detach
done

uv run k8s-cli jobs list
```

### 3. Experiment Tracking

Use descriptive task names and volumes:

```bash
uv run k8s-cli volumes create experiment-001 10Gi
uv run k8s-cli jobs submit exp001.yaml
```

### 4. Resource Cleanup

Stop all your tasks:

```bash
uv run k8s-cli jobs stop --all
```

Delete unused volumes:

```bash
uv run k8s-cli volumes list
uv run k8s-cli volumes delete <volume-id> --force
```

## Best Practices

1. **Always specify resources**: Define CPU and memory to ensure predictable scheduling
2. **Use meaningful names**: Name tasks and volumes descriptively for easy identification
3. **Separate volumes by purpose**: Use different volumes for data, checkpoints, logs, etc.
4. **Check task status**: Monitor tasks before submitting new work
5. **Clean up regularly**: Delete completed tasks and unused volumes
6. **Use appropriate images**: Choose minimal base images for faster startup
7. **Test locally first**: Validate task definitions with small resource requests
8. **Back up important data**: Volumes are persistent but not backed up automatically

## Next Steps

Ready to dive deeper? Check out:

1. **[Task Management Guide](tasks.md)** - Learn all about submitting and managing tasks
2. **[Volume Management Guide](volumes.md)** - Master persistent storage
3. **[Technical Specification](../SPEC.md)** - Detailed API and architecture reference
4. **[Example Task](../example_task.yaml)** - See a complete task definition

## Troubleshooting

### API Server Won't Start

- Check if port 8000 is already in use
- Verify kubeconfig is properly configured
- Ensure all dependencies are installed (`uv sync`)

### Task Submission Fails

- Verify the API server is running
- Check task YAML syntax (the `run` field is required)
- Ensure you're logged in (`uv run k8s-cli auth whoami`)

### Task Stuck in Pending

- Check cluster resources: `kubectl get nodes`
- Verify resource requests don't exceed node capacity
- Check for volume binding issues

### Volume Mount Failures

- Ensure volume status is `Bound`
- Verify volume name matches in task definition
- For multi-node tasks, use `ReadWriteMany` access mode

For more detailed troubleshooting, see the [Tasks](tasks.md#troubleshooting) and [Volumes](volumes.md#troubleshooting) guides.

## Contributing

k8s-cli follows these conventions:

- Run `uv sync` to set up the development environment
- Format code with `ruff format .`
- Check code with `ruff check . --fix`
- Update `SPEC.md` when adding or removing features

## License

See [LICENSE](../LICENSE) for details.
