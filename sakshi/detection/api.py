"""
Detection API endpoints.
"""
from fastapi import APIRouter, HTTPException
import logging

from detection.schemas import DetectionRequest, DetectionResponse, DetectionStats
from detection.service import get_detection_service
from camera.service import camera_manager
from usecase.service import evaluate_person_in_roi

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/detection", tags=["detection"])


@router.post("/detect", response_model=DetectionResponse)
async def detect_objects(request: DetectionRequest):
    """
    Run object detection on current frame from a camera.
    
    **Process:**
    1. Gets current frame from camera manager
    2. Runs YOLO detection
    3. Filters detections by ROI
    4. Returns detection results
    
    **Request Body:**
    - **camera_id**: Camera to detect from (required)
    - **confidence_threshold**: Min confidence (default: 0.5)
    - **iou_threshold**: IOU for NMS (default: 0.45)
    - **classes**: Filter specific class IDs (optional)
    
    **Response:**
    - Detection results with ROI filtering
    - Processing time
    - Frame metadata
    """
    logger.info(f"Detection request for camera: {request.camera_id}")
    
    # Get camera object
    camera = camera_manager.get_camera_stream(request.camera_id)
    if not camera:
        logger.error(f"Camera {request.camera_id} not found or not running")
        raise HTTPException(status_code=404, detail=f"Camera {request.camera_id} not found or not running")
    
    # Get frame from camera
    frame = camera.get_frame()
    if frame is None:
        logger.error(f"No frame available from camera {request.camera_id}")
        raise HTTPException(status_code=400, detail="No frame available from camera")
    
    # Get ROI data from camera
    roi_points = camera.roi_points
    roi_mask = camera.roi_mask
    
    # Run detection
    detection_service = get_detection_service()
    result = detection_service.detect(
        frame=frame,
        camera_id=request.camera_id,
        roi_points=roi_points,
        roi_mask=roi_mask,
        confidence_threshold=request.confidence_threshold,
        iou_threshold=request.iou_threshold,
        classes=request.classes
    )
    
    logger.info(f"Detection completed: {result.total_detections_count} total, {result.roi_detections_count} in ROI")
    
    # Auto-call Usecase API for evaluation
    print(f"[DETECTION] Auto-triggering usecase evaluation for camera: {request.camera_id}")
    try:
        detection_output = result.model_dump() if hasattr(result, 'model_dump') else result.dict()
        usecase_result = evaluate_person_in_roi(
            camera_id=request.camera_id,
            detection_output=detection_output
        )
        print(f"[DETECTION] Usecase evaluation completed - Triggered: {usecase_result['usecase_triggered']}")
    except Exception as e:
        print(f"[DETECTION] Warning: Usecase evaluation failed - {str(e)}")
        # Continue even if usecase fails - don't break detection API
    
    print(f"✓ detect_objects completed for {request.camera_id}")
    
    return result


@router.get("/stats/{camera_id}", response_model=DetectionStats)
async def get_detection_stats(camera_id: str):
    """
    Get detection statistics for a camera.
    
    **Response:**
    - Total frames processed
    - Total detections
    - ROI detections
    - Average processing time
    """
    logger.info(f"Stats request for camera: {camera_id}")
    
    detection_service = get_detection_service()
    stats = detection_service.get_stats(camera_id)
    
    if not stats:
        logger.warning(f"No detection stats found for camera {camera_id}")
        raise HTTPException(status_code=404, detail=f"No detection stats for camera {camera_id}")
    
    print(f"✓ get_detection_stats completed for {camera_id}")
    return stats


@router.delete("/stats/{camera_id}")
async def reset_detection_stats(camera_id: str):
    """
    Reset detection statistics for a camera.
    """
    logger.info(f"Reset stats for camera: {camera_id}")
    
    detection_service = get_detection_service()
    detection_service.reset_stats(camera_id)
    
    print(f"✓ reset_detection_stats completed for {camera_id}")
    return {"status": "success", "message": f"Stats reset for camera {camera_id}"}


@router.get("/health")
async def detection_health():
    """
    Check detection service health.
    """
    try:
        detection_service = get_detection_service()
        device_info = {
            "device": detection_service.device,
            "model_path": detection_service.model_path,
            "model_loaded": detection_service.model is not None
        }
        print("✓ detection_health completed")
        return {
            "status": "healthy",
            "service": "detection",
            **device_info
        }
    except Exception as e:
        logger.error(f"Detection health check failed: {e}")
        print(f"✓ detection_health completed: unhealthy - {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


print("✓ detection.api module loaded")
