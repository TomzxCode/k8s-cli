# REST API Specification

## Overview

This specification defines the REST API for k8s-cli. The API provides programmatic access to task and volume management functionality, with support for both individual user operations and administrative operations across all users.

## Requirements

### Core Functionality

#### Server Configuration
- The system MUST implement a FastAPI-based REST API
- The system MUST initialize the Kubernetes executor on startup
- The system MUST provide a health check endpoint at the root path
- The system MAY support configurable port via the `K8S_CLI_API_PORT` environment variable
- The system MUST default to port 8000 if no port is specified

#### Request Authentication
- The system MUST require an `X-User` header on all endpoints
- The system MUST extract the username from the `X-User` header
- The system MUST pass the username to executor methods for authorization
- The system SHOULD validate the presence of the `X-User` header

#### Response Format
- The system MUST return JSON responses for all endpoints
- The system MUST use appropriate HTTP status codes
- The system MUST return descriptive error messages in response bodies
- The system MUST use Pydantic models for request/response validation

#### Streaming Responses
- The system MUST support streaming responses for log endpoints
- The system MUST use `text/plain` content type for streaming responses
- The system MUST stream log lines as they arrive from the executor

### Task Endpoints

#### Submit Task
- **Endpoint:** `POST /tasks/submit`
- **Authentication:** Required (`X-User` header)
- **Request Body:** TaskDefinition JSON
- **Response:** TaskSubmitResponse with task_id, status, and message
- **Behavior:**
  - MUST validate the task definition
  - MUST submit the task to Kubernetes
  - MUST return a unique task ID
  - MUST log the submission with username

#### Stop Task
- **Endpoint:** `POST /tasks/{task_id}/stop`
- **Authentication:** Required (`X-User` header)
- **Response:** TaskStopResponse with task_id, status, and message
- **Behavior:**
  - MUST stop the specified task for the authenticated user
  - MUST return 404 if the task is not found for the user
  - MUST delete all associated Kubernetes Jobs

#### Stop All Tasks
- **Endpoint:** `POST /tasks/stop`
- **Authentication:** Required (`X-User` header)
- **Query Parameters:**
  - `all_users` (boolean): If true, stop tasks for all users
- **Response:** TaskStopAllResponse with count, status, and message
- **Behavior:**
  - MUST stop all tasks for the authenticated user by default
  - MUST stop all tasks for all users if `all_users=true`
  - MUST return the count of stopped tasks

#### List Tasks
- **Endpoint:** `GET /tasks`
- **Authentication:** Required (`X-User` header)
- **Query Parameters:**
  - `all_users` (boolean): If true, list tasks from all users
- **Response:** TaskListResponse with tasks array
- **Behavior:**
  - MUST return tasks for the authenticated user by default
  - MUST return tasks from all users if `all_users=true`
  - MUST include task status, metadata, and timestamps

#### Get Task Status
- **Endpoint:** `GET /tasks/{task_id}`
- **Authentication:** Required (`X-User` header)
- **Response:** TaskStatus with task details
- **Behavior:**
  - MUST return status for the specified task for the authenticated user
  - MUST return 404 if the task is not found for the user
  - MUST include aggregated status for multi-node tasks

#### Stream Task Logs
- **Endpoint:** `GET /tasks/{task_id}/logs`
- **Authentication:** Required (`X-User` header)
- **Response:** Streaming text/plain response
- **Behavior:**
  - MUST stream logs from all pods for the task
  - MUST prefix log lines with node identifiers for multi-node tasks
  - MUST follow logs in real-time

### Volume Endpoints

#### Create Volume
- **Endpoint:** `POST /volumes/create`
- **Authentication:** Required (`X-User` header)
- **Request Body:** VolumeDefinition JSON
- **Response:** VolumeCreateResponse with volume_id, status, and message
- **Behavior:**
  - MUST validate the volume definition
  - MUST create a Kubernetes PVC
  - MUST return a unique volume ID
  - MUST label the PVC with user information

#### List Volumes
- **Endpoint:** `GET /volumes`
- **Authentication:** Required (`X-User` header)
- **Query Parameters:**
  - `all_users` (boolean): If true, list volumes from all users
- **Response:** VolumeListResponse with volumes array
- **Behavior:**
  - MUST return volumes for the authenticated user by default
  - MUST return volumes from all users if `all_users=true`
  - MUST include volume status, size, and metadata

#### Get Volume Status
- **Endpoint:** `GET /volumes/{volume_id}`
- **Authentication:** Required (`X-User` header)
- **Response:** VolumeStatus with volume details
- **Behavior:**
  - MUST return status for the specified volume for the authenticated user
  - MUST return 404 if the volume is not found for the user

#### Delete Volume
- **Endpoint:** `DELETE /volumes/{volume_id}`
- **Authentication:** Required (`X-User` header)
- **Response:** VolumeDeleteResponse with volume_id, status, and message
- **Behavior:**
  - MUST delete the specified volume for the authenticated user
  - MUST return 404 if the volume is not found for the user
  - MUST delete the associated Kubernetes PVC

### Health Check

#### Root Endpoint
- **Endpoint:** `GET /`
- **Authentication:** Not required
- **Response:** JSON with status and service name
- **Behavior:**
  - MUST return `{"status": "ok", "service": "k8s-cli-api"}`
  - MUST be available for health checks

### Error Handling

#### HTTP Status Codes
- `200 OK`: Successful request
- `404 Not Found`: Resource not found for the authenticated user
- `500 Internal Server Error`: Server-side error

#### Error Response Format
- All error responses MUST include a `detail` field with a descriptive message
- The system MUST log errors with context including username and operation

### Logging

- The system MUST log all API operations with username
- The system MUST log errors with stack traces
- The system MUST use structured logging with timestamps
- The system MUST log task lifecycle events (submit, stop, status check)
- The system MUST log volume lifecycle events (create, delete, status check)

## Implementation Notes

- The API uses FastAPI framework
- The Kubernetes executor is stored in `app.state.executor`
- All executor methods are passed the username for authorization
- Streaming responses use generators to yield log lines
- Request/response models are defined using Pydantic
- CORS and other security middleware may be added as needed
