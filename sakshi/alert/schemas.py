"""
Pydantic schemas for alert module.
"""
from pydantic import BaseModel, Field
from typing import List


class AlertRequest(BaseModel):
    """Alert-ready payload from Usecase API"""
    camera_id: str = Field(..., description="Camera ID")
    usecase_id: str = Field(..., description="Usecase identifier")
    alert_required: bool = Field(..., description="Whether alert is required")
    alert_type: str = Field(..., description="Type of alert")
    alert_objects: List[dict] = Field(..., description="Objects that triggered the alert")
    alert_count: int = Field(..., description="Number of objects in alert")


class AlertResponse(BaseModel):
    """Response after processing alert"""
    camera_id: str
    alert_sent: bool
    alert_type: str
    alert_count: int
    message: str
