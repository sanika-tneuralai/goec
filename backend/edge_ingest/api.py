"""
Edge device ingest API.
Receives detection output from edge devices (e.g., Raspberry Pi with Helio)
and forwards it to the usecase pipeline.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from usecase.service import evaluate_usecases

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/edge", tags=["edge"])


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


@router.post("/ingest")
def ingest_edge_detection(payload: EdgeInput):
    """
    Receive detection output from edge device and forward to usecase pipeline.
    
    This endpoint:
    - Validates edge device output
    - Converts to internal detection format
    - Forwards to usecase evaluation
    - Returns usecase results
    
    Required fields: camera_id, timestamp, frame_id, person_count, object_count
    Optional: usecases (if not provided, must be specified in query param or returns error)
    """
    logger.info(f"Edge ingest: camera_id={payload.camera_id}, frame_id={payload.frame_id}, persons={payload.person_count}, objects={payload.object_count}")
    
    # Validate usecases specified
    if not payload.usecases or len(payload.usecases) == 0:
        raise HTTPException(status_code=400, detail="'usecases' field is required and must contain at least one usecase ID")
    
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
            "processing_time_ms": 0.0,  # Not available from edge
            "first_detection_id": None,  # Will be set by usecase if needed
            "screenshot_path": None  # Not available from edge
        }
        
        # Forward to usecase evaluation
        result = evaluate_usecases(
            camera_id=payload.camera_id,
            detection_output=detection_output,
            usecases=payload.usecases
        )
        
        logger.info(f"Edge ingest complete: camera_id={payload.camera_id}, results={len(result['results'])}")
        return result
        
    except Exception as e:
        logger.error(f"Edge ingest failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Edge ingest failed: {str(e)}")
