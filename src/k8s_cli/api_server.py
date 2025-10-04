import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header

from k8s_cli.k8s_executor import KubernetesTaskExecutor
from k8s_cli.task_models import (
    TaskDefinition,
    TaskListResponse,
    TaskStatus,
    TaskStopResponse,
    TaskSubmitResponse,
    VolumeCreateResponse,
    VolumeDefinition,
    VolumeDeleteResponse,
    VolumeListResponse,
    VolumeStatus,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup"""
    logger.info("Starting API server")
    app.state.executor = KubernetesTaskExecutor()
    logger.info("Kubernetes executor initialized")
    yield
    logger.info("Shutting down API server")


app = FastAPI(
    title="SkyPilot-Compatible Kubernetes Task Launcher",
    description="API server for launching tasks on Kubernetes with SkyPilot YAML compatibility",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "skypilot-k8s-launcher"}


@app.post("/tasks/submit", response_model=TaskSubmitResponse)
async def submit_task(task: TaskDefinition, x_user: str = Header(...)):
    """
    Submit a new task to Kubernetes

    Accepts a SkyPilot-compatible task definition and creates
    a Kubernetes Job to execute it.
    """
    try:
        logger.info(f"User '{x_user}' submitting task: {task.name or 'unnamed'}")
        executor: KubernetesTaskExecutor = app.state.executor
        task_id = await executor.submit_task(task, username=x_user)
        logger.info(f"Task submitted successfully with ID: {task_id} for user '{x_user}'")

        return TaskSubmitResponse(
            task_id=task_id,
            status="submitted",
            message=f"Task submitted successfully with ID: {task_id}",
        )
    except Exception as e:
        logger.error(f"Failed to submit task for user '{x_user}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to submit task: {str(e)}")


@app.post("/tasks/{task_id}/stop", response_model=TaskStopResponse)
async def stop_task(task_id: str, x_user: str = Header(...)):
    """
    Stop a running task

    Terminates the Kubernetes Job associated with the task ID.
    """
    try:
        logger.info(f"User '{x_user}' stopping task: {task_id}")
        executor: KubernetesTaskExecutor = app.state.executor
        success = await executor.stop_task(task_id, username=x_user)

        if not success:
            logger.warning(f"Task not found: {task_id} for user '{x_user}'")
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        logger.info(f"Task stopped successfully: {task_id} for user '{x_user}'")
        return TaskStopResponse(
            task_id=task_id,
            status="stopped",
            message=f"Task {task_id} stopped successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop task {task_id} for user '{x_user}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to stop task: {str(e)}")


@app.get("/tasks", response_model=TaskListResponse)
async def list_tasks(x_user: str = Header(...), all_users: bool = False):
    """
    List all tasks for the current user or all users

    Returns a list of all tasks with their current status.
    If all_users is True, returns tasks from all users.
    """
    try:
        if all_users:
            logger.info(f"Listing tasks for all users (requested by '{x_user}')")
            executor: KubernetesTaskExecutor = app.state.executor
            tasks = await executor.list_tasks(username=None)
            logger.info(f"Found {len(tasks)} tasks for all users")
        else:
            logger.info(f"Listing tasks for user '{x_user}'")
            executor: KubernetesTaskExecutor = app.state.executor
            tasks = await executor.list_tasks(username=x_user)
            logger.info(f"Found {len(tasks)} tasks for user '{x_user}'")

        return TaskListResponse(tasks=tasks)
    except Exception as e:
        logger.error(f"Failed to list tasks for user '{x_user}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")


@app.get("/tasks/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str, x_user: str = Header(...)):
    """
    Get status of a specific task

    Returns detailed status information for the specified task.
    """
    try:
        logger.info(f"Getting status for task: {task_id} for user '{x_user}'")
        executor: KubernetesTaskExecutor = app.state.executor
        task_status = await executor.get_task_status(task_id, username=x_user)

        if not task_status:
            logger.warning(f"Task not found: {task_id} for user '{x_user}'")
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        logger.info(f"Task status retrieved: {task_id} - {task_status.status} for user '{x_user}'")
        return task_status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status for {task_id} for user '{x_user}': {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get task status: {str(e)}"
        )


@app.post("/volumes/create", response_model=VolumeCreateResponse)
async def create_volume(volume: VolumeDefinition, x_user: str = Header(...)):
    """
    Create a new volume (PersistentVolumeClaim)

    Creates a Kubernetes PVC with the specified size and configuration.
    """
    try:
        logger.info(f"User '{x_user}' creating volume: {volume.name}")
        executor: KubernetesTaskExecutor = app.state.executor
        volume_id = await executor.create_volume(volume, username=x_user)
        logger.info(f"Volume created successfully with ID: {volume_id} for user '{x_user}'")

        return VolumeCreateResponse(
            volume_id=volume_id,
            status="created",
            message=f"Volume created successfully with ID: {volume_id}",
        )
    except Exception as e:
        logger.error(f"Failed to create volume for user '{x_user}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create volume: {str(e)}")


@app.get("/volumes", response_model=VolumeListResponse)
async def list_volumes(x_user: str = Header(...), all_users: bool = False):
    """
    List all volumes for the current user or all users

    Returns a list of all volumes (PVCs) with their current status.
    If all_users is True, returns volumes from all users.
    """
    try:
        if all_users:
            logger.info(f"Listing volumes for all users (requested by '{x_user}')")
            executor: KubernetesTaskExecutor = app.state.executor
            volumes = await executor.list_volumes(username=None)
            logger.info(f"Found {len(volumes)} volumes for all users")
        else:
            logger.info(f"Listing volumes for user '{x_user}'")
            executor: KubernetesTaskExecutor = app.state.executor
            volumes = await executor.list_volumes(username=x_user)
            logger.info(f"Found {len(volumes)} volumes for user '{x_user}'")

        return VolumeListResponse(volumes=volumes)
    except Exception as e:
        logger.error(f"Failed to list volumes for user '{x_user}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list volumes: {str(e)}")


@app.delete("/volumes/{volume_id}", response_model=VolumeDeleteResponse)
async def delete_volume(volume_id: str, x_user: str = Header(...)):
    """
    Delete a volume (PersistentVolumeClaim)

    Removes the Kubernetes PVC associated with the volume ID.
    """
    try:
        logger.info(f"User '{x_user}' deleting volume: {volume_id}")
        executor: KubernetesTaskExecutor = app.state.executor
        success = await executor.delete_volume(volume_id, username=x_user)

        if not success:
            logger.warning(f"Volume not found: {volume_id} for user '{x_user}'")
            raise HTTPException(status_code=404, detail=f"Volume {volume_id} not found")

        logger.info(f"Volume deleted successfully: {volume_id} for user '{x_user}'")
        return VolumeDeleteResponse(
            volume_id=volume_id,
            status="deleted",
            message=f"Volume {volume_id} deleted successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete volume {volume_id} for user '{x_user}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete volume: {str(e)}")


@app.get("/volumes/{volume_id}", response_model=VolumeStatus)
async def get_volume_status(volume_id: str, x_user: str = Header(...)):
    """
    Get status of a specific volume

    Returns detailed status information for the specified volume.
    """
    try:
        logger.info(f"Getting status for volume: {volume_id} for user '{x_user}'")
        executor: KubernetesTaskExecutor = app.state.executor
        volume_status = await executor.get_volume_status(volume_id, username=x_user)

        if not volume_status:
            logger.warning(f"Volume not found: {volume_id} for user '{x_user}'")
            raise HTTPException(status_code=404, detail=f"Volume {volume_id} not found")

        logger.info(f"Volume status retrieved: {volume_id} - {volume_status.status} for user '{x_user}'")
        return volume_status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get volume status for {volume_id} for user '{x_user}': {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get volume status: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
