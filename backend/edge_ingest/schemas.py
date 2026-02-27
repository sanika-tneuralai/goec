"""
Pydantic schemas for edge_ingest module.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict


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
