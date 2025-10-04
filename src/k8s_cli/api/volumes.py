import logging

from fastapi import APIRouter, HTTPException, Header, Request

from k8s_cli.k8s_executor import KubernetesTaskExecutor
from k8s_cli.task_models import (
    VolumeCreateResponse,
    VolumeDefinition,
    VolumeDeleteResponse,
    VolumeListResponse,
    VolumeStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/volumes", tags=["volumes"])


@router.post("/create", response_model=VolumeCreateResponse)
async def create_volume(request: Request, volume: VolumeDefinition, x_user: str = Header(...)):
    """
    Create a new volume (PersistentVolumeClaim)

    Creates a Kubernetes PVC with the specified size and configuration.
    """
    try:
        logger.info(f"User '{x_user}' creating volume: {volume.name}")
        executor: KubernetesTaskExecutor = request.app.state.executor
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


@router.get("", response_model=VolumeListResponse)
async def list_volumes(request: Request, x_user: str = Header(...), all_users: bool = False):
    """
    List all volumes for the current user or all users

    Returns a list of all volumes (PVCs) with their current status.
    If all_users is True, returns volumes from all users.
    """
    try:
        executor: KubernetesTaskExecutor = request.app.state.executor
        if all_users:
            logger.info(f"Listing volumes for all users (requested by '{x_user}')")
            volumes = await executor.list_volumes(username=None)
            logger.info(f"Found {len(volumes)} volumes for all users")
        else:
            logger.info(f"Listing volumes for user '{x_user}'")
            volumes = await executor.list_volumes(username=x_user)
            logger.info(f"Found {len(volumes)} volumes for user '{x_user}'")

        return VolumeListResponse(volumes=volumes)
    except Exception as e:
        logger.error(f"Failed to list volumes for user '{x_user}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list volumes: {str(e)}")


@router.delete("/{volume_id}", response_model=VolumeDeleteResponse)
async def delete_volume(request: Request, volume_id: str, x_user: str = Header(...)):
    """
    Delete a volume (PersistentVolumeClaim)

    Removes the Kubernetes PVC associated with the volume ID.
    """
    try:
        logger.info(f"User '{x_user}' deleting volume: {volume_id}")
        executor: KubernetesTaskExecutor = request.app.state.executor
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


@router.get("/{volume_id}", response_model=VolumeStatus)
async def get_volume_status(request: Request, volume_id: str, x_user: str = Header(...)):
    """
    Get status of a specific volume

    Returns detailed status information for the specified volume.
    """
    try:
        logger.info(f"Getting status for volume: {volume_id} for user '{x_user}'")
        executor: KubernetesTaskExecutor = request.app.state.executor
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
