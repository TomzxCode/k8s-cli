# Volume Management Guide

This guide explains how to create, manage, and use persistent volumes in k8s-cli for storing data across task executions.

## Overview

Volumes in k8s-cli are Kubernetes PersistentVolumeClaims (PVCs) that provide persistent storage for your tasks. They allow you to:

- Store training data, models, and checkpoints
- Share data between multiple tasks
- Persist data beyond task completion
- Use different storage classes and access modes

## Quick Start

### 1. Create a Volume

Create a 10Gi volume for training data:

```bash
k8s-cli volumes create training-data 10Gi
```

The command returns a unique 8-character volume ID.

### 2. List Volumes

View all your volumes:

```bash
k8s-cli volumes list
```

With details:

```bash
k8s-cli volumes list --details
```

List all users' volumes (admin):

```bash
k8s-cli volumes list --all-users
```

### 3. Use Volume in Task

Mount the volume in your task definition:

```yaml
name: training-job
resources:
  cpus: "4"
  memory: "8Gi"

volumes:
  /data: training-data      # Mount volume at /data

run: |
  python train.py --data /data
```

### 4. Delete a Volume

Delete a volume (with confirmation):

```bash
k8s-cli volumes delete vol12345
```

Force delete without confirmation:

```bash
k8s-cli volumes delete vol12345 --force
```

## Volume Creation Options

### Basic Creation

```bash
k8s-cli volumes create <name> <size>
```

**Parameters:**
- `name`: Logical volume name (used to reference the volume in tasks)
- `size`: Storage size with unit (e.g., `10Gi`, `1Ti`, `500Mi`)

### Storage Class

Specify a custom storage class:

```bash
k8s-cli volumes create fast-storage 20Gi --storage-class fast-ssd
```

Storage classes are defined by your Kubernetes cluster and may include:
- `standard` (default)
- `fast-ssd`
- `slow-hdd`
- Custom classes defined by your cluster admin

### Access Modes

Specify how the volume can be mounted:

```bash
k8s-cli volumes create shared-data 50Gi --access-modes ReadWriteMany
```

**Available Access Modes:**

| Access Mode | Description | Use Case |
|-------------|-------------|----------|
| `ReadWriteOnce` | Can be mounted as read-write by a single node | Default, suitable for most tasks |
| `ReadWriteMany` | Can be mounted as read-write by multiple nodes | Multi-node tasks sharing data |
| `ReadOnlyMany` | Can be mounted as read-only by multiple nodes | Shared read-only datasets |

**Multiple Access Modes:**

```bash
k8s-cli volumes create versatile-vol 10Gi --access-modes "ReadWriteOnce,ReadWriteMany"
```

## Volume Status

Volumes can have the following status values (from Kubernetes PVC phases):

- **`Pending`**: Volume is being created or waiting for storage
- **`Bound`**: Volume is ready and bound to underlying storage
- **`Lost`**: Volume lost connection to underlying storage (rare)

Only `Bound` volumes can be successfully mounted in tasks.

## Using Volumes in Tasks

### Basic Volume Mount

```yaml
volumes:
  /path/in/container: volume-name
```

Example:

```yaml
name: data-processing
resources:
  cpus: "2"
  memory: "4Gi"

volumes:
  /data: training-data

run: |
  ls -la /data
  python process.py --input /data/raw --output /data/processed
```

### Multiple Volume Mounts

```yaml
volumes:
  /data: training-data
  /checkpoints: model-checkpoints
  /logs: experiment-logs
```

### Volume Resolution

When you specify a volume by name in a task, k8s-cli automatically resolves it:

1. Searches for a PVC with label `volume-name={name}` owned by your user
2. If found, uses that PVC
3. If not found, treats the name as a literal PVC name

This allows you to:
- Use volumes created via k8s-cli by their logical name
- Reference existing PVCs directly if needed

## Examples

### Example 1: Training with Persistent Storage

Create volume and run training task:

```bash
# Create volume for training data
k8s-cli volumes create ml-data 100Gi

# Create volume for model checkpoints
k8s-cli volumes create checkpoints 50Gi

# Submit training task
cat > train.yaml <<EOF
name: model-training
resources:
  cpus: "8"
  memory: "32Gi"
  accelerators: "2"
  image_id: "pytorch/pytorch:2.0.0-cuda11.7-cudnn8-runtime"

volumes:
  /data: ml-data
  /checkpoints: checkpoints

envs:
  DATA_DIR: "/data"
  CHECKPOINT_DIR: "/checkpoints"

setup: |
  pip install transformers datasets tensorboard

run: |
  python train.py \
    --data_dir $DATA_DIR \
    --checkpoint_dir $CHECKPOINT_DIR \
    --epochs 100
EOF

k8s-cli jobs submit train.yaml
```

### Example 2: Multi-Node Task with Shared Volume

For multi-node tasks, use `ReadWriteMany` access mode:

```bash
# Create shared volume
k8s-cli volumes create shared-workspace 200Gi --access-modes ReadWriteMany

# Submit multi-node task
cat > distributed.yaml <<EOF
name: distributed-training
num_nodes: 4

resources:
  cpus: "8"
  memory: "16Gi"
  accelerators: "2"

volumes:
  /workspace: shared-workspace

run: |
  # All nodes can read/write to /workspace
  echo "Node $NODE_RANK initialized" > /workspace/node-$NODE_RANK.txt
  python distributed_train.py --workspace /workspace
EOF

k8s-cli jobs submit distributed.yaml
```

### Example 3: Data Preprocessing Pipeline

