# Task Management Guide

This guide explains how to use the task management features in k8s-cli to submit, monitor, and manage computational tasks on Kubernetes.

## Overview

Tasks are computational jobs that run on Kubernetes using the SkyPilot-compatible YAML specification. Each task can run on one or more nodes with configurable resources like CPU, memory, and GPUs.

## Quick Start

### 1. Submit a Task

Create a task definition file (`task.yaml`):

```yaml
name: my-training-job
num_nodes: 1

resources:
  cpus: "2"
  memory: "4Gi"
  image_id: "python:3.11-slim"

setup: |
  pip install numpy pandas

run: |
  python train.py
```

Submit the task:

```bash
k8s-cli jobs submit task.yaml
```

The command will:
- Submit the task to the API server
- Return a unique 8-character task ID
- Automatically tail the task logs (unless `--detach` is used)

### 2. List Tasks

View all your tasks:

```bash
k8s-cli jobs list
```

With details:

```bash
k8s-cli jobs list --details
```

List all users' tasks (admin):

```bash
k8s-cli jobs list --all-users
```

### 3. Check Task Status

Get detailed status for a specific task:

```bash
k8s-cli jobs status abc12345
```

### 4. View Logs

Tail logs from a running or completed task:

```bash
k8s-cli jobs logs abc12345
```

Press `Ctrl+C` to stop tailing logs.

### 5. Stop a Task

Stop a specific task:

```bash
k8s-cli jobs stop abc12345
```

Stop all your tasks:

```bash
k8s-cli jobs stop --all
```

Stop all tasks for all users (admin):

```bash
k8s-cli jobs stop --all --all-users
```

## Task Definition Reference

### Required Fields

- **`run`** (string): The main command to execute. This is the only required field.

### Optional Fields

#### Basic Configuration

- **`name`** (string): Task name. Defaults to `task-{id}` if not specified.
- **`num_nodes`** (integer): Number of nodes to run the task on. Default: 1, minimum: 1.
- **`workdir`** (string): Working directory for the task.

#### Resources

The `resources` section configures compute resources for each node:

```yaml
resources:
  cpus: "2"                    # CPU allocation (e.g., "2", "500m")
  memory: "4Gi"                # Memory allocation (e.g., "4Gi", "512Mi")
  accelerators: "1"            # GPU allocation (e.g., "1", "V100:2")
  image_id: "python:3.13-slim" # Container image (default: "python:3.13-slim")
```

**Resource Behavior:**
- CPU and memory are set as both requests and limits
- GPUs are set as limits only (using `nvidia.com/gpu`)
- Unsupported fields: `instance_type`, `use_spot`, `disk_size`, `ports` (ignored)

#### Environment Variables

Define environment variables for your task:

```yaml
envs:
  BATCH_SIZE: "32"
  EPOCHS: "100"
  MODEL_PATH: "/data/models"
```

**Auto-injected Variables:**
- `NODE_RANK`: Node index (0-based) for multi-node tasks
- `NUM_NODES`: Total number of nodes

#### Volume Mounts

Mount persistent volumes into your task:

```yaml
volumes:
  /data: training-data          # Mount volume named "training-data" at /data
  /checkpoints: model-checkpoints
```

The volume name is automatically resolved to the corresponding PersistentVolumeClaim. See [Volumes Guide](volumes.md) for details.

#### Setup and Run Commands

- **`setup`** (string): Commands to run before the main task (e.g., installing dependencies).
- **`run`** (string): Main command to execute (required).

```yaml
setup: |
  pip install torch numpy
  echo "Setup completed"

run: |
  python train.py --epochs $EPOCHS
```

## Multi-Node Tasks

For distributed workloads, specify the number of nodes:

```yaml
name: distributed-training
num_nodes: 4

resources:
  cpus: "8"
  memory: "16Gi"
  accelerators: "2"
  image_id: "nvcr.io/nvidia/pytorch:23.10-py3"

envs:
  MASTER_ADDR: "master-service"
  MASTER_PORT: "29500"

run: |
  python -m torch.distributed.launch \
    --nproc_per_node=2 \
    --nnodes=$NUM_NODES \
    --node_rank=$NODE_RANK \
    train_distributed.py
```

