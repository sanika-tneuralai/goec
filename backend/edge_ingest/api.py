"""
Edge device ingest API.
Receives detection output from edge devices (e.g., Raspberry Pi with Helio)
and forwards it to the usecase pipeline.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from usecase.service import evaluate_usecases
from database.persistence import persist_camera, persist_detection, persist_usecase_result

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/edge", tags=["edge"])

# Ingestion metrics
_ingest_count = 0
_last_log_time = datetime.now()


class EdgeBoundingBox(BaseModel):
    """Bounding box from edge device"""
    x1: float
    y1: float
    x2: float
    y2: float


class EdgeDetection(BaseModel):
    """Single detection from edge device"""
    label: str = Field(..., description="Class label (e.g., 'person', 'product_a')")
    confidence: float
    bbox: EdgeBoundingBox
    class_id: Optional[int] = Field(None, description="Class ID (optional)")
    in_roi: Optional[bool] = Field(False, description="Whether detection is in ROI")


class EdgeInput(BaseModel):
    """Edge device detection output format"""
    camera_id: str = Field(..., description="Camera identifier")
    camera_name: Optional[str] = Field(None, description="Camera name")
    timestamp: str = Field(..., description="Detection timestamp")
    frame_id: int = Field(..., description="Frame identifier")
    person_count: int = Field(..., description="Number of persons detected")
    persons: List[EdgeDetection] = Field(default_factory=list, description="Person detections")
    object_count: int = Field(..., description="Number of objects detected")
    objects: List[EdgeDetection] = Field(default_factory=list, description="Object detections")
    class_summary: Optional[Dict[str, int]] = Field(None, description="Summary of detected classes")
    usecases: Optional[List[str]] = Field(None, description="List of usecase IDs to evaluate")


def process_detection_background(camera_id: str, camera_name: Optional[str], detection_output: Dict[str, Any], usecases: List[str]):
    """
    Background task to persist detections and evaluate usecases.
    Runs asynchronously after API returns.
    """
    try:
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
        
        # 3. Evaluate usecases
        result = evaluate_usecases(
            camera_id=camera_id,
            detection_output=detection_output,
            usecases=usecases
        )
        
        # 4. Persist usecase results
        for uc_result in result.get("results", []):
            persist_usecase_result(
                camera_id=camera_id,
                usecase_name=uc_result.usecase_id,
                triggered=uc_result.triggered,
                detection_id=uc_result.detection_id
            )
        
    except Exception as e:
        logger.error(f"Background processing failed for camera {camera_id}: {str(e)}", exc_info=True)


@router.post("/ingest")
async def ingest_edge_detection(payload: EdgeInput, background_tasks: BackgroundTasks, usecases: Optional[str] = None):
    """
    Receive detection output from edge device and forward to usecase pipeline.
    
    This endpoint:
    - Validates edge device output
    - Returns immediately (async, non-blocking)
    - Processes DB persistence and usecase evaluation in background
    
    Required fields: camera_id, timestamp, frame_id, person_count, object_count
    Optional: usecases (defaults to ["person_in_roi"] if not provided)
    """
    global _ingest_count, _last_log_time
    
    # Use usecases from payload, or query param, or default
    usecase_list = payload.usecases
    if not usecase_list or len(usecase_list) == 0:
        if usecases:
            usecase_list = [uc.strip() for uc in usecases.split(",")]
        else:
            usecase_list = ["person_in_roi"]  # Default usecase
    
    # Map edge format to internal detection format
    try:
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
            "frame_count": payload.frame_id,
            "detections": all_detections,
            "roi_detections_count": roi_detections_count,
            "total_detections_count": len(all_detections),
            "processing_time_ms": 0.0,
            "first_detection_id": None,
            "screenshot_path": None
        }
        
        # Schedule background processing
        background_tasks.add_task(
            process_detection_background,
            camera_id=payload.camera_id,
            camera_name=payload.camera_name,
            detection_output=detection_output,
            usecases=usecase_list
        )
        
        # Periodic logging (not per-frame)
        _ingest_count += 1
        now = datetime.now()
        if (now - _last_log_time).total_seconds() >= 10:
            logger.info(f"Edge ingest rate: {_ingest_count} frames in last 10s (~{_ingest_count/10:.1f}/sec)")
            _ingest_count = 0
            _last_log_time = now
        
        # Return immediately
        return {
            "status": "accepted",
            "camera_id": payload.camera_id,
            "frame_id": payload.frame_id,
            "detections_count": len(all_detections)
        }
        
    except Exception as e:
        logger.error(f"Edge ingest validation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")
