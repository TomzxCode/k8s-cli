import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from k8s_cli.k8s_executor import KubernetesTaskExecutor
from k8s_cli.api.tasks import router as tasks_router
from k8s_cli.api.volumes import router as volumes_router

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

# Include routers
app.include_router(tasks_router)
app.include_router(volumes_router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "k8s-cli-api"}


if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("K8S_CLI_API_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
