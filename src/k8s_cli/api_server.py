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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
