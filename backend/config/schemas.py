from typing import List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class BoundingBox(BaseModel):
    """Bounding box ROI definition"""
    x: float = Field(..., description="Top-left x coordinate")
    y: float = Field(..., description="Top-left y coordinate")
    width: float = Field(..., gt=0, description="Width of bounding box")
    height: float = Field(..., gt=0, description="Height of bounding box")


class Polygon(BaseModel):
    """Polygon ROI definition"""
    points: List[List[float]] = Field(..., description="List of [x, y] coordinates")
    
    @field_validator('points')
    @classmethod
    def validate_points(cls, v):
        if len(v) < 3:
            raise ValueError("Polygon must have at least 3 points")
        for point in v:
            if len(point) != 2:
                raise ValueError("Each point must have exactly 2 coordinates [x, y]")
        return v


class ROI(BaseModel):
    """Region of Interest definition"""
    roi_id: str = Field(..., description="Unique identifier for the ROI")
    roi_type: str = Field(..., description="Type of ROI: 'bbox' or 'polygon'")
    roi_data: Union[BoundingBox, Polygon] = Field(..., description="ROI data")
    
    @field_validator('roi_type')
    @classmethod
    def validate_roi_type(cls, v):
        if v not in ['bbox', 'polygon']:
            raise ValueError("roi_type must be 'bbox' or 'polygon'")
        return v


class CameraConfigRequest(BaseModel):
    """Request model for creating/updating camera configuration"""
    camera_id: str = Field(..., description="Unique camera identifier")
    rois: List[ROI] = Field(default_factory=list, description="List of ROIs for this camera")
    confidence_threshold: Optional[float] = Field(0.5, ge=0.0, le=1.0, description="Detection confidence threshold")
    detection_model: Optional[str] = Field("yolov8n", description="Detection model identifier")


class CameraConfigResponse(BaseModel):
    """Response model for camera configuration"""
    camera_id: str
    rois: List[ROI]
    confidence_threshold: float
    detection_model: str


class AllConfigsResponse(BaseModel):
    """Response model for all camera configurations"""
    cameras: List[CameraConfigResponse]
    total: int