```bash
# Create volumes
k8s-cli volumes create raw-data 50Gi
k8s-cli volumes create processed-data 100Gi

# Step 1: Download data
cat > download.yaml <<EOF
name: download-data
volumes:
  /data: raw-data
run: |
  wget -P /data https://example.com/dataset.tar.gz
  tar -xzf /data/dataset.tar.gz -C /data
EOF
k8s-cli jobs submit download.yaml

# Step 2: Process data
cat > process.yaml <<EOF
name: process-data
volumes:
  /input: raw-data
  /output: processed-data
run: |
  python preprocess.py --input /input --output /output
EOF
k8s-cli jobs submit process.yaml

# Step 3: Train model
cat > train.yaml <<EOF
name: train-model
volumes:
  /data: processed-data
  /checkpoints: model-checkpoints
run: |
  python train.py --data /data --checkpoints /checkpoints
EOF
k8s-cli jobs submit train.yaml
```

### Example 4: Using Fast Storage

For IO-intensive workloads, use fast storage:

```bash
k8s-cli volumes create fast-cache 20Gi --storage-class fast-ssd

cat > io-intensive.yaml <<EOF
name: io-task
resources:
  cpus: "16"
  memory: "64Gi"

volumes:
  /cache: fast-cache

run: |
  # Fast storage for temporary data
  ./io_intensive_workload --cache /cache
EOF

k8s-cli jobs submit io-intensive.yaml
```

## Volume Lifecycle

1. **Creation**: Volume is created with status `Pending`
2. **Binding**: Kubernetes binds the PVC to underlying storage (status becomes `Bound`)
3. **Usage**: Volume can be mounted in tasks
4. **Deletion**: Volume and its data are permanently deleted

**Important Notes:**
- Volumes persist after tasks complete (data is retained)
- Deleting a volume permanently destroys its data
- Only the volume owner can delete it
- Volumes must be unmounted (tasks stopped) before deletion

## Storage Best Practices

### 1. Size Planning

- Allocate sufficient space for your data plus ~20% buffer
- Consider data growth over time
- Monitor volume usage with `kubectl get pvc`

### 2. Access Modes

- Use `ReadWriteOnce` for single-task workloads (more efficient)
- Use `ReadWriteMany` only when multiple nodes need concurrent write access
- Use `ReadOnlyMany` for shared datasets that don't change

### 3. Storage Classes

- Use default storage for general purposes
- Use fast-ssd for databases, checkpoints, or IO-intensive tasks
- Use slow-hdd for archival or infrequently accessed data
- Check available storage classes: `kubectl get storageclass`

### 4. Volume Organization

- Create separate volumes for different data types:
  - `/data` for input datasets
  - `/checkpoints` for model checkpoints
  - `/logs` for logs and metrics
  - `/output` for results
- Use meaningful volume names (e.g., `imagenet-train`, `bert-checkpoints`)

### 5. Data Management

- Back up important data outside the cluster
- Clean up unused volumes regularly
- Use smaller volumes for experiments, larger for production

## Troubleshooting

### Volume Stuck in Pending

**Problem**: Volume status remains `Pending` after creation.

**Solutions**:
- Check if the cluster has available storage: `kubectl get pv`
- Verify the storage class exists: `kubectl get storageclass`
- Check PVC events: `kubectl describe pvc <pvc-name>`
- Ensure the cluster has a default storage provisioner

### Cannot Mount Volume in Task

**Problem**: Task fails to start due to volume mount issues.

**Solutions**:
- Verify volume status is `Bound`: `k8s-cli volumes list`
- Check volume name spelling in task definition
- Ensure you're the volume owner (or use `--all-users` to check)
- For multi-node tasks, verify access mode is `ReadWriteMany`

### Volume Deletion Fails

**Problem**: Cannot delete a volume.

**Solutions**:
- Stop all tasks using the volume: `k8s-cli jobs list` then `k8s-cli jobs stop <task-id>`
- Wait for tasks to fully terminate
- Check PVC finalizers: `kubectl get pvc <pvc-name> -o yaml`
- Verify you're the volume owner

### Out of Disk Space

**Problem**: Task fails because volume is full.

**Solutions**:
- Create a larger volume and migrate data
- Clean up unnecessary files in the existing volume
- Use compression for data storage
- Consider using object storage for large datasets

### Wrong Storage Class

**Problem**: Volume created with incorrect storage class.

**Solutions**:
- Delete the volume and recreate with correct `--storage-class`
- Or create a new volume and migrate data
- Check available storage classes: `kubectl get storageclass`

## Advanced Usage

### Checking Volume Details

Get detailed volume information via API:

```bash
curl -H "X-User: myuser" http://localhost:8000/volumes/<volume-id>
```

### Listing All Volumes (Admin)

See all volumes across all users:

```bash
k8s-cli volumes list --all-users --details
```

### Volume Naming Convention

PVCs created by k8s-cli follow the naming pattern:

```
{volume-name}-{volume-id}
```

Example: `training-data-vol12345`

### Labels

All volumes are labeled with:
- `skypilot-volume=true`
- `volume-id={id}`
- `volume-name={name}`
- `username={sanitized-username}`

These labels enable filtering and user isolation.

## API Reference

For programmatic access, use the REST API endpoints:

- `POST /volumes/create` - Create a new volume
- `GET /volumes` - List volumes
- `GET /volumes/{volume_id}` - Get volume status
- `DELETE /volumes/{volume_id}` - Delete a volume

See the [SPEC.md](../SPEC.md) for detailed API documentation.

## Next Steps

- Learn about [Task Management](tasks.md)
- See [Example Workflows](../SPEC.md#example-workflows) in the specification
- Explore the [example_task.yaml](../example_task.yaml) for reference
