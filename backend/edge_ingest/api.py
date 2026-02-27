"""
Edge device ingest API.
Receives detection output from edge devices (e.g., Raspberry Pi with Helio)
and forwards it to the usecase pipeline.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional
import logging

from edge_ingest.schemas import EdgeInput
from edge_ingest.service import (
    process_detection_background,
    transform_edge_to_internal,
    log_ingestion_rate
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/edge", tags=["edge"])


@router.post("/ingest")
async def ingest_edge_detection(payload: EdgeInput, background_tasks: BackgroundTasks, usecases: Optional[str] = None):
    """
    Receive detection output from edge device and persist to database.
    
    ⚠️ ORCHESTRATION NOTE:
    - This endpoint ONLY validates input and persists detections
    - It does NOT evaluate usecases, send alerts, or update analytics
    - After calling this endpoint, call /pipeline/execute-edge for orchestration
    
    **Process Flow:**
    1. Edge device → POST /edge/ingest (validates + persists)
    2. Edge device → POST /pipeline/execute-edge (orchestrates usecase → alert → analytics)
    
    **Why Two Steps?**
    - Separation of concerns: ingest ≠ orchestration
    - Ingest can happen in background
    - Orchestration is explicit and traceable
    - Maintains API independence
    
    **This endpoint:**
    - Validates edge device output
    - Returns immediately (async, non-blocking)
    - Persists detections in background
    - Returns transformed detection_output for orchestrator
    
    **Required fields:** camera_id, timestamp, frame_id, person_count, object_count
    
    **Response:**
    - status: "accepted"
    - camera_id: Camera identifier
    - frame_id: Frame ID
    - detections_count: Number of detections
    - detection_output: Transformed output (use this for /pipeline/execute-edge)
    """
    # Transform edge format to internal detection format
    try:
        detection_output = transform_edge_to_internal(payload)
        
        # Schedule background processing (persistence only)
        background_tasks.add_task(
            process_detection_background,
            camera_id=payload.camera_id,
            camera_name=payload.camera_name,
            detection_output=detection_output
        )
        
        # Log ingestion rate periodically
        log_ingestion_rate()
        
        # Return immediately with detection_output for orchestrator
        return {
            "status": "accepted",
            "camera_id": payload.camera_id,
            "frame_id": payload.frame_id,
            "detections_count": detection_output["total_detections_count"],
            "detection_output": detection_output,
            "next_step": "Call POST /pipeline/execute-edge with detection_output to complete processing"
        }
        
    except Exception as e:
        logger.error(f"Edge ingest validation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")
