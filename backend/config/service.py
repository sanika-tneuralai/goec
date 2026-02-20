from typing import Dict, Optional, List
from config.schemas import CameraConfigRequest, CameraConfigResponse, AllConfigsResponse


# In-memory storage for camera configurations
_camera_configs: Dict[str, CameraConfigResponse] = {}


def create_or_update_camera_config(config_request: CameraConfigRequest) -> CameraConfigResponse:
    """
    Create or update camera configuration
    """
    print(f"[CONFIG SERVICE] create_or_update_camera_config called for camera_id: {config_request.camera_id}")
    print(f"[CONFIG SERVICE] ROIs count: {len(config_request.rois)}")
    print(f"[CONFIG SERVICE] Confidence threshold: {config_request.confidence_threshold}")
    print(f"[CONFIG SERVICE] Detection model: {config_request.detection_model}")
    
    camera_config = CameraConfigResponse(
        camera_id=config_request.camera_id,
        rois=config_request.rois,
        confidence_threshold=config_request.confidence_threshold,
        detection_model=config_request.detection_model
    )
    
    _camera_configs[config_request.camera_id] = camera_config
    
    print(f"[CONFIG SERVICE] Configuration saved successfully for camera_id: {config_request.camera_id}")
    return camera_config


def get_camera_config(camera_id: str) -> Optional[CameraConfigResponse]:
    """
    Get camera configuration by camera_id
    """
    print(f"[CONFIG SERVICE] get_camera_config called for camera_id: {camera_id}")
    
    config = _camera_configs.get(camera_id)
    print(f'config: {config}*********')
    
    if config:
        print(f"[CONFIG SERVICE] Configuration found for camera_id: {camera_id}")
    else:
        print(f"[CONFIG SERVICE] No configuration found for camera_id: {camera_id}")
    
    return config


def get_all_camera_configs() -> AllConfigsResponse:
    """
    Get all camera configurations
    """
    print(f"[CONFIG SERVICE] get_all_camera_configs called")
    print(f"[CONFIG SERVICE] Total configurations in storage: {len(_camera_configs)}")
    
    configs_list = list(_camera_configs.values())
    
    response = AllConfigsResponse(
        cameras=configs_list,
        total=len(configs_list)
    )
    
    print(f"[CONFIG SERVICE] Returning {response.total} configurations")
    return response


def get_camera_rois(camera_id: str) -> List:
    """
    Helper function to get ROIs for a specific camera
    """
    print(f"[CONFIG SERVICE] get_camera_rois called for camera_id: {camera_id}")
    
    config = _camera_configs.get(camera_id)
    if config:
        print(f"[CONFIG SERVICE] Found {len(config.rois)} ROIs for camera_id: {camera_id}")
        return config.rois
    
    print(f"[CONFIG SERVICE] No ROIs found for camera_id: {camera_id}")
    return []


def get_camera_threshold(camera_id: str) -> float:
    """
    Helper function to get confidence threshold for a specific camera
    Returns default of 0.5 if not configured
    """
    print(f"[CONFIG SERVICE] get_camera_threshold called for camera_id: {camera_id}")
    
    config = _camera_configs.get(camera_id)
    if config:
        print(f"[CONFIG SERVICE] Threshold for camera_id {camera_id}: {config.confidence_threshold}")
        return config.confidence_threshold
    
    print(f"[CONFIG SERVICE] No threshold found for camera_id {camera_id}, returning default: 0.5")
    return 0.5


def get_camera_detection_model(camera_id: str) -> str:
    """
    Helper function to get detection model for a specific camera
    Returns default of 'yolov8n' if not configured
    """
    print(f"[CONFIG SERVICE] get_camera_detection_model called for camera_id: {camera_id}")
    
    config = _camera_configs.get(camera_id)
    if config:
        print(f"[CONFIG SERVICE] Detection model for camera_id {camera_id}: {config.detection_model}")
        return config.detection_model
    
    print(f"[CONFIG SERVICE] No detection model found for camera_id {camera_id}, returning default: yolov8n")
    return "yolov8n"
