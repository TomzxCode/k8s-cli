# k8s-cli Feature Specification

## Overview

k8s-cli is a lightweight SkyPilot-compatible Kubernetes task launcher that enables running computational tasks on Kubernetes clusters using the SkyPilot YAML specification format.

**Version:** 1.0.0
**Default Namespace:** `default`
**Label Prefix:** `skypilot-`

## Documentation

- [Task Management Guide](docs/tasks.md) - Complete guide to submitting and managing tasks
- [Volume Management Guide](docs/volumes.md) - Guide to creating and using persistent volumes

---

## Architecture Components

### 1. API Server (`src/k8s_cli/api/`)

FastAPI-based REST API server that handles task and volume operations.

**Main Files:**
- `main.py` - Application initialization, configuration, and lifespan management
- `tasks.py` - Task-related API endpoints
- `volumes.py` - Volume-related API endpoints

**Configuration:**
- Default port: `8000`
- Configurable via `K8S_CLI_API_PORT` environment variable
- Host: `0.0.0.0`

### 2. CLI (`src/k8s_cli/cli.py`)

Command-line interface built with Typer for interacting with the API server.

**Command Groups:**
- `auth` - Authentication commands
- `jobs` - Job/task management commands
- `volumes` - Volume/PVC management commands

### 3. Kubernetes Executor (`src/k8s_cli/k8s_executor.py`)

Core execution engine that manages Kubernetes resources using kr8s library.

**Responsibilities:**
- Task submission and lifecycle management
- Volume (PVC) creation and management
- Status aggregation for multi-node tasks
- Log streaming from pods

### 4. Task Models (`src/k8s_cli/task_models.py`)

Pydantic models for task definitions, statuses, and API responses.

---

## Features

### Authentication

#### User Management
- **Login:** `k8s-cli auth login <username>`
  - Sets the active user for subsequent operations
  - Username stored locally for authentication headers

- **Whoami:** `k8s-cli auth whoami`
  - Displays currently logged-in user

**Implementation Details:**
- Username passed via `X-User` HTTP header
- Usernames sanitized for Kubernetes labels (e.g., `@` → `-`)
- User-scoped resource isolation

---

### Task Management

#### Task Submission

**CLI Command:** `k8s-cli jobs submit <task-file.yaml> [--detach]`

**API Endpoint:** `POST /tasks/submit`

**Features:**
- Accepts SkyPilot-compatible YAML files
- Multi-node task support (creates one Job per node)
- Automatic log tailing (unless `--detach` flag used)
- Returns 8-character task ID

**Task Definition Fields:**

```yaml
name: string                    # Task name (optional, defaults to "task-{id}")
num_nodes: int                  # Number of nodes (default: 1, minimum: 1)
workdir: string                 # Working directory (optional)
resources:                      # Resource requirements (optional)
  cpus: string                  # CPU allocation (e.g., "2", "500m")
  memory: string                # Memory allocation (e.g., "4Gi", "512Mi")
  accelerators: string          # GPU allocation (e.g., "1", "V100:2")
  instance_type: string         # Instance type (optional, unused)
  use_spot: boolean             # Use spot instances (optional, unused)
  disk_size: int                # Disk size (optional, unused)
  ports: list[int]              # Port mappings (optional, unused)
  image_id: string              # Container image (default: "python:3.13-slim")
envs: dict[string, string]      # Environment variables (optional)
file_mounts: dict[string, string] # File mounts (optional, unused)
volumes: dict[string, string]   # Volume mounts {mount_path: volume_name}
setup: string                   # Setup commands (optional)
run: string                     # Main command (REQUIRED)
```

**Auto-injected Environment Variables:**
- `NODE_RANK`: Node index (0-based)
- `NUM_NODES`: Total number of nodes

**Kubernetes Resources Created:**
- One `Job` per node with naming pattern:
  - Single node: `{task-name}-{task-id}`
  - Multi-node: `{task-name}-{task-id}-node-{idx}`
- Jobs labeled with:
  - `skypilot-task=true`
  - `task-id={id}`
  - `task-name={name}`
  - `username={sanitized-username}`
  - `node-idx={idx}`

**Resource Handling:**
- CPU/Memory: Set as both requests and limits
- GPUs: Set as limits only (`nvidia.com/gpu`)
- Volumes: Automatically resolved to PVC names by volume-name label

**Location:** `jobs.py:16`, `tasks.py:21`, `k8s_executor.py:53`

---

#### Task Listing

**CLI Command:** `k8s-cli jobs list [--details] [--all-users]`

**API Endpoint:** `GET /tasks?all_users={boolean}`

**Features:**
- Lists tasks for current user (default) or all users
- Displays task ID, name, status, creation time
- Optional detailed view with job names and namespace
- Results sorted by creation time (newest first)

**Status Values:**
- `pending`: No nodes running yet
- `running`: At least one node active
- `failed`: Any node failed
- `completed`: All nodes succeeded

**Location:** `jobs.py:141`, `tasks.py:104`

---

#### Task Status

**CLI Command:** `k8s-cli jobs status <task-id>`

**API Endpoint:** `GET /tasks/{task_id}`

