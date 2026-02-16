from fastapi import APIRouter, HTTPException, status
from config.schemas import CameraConfigRequest, CameraConfigResponse, AllConfigsResponse
from config import service


router = APIRouter(prefix="/config", tags=["Configuration"])


@router.post("/camera", response_model=CameraConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_camera_configuration(config_request: CameraConfigRequest):
    """
    Create or update camera configuration
    """
    print(f"[CONFIG API] POST /config/camera called")
    print(f"[CONFIG API] Request data: camera_id={config_request.camera_id}")
    
    try:
        result = service.create_or_update_camera_config(config_request)
        print(f"[CONFIG API] Successfully created/updated configuration for camera_id: {config_request.camera_id}")
        return result
    except Exception as e:
        print(f"[CONFIG API] Error creating/updating configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create/update configuration: {str(e)}"
        )


@router.get("/camera/{camera_id}", response_model=CameraConfigResponse)
async def get_camera_configuration(camera_id: str):
    """
    Get camera configuration by camera_id
    """
    print(f"[CONFIG API] GET /config/camera/{camera_id} called")
    
    config = service.get_camera_config(camera_id)
    
    if not config:
        print(f"[CONFIG API] Camera configuration not found for camera_id: {camera_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration not found for camera_id: {camera_id}"
        )
    
    print(f"[CONFIG API] Returning configuration for camera_id: {camera_id}")
    return config


@router.get("/cameras", response_model=AllConfigsResponse)
async def get_all_camera_configurations():
    """
    Get all camera configurations
    """
    print(f"[CONFIG API] GET /config/cameras called")
    
    try:
        result = service.get_all_camera_configs()
        print(f"[CONFIG API] Returning {result.total} camera configurations")
        return result
    except Exception as e:
        print(f"[CONFIG API] Error retrieving configurations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve configurations: {str(e)}"
        )