**How It Works:**
- Creates one Kubernetes Job per node
- Job names follow the pattern: `{task-name}-{task-id}-node-{idx}`
- Each node gets `NODE_RANK` (0 to num_nodes-1) and `NUM_NODES` environment variables
- Logs from all nodes are prefixed with `node-{idx} |`

**Status Aggregation:**
- Task is `pending` if no nodes are running
- Task is `running` if at least one node is active
- Task is `failed` if any node fails
- Task is `completed` only when all nodes succeed

## Task Lifecycle

1. **Submission**: Task is submitted with a unique 8-character ID
2. **Pending**: Kubernetes is scheduling pods
3. **Running**: At least one pod is executing
4. **Completed**: All nodes finished successfully
5. **Failed**: One or more nodes failed

## Examples

### Simple Python Task

```yaml
name: data-processing
resources:
  cpus: "4"
  memory: "8Gi"
  image_id: "python:3.11"

setup: |
  pip install pandas numpy

run: |
  python process_data.py
```

### GPU Training Task

```yaml
name: gpu-training
resources:
  cpus: "8"
  memory: "32Gi"
  accelerators: "2"
  image_id: "nvidia/cuda:12.1.0-runtime-ubuntu22.04"

setup: |
  pip install torch torchvision

run: |
  python train_model.py --gpu
```

### Task with Volume Mounts

```yaml
name: training-with-data
resources:
  cpus: "4"
  memory: "16Gi"
  image_id: "python:3.11"

volumes:
  /data: training-data
  /output: model-checkpoints

envs:
  DATA_PATH: "/data"
  OUTPUT_PATH: "/output"

run: |
  python train.py --data $DATA_PATH --output $OUTPUT_PATH
```

### Detached Submission

Submit a task without tailing logs:

```bash
k8s-cli jobs submit task.yaml --detach
```

Later, view logs:

```bash
k8s-cli jobs logs abc12345
```

## Tips and Best Practices

1. **Resource Allocation**: Always specify CPU and memory to ensure predictable scheduling
2. **Multi-Node Tasks**: Use `$NODE_RANK` and `$NUM_NODES` for distributed coordination
3. **Volume Mounts**: Create volumes before submitting tasks that need persistent storage
4. **Container Images**: Use specific image tags for reproducibility (e.g., `python:3.11.5` instead of `python:3.11`)
5. **Setup Commands**: Use the `setup` field for one-time initialization to keep the `run` command clean
6. **Detached Mode**: Use `--detach` for long-running tasks and check logs later
7. **Task Naming**: Give meaningful names to tasks for easier identification in listings

## Troubleshooting

### Task Stuck in Pending

- Check if the cluster has sufficient resources
- Verify the requested resources don't exceed node capacity
- Ensure volume claims are bound (if using volumes)

### Task Failed Immediately

- Check logs with `k8s-cli jobs logs <task-id>`
- Verify the container image exists and is accessible
- Check for syntax errors in setup/run commands

### Cannot Mount Volume

- Verify the volume exists: `k8s-cli volumes list`
- Ensure the volume is bound (status should be "Bound")
- Check the volume name matches exactly in the task definition

### Multi-Node Task Partially Failed

- Check individual node logs for error messages
- Verify network connectivity between nodes
- Ensure all nodes can access shared volumes (use `ReadWriteMany` access mode)

## API Reference

For programmatic access, use the REST API endpoints:

- `POST /tasks/submit` - Submit a new task
- `GET /tasks` - List tasks
- `GET /tasks/{task_id}` - Get task status
- `GET /tasks/{task_id}/logs` - Stream task logs
- `POST /tasks/{task_id}/stop` - Stop a task
- `POST /tasks/stop` - Stop multiple tasks

See the [SPEC.md](../SPEC.md) for detailed API documentation.