**Features:**
- Shows detailed status for specific task
- Displays metadata including:
  - Number of nodes
  - Per-node status counts (succeeded/failed/running/pending)
  - Job names for each node
  - Creation and update timestamps

**Multi-Node Aggregation:**
- Aggregates status from all node jobs
- Task marked completed only when all nodes succeed
- Task marked failed if any node fails

**Location:** `jobs.py:215`, `tasks.py:129`, `k8s_executor.py:230`

---

#### Task Stopping

**CLI Commands:**
- `k8s-cli jobs stop <task-id>` - Stop specific task
- `k8s-cli jobs stop --all` - Stop all tasks for current user
- `k8s-cli jobs stop --all --all-users` - Stop all tasks for all users

**API Endpoints:**
- `POST /tasks/{task_id}/stop` - Stop single task
- `POST /tasks/stop?all_users={boolean}` - Stop multiple tasks

**Features:**
- Deletes Kubernetes Jobs with background propagation policy
- Returns count of tasks stopped (for bulk operations)
- User-scoped by default

**Location:** `jobs.py:85`, `tasks.py:45`, `tasks.py:74`, `k8s_executor.py:155`

---

#### Log Tailing

**CLI Command:** `k8s-cli jobs logs <task-id>`

**API Endpoint:** `GET /tasks/{task_id}/logs`

**Features:**
- Streams logs from all pods in real-time
- Multi-threaded log collection from parallel pods
- Multi-node prefix format: `node-{idx} | {log-line}`
- Handles both running and completed pods
- Continues until all pods terminate

**Implementation:**
- Uses streaming HTTP response
- Waits for pods to be scheduled (5-minute timeout)
- Parallel log streaming via threading and queue

**Location:** `jobs.py:250`, `tasks.py:154`, `k8s_executor.py:523`

---

### Volume Management

#### Volume Creation

**CLI Command:** `k8s-cli volumes create <name> <size> [--storage-class <class>] [--access-modes <modes>]`

**API Endpoint:** `POST /volumes/create`

**Features:**
- Creates Kubernetes PersistentVolumeClaim
- Returns 8-character volume ID
- User-scoped volume ownership

**Parameters:**
- `name`: Logical volume name
- `size`: Storage size (e.g., "10Gi", "1Ti")
- `storage_class`: Storage class (optional)
- `access_modes`: Comma-separated access modes (default: "ReadWriteOnce")

**Supported Access Modes:**
- `ReadWriteOnce` (default)
- `ReadWriteMany`
- `ReadOnlyMany`

**PVC Naming:** `{name}-{volume-id}`

**Labels:**
- `skypilot-volume=true`
- `volume-id={id}`
- `volume-name={name}`
- `username={sanitized-username}`

**Location:** `volumes.py:14`, `api/volumes.py:19`, `k8s_executor.py:392`

---

#### Volume Listing

**CLI Command:** `k8s-cli volumes list [--details] [--all-users]`

**API Endpoint:** `GET /volumes?all_users={boolean}`

**Features:**
- Lists volumes for current user or all users
- Shows volume ID, name, size, status, creation time
- Optional detailed view with storage class, access modes, PVC name

**Volume Statuses:** (from Kubernetes PVC phases)
- `Pending`
- `Bound`
- `Lost`

**Location:** `volumes.py:59`, `api/volumes.py:42`

---

#### Volume Deletion

**CLI Command:** `k8s-cli volumes delete <volume-id> [--force]`

**API Endpoint:** `DELETE /volumes/{volume_id}`

**Features:**
- Deletes PersistentVolumeClaim
- Interactive confirmation (unless `--force` flag)
- User-scoped deletion (only owner can delete)

**Location:** `volumes.py:134`, `api/volumes.py:67`, `k8s_executor.py:432`

---

#### Volume Status

**API Endpoint:** `GET /volumes/{volume_id}`

**Features:**
- Returns detailed status for specific volume
- Includes size, storage class, access modes, phase
- Metadata includes PVC name and namespace

**Location:** `api/volumes.py:96`, `k8s_executor.py:474`

---

### Volume Mounting in Tasks

**YAML Syntax:**
```yaml
volumes:
  /path/in/container: volume-name
```

**Resolution Strategy:**
1. Search for PVC with label `volume-name={name}` and `username={user}`
2. If found, use the PVC name from metadata
3. If not found, treat `volume-name` as literal PVC name

**Implementation:**
- Volumes added to pod spec with automatic PVC claim name resolution
- Volume mounts configured in container spec
- User-scoped volume resolution

**Location:** `k8s_executor.py:32`, `k8s_executor.py:91`

---

## Configuration

### Environment Variables

- `K8S_CLI_API_URL`: API server URL (default: `http://localhost:8000`)
- `K8S_CLI_API_PORT`: Server port (default: `8000`)

### Kubernetes Configuration

- Uses kr8s library for Kubernetes API access
- Requires valid kubeconfig with cluster credentials
- All resources created in `default` namespace

---

## API Response Models

### TaskSubmitResponse
```json
{
  "task_id": "abc12345",
  "status": "submitted",
  "message": "Task submitted successfully with ID: abc12345"
}
```

