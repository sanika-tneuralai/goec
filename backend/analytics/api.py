"""
Analytics API endpoints.
"""
from fastapi import APIRouter, Query
from datetime import date
from typing import Optional

from analytics.schemas import (
    DailyAnalyticsResponse, DailyAnalytics,
    AlertAnalyticsResponse, AlertAnalytics,
    DetectionAnalyticsResponse, DetectionAnalytics,
    PeopleCountAnalyticsResponse, PeopleCountRecord,
    LivePeopleCountResponse, LiveCameraCount
)
from analytics.service import (
    get_daily_analytics,
    get_alert_analytics,
    get_detection_analytics,
    get_people_count_analytics,
    get_live_people_count
)


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/daily", response_model=DailyAnalyticsResponse)
def get_daily(
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get daily aggregated analytics from analytics_daily table.
    
    **Filters:**
    - **camera_id**: Filter by specific camera
    - **start_date**: Start date for date range
    - **end_date**: End date for date range
    
    **Response:**
    - Aggregated daily analytics with detections, ROI violations, and alerts
    """
    print(f"\n[API] GET /analytics/daily called")
    print(f"[API] Filters: camera_id={camera_id}, start_date={start_date}, end_date={end_date}")
    
    results = get_daily_analytics(camera_id, start_date, end_date)
    
    data = [
        DailyAnalytics(
            date=r.date,
            camera_id=r.camera_id,
            total_detections=r.total_detections,
            roi_violations=r.roi_violations,
            alerts_sent=r.alerts_sent
        )
        for r in results
    ]
    
    print(f"[API] Returning {len(data)} daily analytics records\n")
    
    return DailyAnalyticsResponse(
        data=data,
        total_records=len(data)
    )


@router.get("/alerts", response_model=AlertAnalyticsResponse)
def get_alerts(
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get alert analytics aggregated by camera and usecase.
    
    **Filters:**
    - **camera_id**: Filter by specific camera
    - **start_date**: Start date for date range
    - **end_date**: End date for date range
    
    **Response:**
    - Alert counts per camera and usecase (sent/failed)
    """
    print(f"\n[API] GET /analytics/alerts called")
    print(f"[API] Filters: camera_id={camera_id}, start_date={start_date}, end_date={end_date}")
    
    results = get_alert_analytics(camera_id, start_date, end_date)
    
    data = [
        AlertAnalytics(
            camera_id=r.camera_id,
            usecase_name=r.usecase_name,
            total_alerts=r.total_alerts,
            alerts_sent=r.alerts_sent,
            alerts_failed=r.alerts_failed
        )
        for r in results
    ]
    
    print(f"[API] Returning {len(data)} alert analytics records\n")
    
    return AlertAnalyticsResponse(
        data=data,
        total_records=len(data)
    )


@router.get("/detections", response_model=DetectionAnalyticsResponse)
def get_detections(
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get detection analytics aggregated by camera.
    
    **Filters:**
    - **camera_id**: Filter by specific camera
    - **start_date**: Start date for date range
    - **end_date**: End date for date range
    
    **Response:**
    - Detection counts with ROI violation statistics
    """
    print(f"\n[API] GET /analytics/detections called")
    print(f"[API] Filters: camera_id={camera_id}, start_date={start_date}, end_date={end_date}")
    
    results = get_detection_analytics(camera_id, start_date, end_date)
    
    data = [
        DetectionAnalytics(
            camera_id=r.camera_id,
            total_detections=r.total_detections,
            roi_detections=r.roi_detections,
            non_roi_detections=r.non_roi_detections,
            roi_violation_rate=round((r.roi_detections / r.total_detections * 100), 2) if r.total_detections > 0 else 0.0
        )
        for r in results
    ]
    
    print(f"[API] Returning {len(data)} detection analytics records\n")
    
    return DetectionAnalyticsResponse(
        data=data,
        total_records=len(data)
    )


@router.get("/people-count", response_model=PeopleCountAnalyticsResponse)
def get_people_count(
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get people count analytics from usecase evaluations.
    
    **Filters:**
    - **camera_id**: Filter by specific camera
    - **start_date**: Start date for date range
    - **end_date**: End date for date range
    
    **Response:**
    - Time-series people count data with statistics (avg, min, max)
    """
    print(f"\n[API] GET /analytics/people-count called")
    print(f"[API] Filters: camera_id={camera_id}, start_date={start_date}, end_date={end_date}")
    
    results = get_people_count_analytics(camera_id, start_date, end_date)
    
    data = []
    counts = []
    
    for r in results:
        people_count = r.result_metadata.get('people_count', 0) if r.result_metadata else 0
        counts.append(people_count)
        
        data.append(PeopleCountRecord(
            timestamp=r.timestamp,
            camera_id=r.camera_id,
            frame_id=r.frame_id,
            people_count=people_count
        ))
    
    # Calculate statistics
    avg_count = sum(counts) / len(counts) if counts else 0.0
    max_count = max(counts) if counts else 0
    min_count = min(counts) if counts else 0
    
    print(f"[API] Returning {len(data)} people_count records")
    print(f"[API] Stats: avg={avg_count:.1f}, min={min_count}, max={max_count}\n")
    
    return PeopleCountAnalyticsResponse(
        data=data,
        total_records=len(data),
        average_count=round(avg_count, 2),
        max_count=max_count,
        min_count=min_count
    )


@router.get("/live/people-count", response_model=LivePeopleCountResponse)
def get_live_people_count_endpoint():
    """
    Get live people count per camera.
    
    Returns the most recent people count for each camera.
    Designed for real-time dashboard polling.
    
    **Response:**
    - Current timestamp
    - Latest people count per camera
    """
    from datetime import datetime
    
    print(f"\n[API] GET /analytics/live/people-count called")
    
    results = get_live_people_count()
    
    cameras = []
    for r in results:
        people_count = r.result_metadata.get('people_count', 0) if r.result_metadata else 0
        cameras.append(LiveCameraCount(
            camera_id=r.camera_id,
            people_count=people_count
        ))
    
    print(f"[API] Returning live count for {len(cameras)} cameras\n")
    
    return LivePeopleCountResponse(
        timestamp=datetime.utcnow().isoformat(),
        cameras=cameras
    )
