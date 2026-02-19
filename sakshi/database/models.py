"""
Database models for Analytics & Reporting.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from database.connection import Base


class Camera(Base):
    __tablename__ = "cameras"
    
    camera_id = Column(String(255), primary_key=True)
    name = Column(String(255))
    location = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Detection(Base):
    __tablename__ = "detections"
    
    detection_id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(String(255), ForeignKey("cameras.camera_id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    object_type = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    inside_roi = Column(Boolean, nullable=False, default=False)
    screenshot_path = Column(String(500), nullable=True)


class UsecaseResult(Base):
    __tablename__ = "usecase_results"
    
    result_id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(String(255), ForeignKey("cameras.camera_id"), nullable=False, index=True)
    usecase_name = Column(String(100), nullable=False)
    detection_id = Column(Integer, ForeignKey("detections.detection_id"), nullable=True)
    triggered = Column(Boolean, nullable=False, default=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class Alert(Base):
    __tablename__ = "alerts"
    
    alert_id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(String(255), ForeignKey("cameras.camera_id"), nullable=False, index=True)
    usecase_name = Column(String(100), nullable=False)
    alert_type = Column(String(50), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    status = Column(String(20), nullable=False)  # 'sent' or 'failed'
    detection_id = Column(Integer, ForeignKey("detections.detection_id"), nullable=True)
    screenshot_path = Column(String(500), nullable=True)


class AnalyticsDaily(Base):
    __tablename__ = "analytics_daily"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    camera_id = Column(String(255), ForeignKey("cameras.camera_id"), nullable=False, index=True)
    total_detections = Column(Integer, nullable=False, default=0)
    roi_violations = Column(Integer, nullable=False, default=0)
    alerts_sent = Column(Integer, nullable=False, default=0)
    
    __table_args__ = (
        UniqueConstraint('date', 'camera_id', name='uix_date_camera'),
    )
