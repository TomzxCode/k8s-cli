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
