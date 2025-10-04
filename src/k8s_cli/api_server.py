from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import yaml

from k8s_cli.task_models import (
    TaskDefinition,
    TaskSubmitResponse,
    TaskListResponse,
    TaskStopResponse,
    TaskStatus
)
from k8s_cli.k8s_executor import KubernetesTaskExecutor


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup"""
    app.state.executor = KubernetesTaskExecutor()
    yield


app = FastAPI(
    title="SkyPilot-Compatible Kubernetes Task Launcher",
    description="API server for launching tasks on Kubernetes with SkyPilot YAML compatibility",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "skypilot-k8s-launcher"}


@app.post("/tasks/submit", response_model=TaskSubmitResponse)
async def submit_task(task: TaskDefinition):
    """
    Submit a new task to Kubernetes

    Accepts a SkyPilot-compatible task definition and creates
    a Kubernetes Job to execute it.
    """
    try:
        executor: KubernetesTaskExecutor = app.state.executor
        task_id = await executor.submit_task(task)

        return TaskSubmitResponse(
            task_id=task_id,
            status="submitted",
            message=f"Task submitted successfully with ID: {task_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit task: {str(e)}")


@app.post("/tasks/{task_id}/stop", response_model=TaskStopResponse)
async def stop_task(task_id: str):
    """
    Stop a running task

    Terminates the Kubernetes Job associated with the task ID.
    """
    try:
        executor: KubernetesTaskExecutor = app.state.executor
        success = await executor.stop_task(task_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        return TaskStopResponse(
            task_id=task_id,
            status="stopped",
            message=f"Task {task_id} stopped successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop task: {str(e)}")


@app.get("/tasks", response_model=TaskListResponse)
async def list_tasks():
    """
    List all tasks

    Returns a list of all tasks with their current status.
    """
    try:
        executor: KubernetesTaskExecutor = app.state.executor
        tasks = await executor.list_tasks()

        return TaskListResponse(tasks=tasks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")


@app.get("/tasks/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """
    Get status of a specific task

    Returns detailed status information for the specified task.
    """
    try:
        executor: KubernetesTaskExecutor = app.state.executor
        task_status = await executor.get_task_status(task_id)

        if not task_status:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        return task_status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
