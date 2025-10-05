from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Resources(BaseModel):
    """Resource requirements for a task"""

    cpus: Optional[str] = None
    memory: Optional[str] = None
    accelerators: Optional[str] = None
    instance_type: Optional[str] = None
    use_spot: Optional[bool] = None
    disk_size: Optional[int] = None
    ports: Optional[List[int]] = None
    image_id: Optional[str] = None


class TaskDefinition(BaseModel):
    """SkyPilot-compatible task definition"""

    name: Optional[str] = None
    workdir: Optional[str] = None
    num_nodes: int = Field(default=1, ge=1)
    resources: Optional[Resources] = None
    envs: Optional[Dict[str, str]] = None
    file_mounts: Optional[Dict[str, str]] = None
    volumes: Optional[Dict[str, str]] = None  # {mount_path: volume_name}
    setup: Optional[str] = None
    run: str


class TaskStatus(BaseModel):
    """Task status information"""

    task_id: str
    name: Optional[str]
    status: str  # pending, running, completed, failed, stopped
    created_at: str
    updated_at: str
    username: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TaskSubmitResponse(BaseModel):
    """Response from task submission"""

    task_id: str
    status: str
    message: str


class TaskListResponse(BaseModel):
    """Response for listing tasks"""

    tasks: List[TaskStatus]


class TaskStopResponse(BaseModel):
    """Response from stopping a task"""

    task_id: str
    status: str
    message: str


class TaskStopAllResponse(BaseModel):
    """Response from stopping all tasks"""

    count: int
    status: str
    message: str


class VolumeDefinition(BaseModel):
    """Volume definition for creating a PVC"""

    name: str
    size: str  # e.g., "10Gi"
    storage_class: Optional[str] = None
    access_modes: Optional[List[str]] = Field(default_factory=lambda: ["ReadWriteOnce"])


class VolumeStatus(BaseModel):
    """Volume status information"""

    volume_id: str
    name: str
    size: str
    storage_class: Optional[str] = None
    access_modes: List[str]
    status: str  # Pending, Bound, Lost, etc.
    created_at: str
    username: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class VolumeCreateResponse(BaseModel):
    """Response from volume creation"""

    volume_id: str
    status: str
    message: str


class VolumeListResponse(BaseModel):
    """Response for listing volumes"""

    volumes: List[VolumeStatus]


class VolumeDeleteResponse(BaseModel):
    """Response from deleting a volume"""

    volume_id: str
    status: str
    message: str
