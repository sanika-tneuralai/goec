"""
Pydantic schemas for usecase module.
"""
from pydantic import BaseModel, Field
from typing import List


class UsecaseRequest(BaseModel):
    """Request to evaluate usecase"""
    camera_id: str = Field(..., description="Camera ID")
    detection_output: dict = Field(..., description="Detection API output")


class UsecaseResponse(BaseModel):
    """Alert-ready payload from usecase evaluation"""
    camera_id: str
    usecase_id: str
    usecase_triggered: bool
    matched_detections: List[dict]
    matched_count: int
