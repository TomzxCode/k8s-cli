# Volume Management Specification

## Overview

This specification defines the volume management system for k8s-cli. The system provides persistent storage capabilities through Kubernetes PersistentVolumeClaims (PVCs), allowing tasks to maintain state across executions.

## Requirements

### Core Functionality

#### Volume Creation
- The system MUST support creating volumes with a specified name and size
- The system MUST generate a unique volume ID for each created volume
- The system MUST create a Kubernetes PersistentVolumeClaim (PVC) for each volume
- The system MAY support specifying a storage class via the `storage_class` field
- The system MUST support specifying access modes via the `access_modes` field
- The system MUST default to `ReadWriteOnce` access mode if not specified
- The system MUST label all PVCs with `skypilot-volume: true`

#### Volume Metadata
- The system MUST store `volume-id` label on the PVC for identification
- The system MUST store `volume-name` label on the PVC for user-friendly names
- The system MUST store `username` label on the PVC for user isolation
- The system MUST store `created-at` annotation on the PVC with ISO timestamp

#### Volume Status Tracking
- The system MUST track the status of each volume (Pending, Bound, Lost)
- The system MUST report volume size, storage class, and access modes
- The system MUST provide creation timestamp for each volume
- The system MUST return metadata including PVC name and namespace

#### Volume Deletion
- The system MUST support deleting a volume by volume ID
- The system MUST delete the associated Kubernetes PVC
- The system MUST prevent users from deleting volumes owned by other users
- The system SHOULD provide a confirmation prompt before deletion (CLI)

#### Volume Listing
- The system MUST support listing all volumes for the current user
- The system MAY support listing volumes for all users (admin operation)
- The system MUST return volume status, size, and metadata for each volume

#### Volume Resolution
- The system MUST support resolving user-friendly volume names to PVC names
- The system MUST look up PVCs by `volume-name` and `username` labels first
- The system MUST fall back to using the volume name as the PVC name directly
- The system MUST use resolved PVC names when mounting volumes in tasks

### CLI Interface

- The system MUST provide a `volumes create` command to create volumes
- The system MUST provide a `volumes list` command to list volumes
- The system MUST provide a `volumes delete` command to delete volumes
- The system SHOULD support the `--storage-class` flag to specify storage class
- The system SHOULD support the `--access-modes` flag to specify access modes
- The system SHOULD support the `--details` flag to show extended information
- The system SHOULD support the `--all-users` flag to list volumes from all users
- The system SHOULD support the `--force` flag to skip deletion confirmation

### REST API Interface

- The system MUST provide a `POST /volumes/create` endpoint to create volumes
- The system MUST provide a `GET /volumes` endpoint to list volumes
- The system MUST provide a `DELETE /volumes/{volume_id}` endpoint to delete volumes
- The system MUST provide a `GET /volumes/{volume_id}` endpoint to get volume status
- The system MUST require an `X-User` header for user identification
- The system MUST support an `all_users` query parameter for privileged operations

### User Isolation

- The system MUST isolate volumes by username using Kubernetes labels
- The system MUST sanitize usernames for use in Kubernetes labels (replace `@` with `-`)
- The system MUST prevent users from accessing volumes owned by other users
- The system MAY allow privileged operations to list volumes across all users

### Error Handling

- The system MUST return appropriate HTTP status codes for API errors
- The system MUST return 404 if a volume ID is not found for the user
- The system MUST provide descriptive error messages for failed operations
- The system MUST validate volume size format (e.g., "10Gi", "1Ti")

### Kubernetes Integration

- The system MUST label all PVCs with `skypilot-volume: true`
- The system MUST use the `default` namespace for all PVCs
- The system MUST respect the specified storage class when creating PVCs
- The system MUST respect the specified access modes when creating PVCs

## Data Models

### VolumeDefinition
- `name` (required): User-friendly volume name
- `size` (required): Volume size in Kubernetes format (e.g., "10Gi", "1Ti")
- `storage_class` (optional): Kubernetes storage class name
- `access_modes` (optional): List of access modes (default: `["ReadWriteOnce"]`)

### VolumeStatus
- `volume_id`: Unique volume identifier
- `name`: User-friendly volume name
- `size`: Volume size
- `storage_class`: Storage class name
- `access_modes`: List of access modes
- `status`: PVC phase (Pending, Bound, Lost)
- `created_at`: ISO timestamp of volume creation
- `username`: User who created the volume
- `metadata`: Additional information including PVC name and namespace

## Implementation Notes

- Volume IDs are 8-character UUID prefixes
- PVC names follow the pattern `{volume-name}-{volume-id}`
- Username sanitization replaces `@` with `-` for DNS-1123 compliance
- Volume resolution is performed when tasks reference volumes by name
- Access modes are specified as a list to support multi-mode configurations
