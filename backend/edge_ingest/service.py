"""
Edge ingest service for processing edge device detections.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from database.persistence import persist_camera, persist_detection

logger = logging.getLogger(__name__)

# Ingestion metrics
_ingest_count = 0
_last_log_time = datetime.now()


def process_detection_background(camera_id: str, camera_name: Optional[str], detection_output: Dict[str, Any]):
    """
    Background task to persist detections only.
    Runs asynchronously after API returns.
    
    ⚠️ ORCHESTRATION NOTE:
    - This function ONLY persists detections to the database
    - Usecase evaluation, alerts, and analytics are triggered by main.py orchestrator
    - Edge devices should call the pipeline orchestrator after ingestion
    """
    try:
        logger.info(f"[EDGE_INGEST] Persisting detections for camera {camera_id}")
        
        # 1. Persist camera (if not exists)
        persist_camera(camera_id, name=camera_name)
        
        # 2. Persist all detections to DB
        detection_ids = []
        for detection in detection_output.get("detections", []):
            det_id = persist_detection(
                camera_id=camera_id,
                object_type=detection["class_name"],
                confidence=detection["confidence"],
                inside_roi=detection["in_roi"],
                screenshot_path=None
            )
            if det_id:
                detection_ids.append(det_id)
        
        # Update first detection ID
        if detection_ids:
            detection_output["first_detection_id"] = detection_ids[0]
        
        logger.info(f"[EDGE_INGEST] Persisted {len(detection_ids)} detections for camera {camera_id}")
        
        # ⚠️ REMOVED: Direct usecase evaluation (moved to main.py orchestrator)
        # Orchestration is now handled by main.py pipeline controller
        
    except Exception as e:
        logger.error(f"Background processing failed for camera {camera_id}: {str(e)}", exc_info=True)


def transform_edge_to_internal(payload) -> Dict[str, Any]:
    """
    Transform edge device payload to internal detection format.
    
    Args:
        payload: EdgeInput payload from edge device
        
    Returns:
        Dictionary in internal detection format
    """
    # Combine persons and objects into single detections list
    all_detections = []
    
    # Process persons
    for person in payload.persons:
        detection = {
            "class_id": 0,  # Usecases only check class_name, not class_id
            "class_name": person.label,  # Map 'label' to 'class_name'
            "confidence": person.confidence,
            "bbox": {
                "x1": person.bbox.x1,
                "y1": person.bbox.y1,
                "x2": person.bbox.x2,
                "y2": person.bbox.y2
            },
            "in_roi": person.in_roi if person.in_roi is not None else False
        }
        all_detections.append(detection)
    
    # Process objects
    for obj in payload.objects:
        detection = {
            "class_id": 0,  # Usecases only check class_name, not class_id
            "class_name": obj.label,  # Map 'label' to 'class_name'
            "confidence": obj.confidence,
            "bbox": {
                "x1": obj.bbox.x1,
                "y1": obj.bbox.y1,
                "x2": obj.bbox.x2,
                "y2": obj.bbox.y2
            },
            "in_roi": obj.in_roi if obj.in_roi is not None else False
        }
        all_detections.append(detection)
    
    # Count ROI detections
    roi_detections_count = sum(1 for d in all_detections if d["in_roi"])
    
    # Parse timestamp
    try:
        ts = datetime.fromisoformat(payload.timestamp.replace('Z', '+00:00'))
    except:
        ts = datetime.now()
    
    # Create internal detection format
    detection_output = {
        "camera_id": payload.camera_id,
        "timestamp": ts.isoformat(),
        "frame_id": payload.frame_id,  # Use frame_id consistently
        "frame_count": payload.frame_id,  # Keep for backward compatibility
        "detections": all_detections,
        "roi_detections_count": roi_detections_count,
        "total_detections_count": len(all_detections),
        "processing_time_ms": 0.0,
        "first_detection_id": None,
        "screenshot_path": None
    }
    
    return detection_output


def resolve_usecases(payload_usecases: Optional[List[str]], query_usecases: Optional[str]) -> List[str]:
    """
    Resolve which usecases to evaluate.
    Priority: payload > query param > default
    
    Args:
        payload_usecases: Usecases from request payload
        query_usecases: Usecases from query parameter (comma-separated)
        
    Returns:
        List of usecase IDs to evaluate
    """
    if payload_usecases and len(payload_usecases) > 0:
        return payload_usecases
    
    if query_usecases:
        return [uc.strip() for uc in query_usecases.split(",")]
    
    return ["person_in_roi"]  # Default usecase


def log_ingestion_rate():
    """
    Log ingestion rate periodically (every 10 seconds).
    """
    global _ingest_count, _last_log_time
    
    _ingest_count += 1
    now = datetime.now()
    if (now - _last_log_time).total_seconds() >= 10:
        logger.info(f"Edge ingest rate: {_ingest_count} frames in last 10s (~{_ingest_count/10:.1f}/sec)")
        _ingest_count = 0
        _last_log_time = now
