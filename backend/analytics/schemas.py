"""
Analytics Pydantic schemas.
"""
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional


# Analytics Daily Response
class DailyAnalytics(BaseModel):
    date: date
    camera_id: str
    total_detections: int
    roi_violations: int
    alerts_sent: int


class DailyAnalyticsResponse(BaseModel):
    data: list[DailyAnalytics]
    total_records: int


# Alert Analytics Response
class AlertAnalytics(BaseModel):
    camera_id: str
    usecase_name: str
    total_alerts: int
    alerts_sent: int
    alerts_failed: int


class AlertAnalyticsResponse(BaseModel):
    data: list[AlertAnalytics]
    total_records: int


# Detection Analytics Response
class DetectionAnalytics(BaseModel):
    camera_id: str
    total_detections: int
    roi_detections: int
    non_roi_detections: int
    roi_violation_rate: float


class DetectionAnalyticsResponse(BaseModel):
    data: list[DetectionAnalytics]
    total_records: int


# People Count Analytics Response
class PeopleCountRecord(BaseModel):
    timestamp: datetime
    camera_id: str
    frame_id: Optional[int]
    people_count: int


class PeopleCountAnalyticsResponse(BaseModel):
    data: list[PeopleCountRecord]
    total_records: int
    average_count: float
    max_count: int
    min_count: int