### TaskStatus
```json
{
  "task_id": "abc12345",
  "name": "my-task",
  "status": "running",
  "created_at": "2025-10-05T12:34:56.789012",
  "updated_at": "2025-10-05T12:35:01.234567",
  "username": "user-example.com",
  "metadata": {
    "job_name": "my-task-abc12345",
    "namespace": "default",
    "num_nodes": 2,
    "node_jobs": ["my-task-abc12345-node-0", "my-task-abc12345-node-1"],
    "succeeded_nodes": 0,
    "failed_nodes": 0,
    "running_nodes": 2,
    "pending_nodes": 0
  }
}
```

### TaskListResponse
```json
{
  "tasks": [/* array of TaskStatus */]
}
```

### TaskStopResponse
```json
{
  "task_id": "abc12345",
  "status": "stopped",
  "message": "Task abc12345 stopped successfully"
}
```

### TaskStopAllResponse
```json
{
  "count": 5,
  "status": "stopped",
  "message": "Stopped 5 tasks"
}
```

### VolumeCreateResponse
```json
{
  "volume_id": "vol12345",
  "status": "created",
  "message": "Volume created successfully with ID: vol12345"
}
```

### VolumeStatus
```json
{
  "volume_id": "vol12345",
  "name": "my-volume",
  "size": "10Gi",
  "storage_class": "standard",
  "access_modes": ["ReadWriteOnce"],
  "status": "Bound",
  "created_at": "2025-10-05T12:34:56.789012",
  "username": "user-example.com",
  "metadata": {
    "pvc_name": "my-volume-vol12345",
    "namespace": "default"
  }
}
```

### VolumeListResponse
```json
{
  "volumes": [/* array of VolumeStatus */]
}
```

### VolumeDeleteResponse
```json
{
  "volume_id": "vol12345",
  "status": "deleted",
  "message": "Volume vol12345 deleted successfully"
}
```

---

## Error Handling

### HTTP Status Codes

- `200 OK`: Successful operation
- `404 Not Found`: Task or volume not found
- `500 Internal Server Error`: Operation failed (with error details)

### Error Response Format
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Security & Multi-tenancy

### User Isolation
- All resources tagged with sanitized username
- Users can only access their own resources by default
- Admin operations available with `--all-users` flag

### Label-based Access Control
- Resources filtered by `username` label
- Prevents cross-user resource access
- Consistent across tasks and volumes

### Username Sanitization
- `@` characters replaced with `-` for Kubernetes label compatibility
- Example: `user@example.com` → `user-example.com`

**Location:** `k8s_executor.py:22`

---

## Limitations & Future Considerations

### Unsupported SkyPilot Fields
- `instance_type`: Ignored (Kubernetes doesn't support instance type selection)
- `use_spot`: Ignored (requires cluster-level spot instance configuration)
- `disk_size`: Ignored (disk managed at node/storage class level)
- `ports`: Ignored (no Service resource creation)
- `file_mounts`: Not implemented

### Known Constraints
- Single namespace operation (`default`)
- No built-in cleanup of completed jobs
- No job history retention policy
- No resource quotas or limits per user
- No authentication/authorization beyond username header

---

## Dependencies

### Core Libraries
- **FastAPI**: Web framework for API server
- **Typer**: CLI framework
- **kr8s**: Kubernetes API client
- **Pydantic**: Data validation and models
- **httpx**: HTTP client for CLI
- **PyYAML**: YAML parsing
- **Rich**: Terminal output formatting
- **Uvicorn**: ASGI server

### Requirements
- Python 3.11+
- Kubernetes cluster access
- Valid kubeconfig configuration

---

## Example Workflows

### Complete Task Lifecycle

```bash
# 1. Login
k8s-cli auth login myuser

# 2. Create volume
k8s-cli volumes create data-vol 10Gi

# 3. Submit task using volume
cat > task.yaml <<EOF
name: training-job
num_nodes: 2
resources:
  cpus: "4"
  memory: "8Gi"
  accelerators: "1"
  image_id: "python:3.11"
volumes:
  /data: data-vol
envs:
  EPOCHS: "100"
setup: |
  pip install torch numpy
run: |
  python train.py --data /data --epochs $EPOCHS
EOF

k8s-cli jobs submit task.yaml

# 4. Monitor task
k8s-cli jobs list
k8s-cli jobs status abc12345

# 5. View logs
k8s-cli jobs logs abc12345

# 6. Stop if needed
k8s-cli jobs stop abc12345

# 7. Cleanup
k8s-cli volumes delete vol12345 --force
```

### Multi-node Distributed Training

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
setup: |
  pip install transformers datasets
run: |
  python -m torch.distributed.launch \
    --nproc_per_node=2 \
    --nnodes=$NUM_NODES \
    --node_rank=$NODE_RANK \
    --master_addr=$MASTER_ADDR \
    --master_port=$MASTER_PORT \
    train_distributed.py
```

---

## API Server Health Check

**Endpoint:** `GET /`

**Response:**
```json
{
  "status": "ok",
  "service": "k8s-cli-api"
}
```

**Location:** `api/main.py:37`
