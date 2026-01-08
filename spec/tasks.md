# Task Execution Specification

## Overview

This specification defines the task execution system for k8s-cli, a SkyPilot-compatible Kubernetes task launcher. The system allows users to submit, monitor, and manage containerized workloads on Kubernetes through both CLI and REST API interfaces.

## Requirements

### Core Functionality

#### Task Submission
- The system MUST accept task definitions in SkyPilot-compatible YAML format
- The system MUST support the `run` field as a required command to execute
- The system MAY support an optional `name` field for task identification
- The system MAY support an optional `workdir` field to specify the working directory
- The system MAY support an optional `setup` field for pre-execution commands
- The system MUST generate a unique task ID for each submitted task
- The system MUST validate that the `run` field exists in the task definition

#### Multi-Node Execution
- The system MUST support multi-node task execution via the `num_nodes` field
- The system MUST create one Kubernetes Job per node when `num_nodes > 1`
- The system MUST set the `NODE_RANK` environment variable to indicate the node index
- The system MUST set the `NUM_NODES` environment variable to indicate total node count
- The system SHOULD aggregate status across all nodes when reporting task status

#### Resource Management
- The system MAY support CPU resource requests via the `cpus` field
- The system MAY support memory resource requests via the `memory` field
- The system MAY support accelerator requests (e.g., GPUs) via the `accelerators` field
- The system MAY support custom container images via the `image_id` field
- The system MUST default to `python:3.13-slim` image if no image is specified
- The system MUST apply resource requests as both requests and limits in Kubernetes

#### Environment Variables
- The system MUST support custom environment variables via the `envs` field
- The system MUST inject `NODE_RANK` and `NUM_NODES` for multi-node tasks
- The system MUST pass all environment variables to the container

#### Volume Mounting
- The system MAY support mounting persistent volumes via the `volumes` field
- The system MUST resolve volume names to actual PVC names using labels
- The system MUST mount volumes at the specified paths in the container

#### Task Status Tracking
- The system MUST track the status of each task (pending, running, completed, failed)
- The system MUST aggregate status from all node jobs for multi-node tasks
- The system MUST report a task as completed only when all nodes succeed
- The system MUST report a task as failed when any node fails
- The system MUST provide creation and update timestamps for each task
- The system MUST store metadata including job names, namespace, and node counts

#### Task Termination
- The system MUST support stopping a running task by task ID
- The system MUST support stopping all tasks for a specific user
- The system MAY support stopping all tasks for all users (admin operation)
- The system MUST delete all associated Kubernetes Jobs when stopping a task

#### Log Streaming
- The system MUST support streaming logs from running and completed tasks
- The system MUST aggregate logs from all pods for multi-node tasks
- The system MUST prefix log lines with node identifiers for multi-node tasks
- The system SHOULD follow logs in real-time for running tasks

### User Isolation

- The system MUST isolate tasks by username using Kubernetes labels
- The system MUST sanitize usernames for use in Kubernetes labels (replace `@` with `-`)
- The system MUST prevent users from accessing or stopping tasks owned by other users
- The system MAY allow privileged operations to list/stop tasks across all users

### CLI Interface

- The system MUST provide a `jobs submit` command to submit task YAML files
- The system MUST provide a `jobs stop` command to stop tasks
- The system MUST provide a `jobs list` command to list tasks
- The system MUST provide a `jobs status` command to get task details
- The system MUST provide a `jobs logs` command to stream task logs
- The system SHOULD support the `--detach` flag to submit without tailing logs
- The system SHOULD support the `--all` flag to stop all tasks
- The system SHOULD support the `--details` flag to show extended information

### REST API Interface

- The system MUST provide a `POST /tasks/submit` endpoint to submit tasks
- The system MUST provide a `POST /tasks/{task_id}/stop` endpoint to stop a specific task
- The system MUST provide a `POST /tasks/stop` endpoint to stop all tasks
- The system MUST provide a `GET /tasks` endpoint to list tasks
- The system MUST provide a `GET /tasks/{task_id}` endpoint to get task status
- The system MUST provide a `GET /tasks/{task_id}/logs` endpoint to stream logs
- The system MUST require an `X-User` header for user identification
- The system MUST support an `all_users` query parameter for privileged operations

### Error Handling

- The system MUST return appropriate HTTP status codes for API errors
- The system MUST provide descriptive error messages for failed operations
- The system MUST validate task definitions before submission
- The system MUST handle Kubernetes API failures gracefully

### Kubernetes Integration

- The system MUST create Kubernetes Jobs with `backoffLimit: 0`
- The system MUST label all resources with `skypilot-task: true`
- The system MUST label all resources with `task-id`, `task-name`, and `username`
- The system MUST annotate jobs with `created-at` and `num-nodes`
- The system MUST use the `default` namespace for all resources
- The system MUST wait for pods to be scheduled before streaming logs

## Data Models

### TaskDefinition
- `name` (optional): Task name for identification
- `workdir` (optional): Working directory in the container
- `num_nodes` (default: 1): Number of nodes for distributed execution
- `resources` (optional): Resource requirements
- `envs` (optional): Environment variables dictionary
- `file_mounts` (optional): File mounts (reserved for future use)
- `volumes` (optional): Volume mounts as `{mount_path: volume_name}`
- `setup` (optional): Setup commands to run before main command
- `run` (required): Main command to execute

### TaskStatus
- `task_id`: Unique task identifier
- `name`: Task name
- `status`: One of `pending`, `running`, `completed`, `failed`
- `created_at`: ISO timestamp of task creation
- `updated_at`: ISO timestamp of last status update
- `username`: User who submitted the task
- `metadata`: Additional information including job names, namespace, node counts

## Implementation Notes

- Task IDs are 8-character UUID prefixes
- Job names follow the pattern `{task-name}-{task-id}` or `{task-name}-{task-id}-node-{idx}`
- Username sanitization replaces `@` with `-` for DNS-1123 compliance
- Multi-node status aggregation considers all node jobs before determining final status
