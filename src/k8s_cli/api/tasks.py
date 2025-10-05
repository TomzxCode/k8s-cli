import logging

from fastapi import APIRouter, HTTPException, Header, Request

from k8s_cli.k8s_executor import KubernetesTaskExecutor
from k8s_cli.task_models import (
    TaskDefinition,
    TaskListResponse,
    TaskStatus,
    TaskStopAllResponse,
    TaskStopResponse,
    TaskSubmitResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/submit", response_model=TaskSubmitResponse)
def submit_task(request: Request, task: TaskDefinition, x_user: str = Header(...)):
    """
    Submit a new task to Kubernetes

    Accepts a SkyPilot-compatible task definition and creates
    a Kubernetes Job to execute it.
    """
    try:
        logger.info(f"User '{x_user}' submitting task: {task.name or 'unnamed'}")
        executor: KubernetesTaskExecutor = request.app.state.executor
        task_id = executor.submit_task(task, username=x_user)
        logger.info(f"Task submitted successfully with ID: {task_id} for user '{x_user}'")

        return TaskSubmitResponse(
            task_id=task_id,
            status="submitted",
            message=f"Task submitted successfully with ID: {task_id}",
        )
    except Exception as e:
        logger.error(f"Failed to submit task for user '{x_user}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to submit task: {str(e)}")


@router.post("/{task_id}/stop", response_model=TaskStopResponse)
def stop_task(request: Request, task_id: str, x_user: str = Header(...)):
    """
    Stop a running task

    Terminates the Kubernetes Job associated with the task ID.
    """
    try:
        logger.info(f"User '{x_user}' stopping task: {task_id}")
        executor: KubernetesTaskExecutor = request.app.state.executor
        success = executor.stop_task(task_id, username=x_user)

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


@router.post("/stop", response_model=TaskStopAllResponse)
def stop_all_tasks(request: Request, x_user: str = Header(...), all_users: bool = False):
    """
    Stop all tasks for current user or all users

    Terminates all Kubernetes Jobs for the user, or all users if all_users is True.
    """
    try:
        executor: KubernetesTaskExecutor = request.app.state.executor
        if all_users:
            logger.info(f"User '{x_user}' stopping all tasks for all users")
            count = executor.stop_all_tasks(username=None)
            logger.info(f"Stopped {count} tasks for all users")
            message = f"Stopped {count} tasks for all users"
        else:
            logger.info(f"User '{x_user}' stopping all their tasks")
            count = executor.stop_all_tasks(username=x_user)
            logger.info(f"Stopped {count} tasks for user '{x_user}'")
            message = f"Stopped {count} tasks"

        return TaskStopAllResponse(
            count=count,
            status="stopped",
            message=message,
        )
    except Exception as e:
        logger.error(f"Failed to stop all tasks for user '{x_user}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to stop all tasks: {str(e)}")


@router.get("", response_model=TaskListResponse)
def list_tasks(request: Request, x_user: str = Header(...), all_users: bool = False):
    """
    List all tasks for the current user or all users

    Returns a list of all tasks with their current status.
    If all_users is True, returns tasks from all users.
    """
    try:
        executor: KubernetesTaskExecutor = request.app.state.executor
        if all_users:
            logger.info(f"Listing tasks for all users (requested by '{x_user}')")
            tasks = executor.list_tasks(username=None)
            logger.info(f"Found {len(tasks)} tasks for all users")
        else:
            logger.info(f"Listing tasks for user '{x_user}'")
            tasks = executor.list_tasks(username=x_user)
            logger.info(f"Found {len(tasks)} tasks for user '{x_user}'")

        return TaskListResponse(tasks=tasks)
    except Exception as e:
        logger.error(f"Failed to list tasks for user '{x_user}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")


@router.get("/{task_id}", response_model=TaskStatus)
def get_task_status(request: Request, task_id: str, x_user: str = Header(...)):
    """
    Get status of a specific task

    Returns detailed status information for the specified task.
    """
    try:
        logger.info(f"Getting status for task: {task_id} for user '{x_user}'")
        executor: KubernetesTaskExecutor = request.app.state.executor
        task_status = executor.get_task_status(task_id, username=x_user)

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
