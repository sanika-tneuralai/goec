import sys
import os

# Add DeepStream path FIRST, before any other imports
deepstream_path = '/opt/nvidia/deepstream/deepstream-6.4/lib'
if deepstream_path not in sys.path:
    sys.path.insert(0, deepstream_path)

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Optional, List
from pydantic import BaseModel, Field
import logging
import uvicorn


# Configure logging FIRST before any other imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('camera_api.log')
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Import here to avoid circular imports
    from camera.service import camera_manager
    from common.utils import log_system_info
    from database.connection import init_db
    from analytics.scheduler import start_scheduler, stop_scheduler
    
    # Startup
    logger.info("=" * 60)
    logger.info("Starting Camera Management API with DeepStream")
    logger.info("=" * 60)
    log_system_info()
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Start analytics scheduler
    start_scheduler()
    logger.info("Analytics scheduler started")
    
    # Log GStreamer info
    try:
        import gi
        gi.require_version('Gst', '1.0')
        from gi.repository import Gst
        logger.info(f"GStreamer version: {Gst.version_string()}")
    except Exception as e:
        logger.error(f"GStreamer not available: {str(e)}")
    
    logger.info("API server started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Camera Management API")
    try:
        await camera_manager.stop_all()
        logger.info("All cameras stopped")
    except Exception as e:
        logger.error(f"Error stopping cameras during shutdown: {str(e)}")
    
    # Stop scheduler
    stop_scheduler()
    logger.info("Analytics scheduler stopped")
    
    logger.info("API server shut down successfully")
    logger.info("✓ lifespan completed")


# Create FastAPI application
app = FastAPI(
    title="Camera Management & Detection API",
    description="""
    ## High-Performance RTSP Camera Stream Management & Object Detection
    
    ### Features:
    - **Camera Management**: RTSP stream handling with ROI support
    - **Object Detection**: YOLO-based detection with ROI filtering
    - **Single Camera Mode**: For < 10 cameras with independent processing
    - **Multi-Stream Mode**: For 100+ cameras with batched GPU processing
    - **Hardware Acceleration**: NVIDIA DeepStream for optimal performance
    - **ROI Support**: Define custom regions of interest for queue monitoring
    - **Real-time Processing**: Low-latency frame extraction and detection
    
    ### Camera Modes:
    
    #### Single Camera Mode
    - Best for: < 10 cameras
    - Each camera runs independently
    - Lower latency per camera
    - Use `/camera/start` endpoint
    
    #### Multi-Stream Mode (Recommended for 100+ cameras)
    - Best for: 100+ cameras
    - Batched GPU processing
    - Optimal resource utilization
    - Use `/camera/start-multi` endpoint
    
    ### Quick Start:
    1. Start a camera: `POST /camera/start`
    2. Check status: `GET /camera/status/{camera_id}`
    3. Get frame: `GET /camera/frame/{camera_id}`
    4. Run detection: `POST /detection/detect`
    5. Stop camera: `DELETE /camera/stop/{camera_id}`
    
    For 100+ cameras, use multi-stream mode for best performance!
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "detail": str(exc)
        }
    )


# Import and include routers AFTER app creation
from camera.api import router as camera_router
from detection.api import router as detection_router
from usecase.api import router as usecase_router
from config.api import router as config_router
from alert.api import router as alert_router
from analytics.api import router as analytics_router
from edge_ingest.api import router as edge_ingest_router

app.include_router(camera_router)
app.include_router(detection_router)
app.include_router(usecase_router)
app.include_router(config_router)
app.include_router(alert_router)
app.include_router(analytics_router)
app.include_router(edge_ingest_router)


# ============================================================================
# FRONTEND STATIC FILES - DASHBOARD
# ============================================================================

# Get the path to the frontend directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")

# Mount static files (if frontend has CSS/JS/images)
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
    logger.info(f"Frontend directory mounted: {FRONTEND_DIR}")


@app.get("/", include_in_schema=False)
async def serve_dashboard():
    """Serve the dashboard HTML at root URL"""
    dashboard_path = os.path.join(FRONTEND_DIR, "dashboard.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return JSONResponse(
        status_code=404,
        content={"message": "Dashboard not found. Ensure frontend/dashboard.html exists."}
    )


# ============================================================================
# ORCHESTRATION LAYER - PIPELINE CONTROLLER
# ============================================================================

class PipelineRequest(BaseModel):
    """Request schema for pipeline execution"""
    camera_id: str = Field(..., description="Camera identifier")
    usecases: Optional[List[str]] = Field(
        None, 
        description="List of usecases to evaluate. If None, uses defaults."
    )
    confidence_threshold: Optional[float] = Field(
        0.5, 
        ge=0.0, 
        le=1.0,
        description="Detection confidence threshold"
    )


@app.post("/pipeline/execute", tags=["pipeline"])
def execute_pipeline(request: PipelineRequest):
    """
    Orchestrate the LOCAL/INTERNAL pipeline: Camera → Detection → Usecase → Alert
    
    ⚠️ MODE: Local/Internal (camera + detection run on server)
    For edge devices, use /pipeline/execute-edge instead.
    
    This is the ONLY place where pipeline logic exists.
    Each API is called independently via HTTP.
    
    **Request Body:**
    - **camera_id**: Camera identifier (required)
    - **usecases**: List of usecase IDs (optional, defaults to all)
    - **confidence_threshold**: Detection confidence 0.0-1.0 (optional, default: 0.5)
    
    **Example:**
    ```json
    {
      "camera_id": "s1_cam_1",
      "confidence_threshold": 0.5,
      "usecases": ["person_in_roi", "crowd_in_roi"]
    }
    ```
    """
    print("\n" + "="*80)
    print("[ORCHESTRATOR] LOCAL PIPELINE EXECUTION STARTED")
    print("="*80)
    print(f"[ORCHESTRATOR] Mode: LOCAL (camera + detection on server)")
    print(f"[ORCHESTRATOR] Camera ID: {request.camera_id}")
    print(f"[ORCHESTRATOR] Usecases: {request.usecases or ['person_in_roi', 'crowd_in_roi', 'restricted_zone_breach']}")
    print(f"[ORCHESTRATOR] Confidence Threshold: {request.confidence_threshold}")
    print("="*80 + "\n")
    
    import requests
    from common.config import API_BASE_URL
    base_url = API_BASE_URL
    timeout = 30  # 30 second timeout for each API call
    
    # Default usecases if none provided
    usecases = request.usecases or ["person_in_roi", "crowd_in_roi", "restricted_zone_breach"]
    
    try:
        # STEP 1: Get frame from Camera API
        print(f"[ORCHESTRATOR] STEP 1/4: Calling Camera API")
        print(f"[ORCHESTRATOR] Endpoint: GET {base_url}/camera/frame/{request.camera_id}")
        
        camera_response = requests.get(f"{base_url}/camera/frame/{request.camera_id}", timeout=timeout)
        print(f"[ORCHESTRATOR] Camera API Response: {camera_response.status_code}")
        
        if camera_response.status_code != 200:
            print(f"[ORCHESTRATOR] ERROR: Camera API failed")
            raise HTTPException(status_code=camera_response.status_code, 
                              detail=f"Camera API failed: {camera_response.text}")
        
        camera_data = camera_response.json()
        print(f"[ORCHESTRATOR] Camera API Success")
        print(f"[ORCHESTRATOR]   - Frame status: {camera_data.get('status')}")
        print(f"[ORCHESTRATOR]   - Backend: {camera_data.get('backend')}")
        print("")
        
        # STEP 2: Run Detection API
        print(f"[ORCHESTRATOR] STEP 2/4: Calling Detection API")
        print(f"[ORCHESTRATOR] Endpoint: POST {base_url}/detection/detect")
        
        detection_payload = {
            "camera_id": request.camera_id,
            "confidence_threshold": request.confidence_threshold
        }
        print(f"[ORCHESTRATOR] Detection payload: {detection_payload}")
        
        detection_response = requests.post(
            f"{base_url}/detection/detect",
            json=detection_payload,
            timeout=timeout
        )
        print(f"[ORCHESTRATOR] Detection API Response: {detection_response.status_code}")
        
        if detection_response.status_code != 200:
            print(f"[ORCHESTRATOR] ERROR: Detection API failed")
            raise HTTPException(status_code=detection_response.status_code,
                              detail=f"Detection API failed: {detection_response.text}")
        
        detection_data = detection_response.json()
        print(f"[ORCHESTRATOR] Detection API Success")
        print(f"[ORCHESTRATOR]   - Total detections: {detection_data.get('total_detections_count')}")
        print(f"[ORCHESTRATOR]   - ROI detections: {detection_data.get('roi_detections_count')}")
        print(f"[ORCHESTRATOR]   - Processing time: {detection_data.get('processing_time_ms')}ms")
        print("")
        
        # STEP 3: Evaluate Usecases
        print(f"[ORCHESTRATOR] STEP 3/4: Calling Usecase API")
        print(f"[ORCHESTRATOR] Endpoint: POST {base_url}/usecase/evaluate")
        
        usecase_payload = {
            "camera_id": request.camera_id,
            "detection_output": detection_data,
            "usecases": usecases
        }
        print(f"[ORCHESTRATOR] Evaluating {len(usecases)} usecases")
        
        usecase_response = requests.post(
            f"{base_url}/usecase/evaluate",
            json=usecase_payload,
            timeout=timeout
        )
        print(f"[ORCHESTRATOR] Usecase API Response: {usecase_response.status_code}")
        
        if usecase_response.status_code != 200:
            print(f"[ORCHESTRATOR] ERROR: Usecase API failed")
            raise HTTPException(status_code=usecase_response.status_code,
                              detail=f"Usecase API failed: {usecase_response.text}")
        
        usecase_data = usecase_response.json()
        print(f"[ORCHESTRATOR] Usecase API Success")
        print(f"[ORCHESTRATOR]   - Results count: {len(usecase_data.get('results', []))}")
        
        triggered_usecases = [r for r in usecase_data.get('results', []) if r.get('triggered')]
        print(f"[ORCHESTRATOR]   - Triggered usecases: {len(triggered_usecases)}/{len(usecase_data.get('results', []))}")
        
        for result in usecase_data.get('results', []):
            status = "✓ TRIGGERED" if result.get('triggered') else "✗ Not triggered"
            print(f"[ORCHESTRATOR]     {result.get('usecase_id')}: {status}")
        print("")
        
        # STEP 4: Send Alerts
        print(f"[ORCHESTRATOR] STEP 4/4: Calling Alert API")
        print(f"[ORCHESTRATOR] Endpoint: POST {base_url}/alert/send")
        
        alert_payload = {
            "camera_id": request.camera_id,
            "usecase_results": usecase_data.get('results', [])
        }
        print(f"[ORCHESTRATOR] Processing alerts for {len(triggered_usecases)} triggered usecases")
        
        alert_response = requests.post(
            f"{base_url}/alert/send",
            json=alert_payload,
            timeout=timeout
        )
        print(f"[ORCHESTRATOR] Alert API Response: {alert_response.status_code}")
        
        if alert_response.status_code != 200:
            print(f"[ORCHESTRATOR] WARNING: Alert API failed (non-critical)")
            print(f"[ORCHESTRATOR] Alert error: {alert_response.text}")
            alert_data = {"alerts_sent": [], "status": "failed"}
        else:
            alert_data = alert_response.json()
            print(f"[ORCHESTRATOR] Alert API Success")
            print(f"[ORCHESTRATOR]   - Alerts sent: {len(alert_data.get('alerts_sent', []))}")
        
        print("")
        print("="*80)
        print("[ORCHESTRATOR] PIPELINE EXECUTION COMPLETED")
        print("="*80 + "\n")
        
        # Return combined results
        return {
            "status": "success",
            "camera_id": request.camera_id,
            "pipeline_results": {
                "camera": {
                    "status": camera_data.get('status'),
                    "backend": camera_data.get('backend')
                },
                "detection": {
                    "total_detections": detection_data.get('total_detections_count'),
                    "roi_detections": detection_data.get('roi_detections_count'),
                    "processing_time_ms": detection_data.get('processing_time_ms')
                },
                "usecases": {
                    "evaluated": len(usecase_data.get('results', [])),
                    "triggered": len(triggered_usecases),
                    "results": usecase_data.get('results', [])
                },
                "alerts": {
                    "sent": len(alert_data.get('alerts_sent', [])),
                    "details": alert_data.get('alerts_sent', [])
                }
            }
        }
        
    except requests.exceptions.ConnectionError as e:
        print(f"[ORCHESTRATOR] ERROR: Connection failed - {str(e)}")
        raise HTTPException(status_code=503, detail=f"Service connection failed: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ORCHESTRATOR] ERROR: Pipeline execution failed - {str(e)}")
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")


class EdgePipelineRequest(BaseModel):
    """Request schema for edge-based pipeline execution"""
    camera_id: str = Field(..., description="Camera identifier")
    detection_output: dict = Field(..., description="Detection output from edge device (already transformed)")


@app.post("/pipeline/execute-edge", tags=["pipeline"])
def execute_edge_pipeline(request: EdgePipelineRequest):
    """
    Orchestrate EDGE-BASED pipeline: Usecase → Alert → Analytics
    
    ⚠️ MODE: Edge (camera + detection run on edge device)
    Edge device sends detection results to /edge/ingest, then calls this endpoint.
    
    This orchestrator:
    - Skips camera API (edge device handles capture)
    - Skips detection API (edge device handles inference)
    - Starts from usecase API
    - Chains: Usecase → Alert → Analytics
    
    **Request Body:**
    - **camera_id**: Camera identifier (required)
    - **detection_output**: Detection output from edge/ingest (transformed format)
    
    **Example:**
    ```json
    {
      "camera_id": "edge_cam_1",
      "detection_output": {
        "camera_id": "edge_cam_1",
        "timestamp": "2026-02-27T10:00:00",
        "frame_id": 123,
        "detections": [...]
      }
    }
    ```
    """
    print("\n" + "="*80)
    print("[ORCHESTRATOR] EDGE PIPELINE EXECUTION STARTED")
    print("="*80)
    print(f"[ORCHESTRATOR] Mode: EDGE (camera + detection on edge device)")
    print(f"[ORCHESTRATOR] Camera ID: {request.camera_id}")
    print(f"[ORCHESTRATOR] Detection count: {len(request.detection_output.get('detections', []))}")
    print("="*80 + "\n")
    
    import requests
    from common.config import API_BASE_URL
    base_url = API_BASE_URL
    timeout = 30
    
    try:
        # STEP 1: Evaluate Usecases (SKIP camera + detection - edge device handled it)
        print(f"[ORCHESTRATOR] STEP 1/3: Calling Usecase API")
        print(f"[ORCHESTRATOR] Endpoint: POST {base_url}/usecase/evaluate")
        print(f"[ORCHESTRATOR] ℹ️  Camera and Detection APIs BYPASSED (edge mode)")
        
        usecase_payload = {
            "camera_id": request.camera_id,
            "detection_output": request.detection_output
        }
        
        usecase_response = requests.post(
            f"{base_url}/usecase/evaluate",
            json=usecase_payload,
            timeout=timeout
        )
        print(f"[ORCHESTRATOR] Usecase API Response: {usecase_response.status_code}")
        
        if usecase_response.status_code != 200:
            print(f"[ORCHESTRATOR] ERROR: Usecase API failed")
            raise HTTPException(status_code=usecase_response.status_code,
                              detail=f"Usecase API failed: {usecase_response.text}")
        
        usecase_data = usecase_response.json()
        print(f"[ORCHESTRATOR] Usecase API Success")
        print(f"[ORCHESTRATOR]   - Results count: {len(usecase_data.get('results', []))}")
        
        triggered_usecases = [r for r in usecase_data.get('results', []) if r.get('triggered')]
        print(f"[ORCHESTRATOR]   - Triggered usecases: {len(triggered_usecases)}/{len(usecase_data.get('results', []))}")
        
        for result in usecase_data.get('results', []):
            status = "✓ TRIGGERED" if result.get('triggered') else "✗ Not triggered"
            print(f"[ORCHESTRATOR]     {result.get('usecase_id')}: {status}")
        print("")
        
        # STEP 2: Send Alerts
        print(f"[ORCHESTRATOR] STEP 2/3: Calling Alert API")
        print(f"[ORCHESTRATOR] Endpoint: POST {base_url}/alert/send")
        
        alert_payload = {
            "camera_id": request.camera_id,
            "usecase_results": usecase_data.get('results', [])
        }
        print(f"[ORCHESTRATOR] Processing alerts for {len(triggered_usecases)} triggered usecases")
        
        alert_response = requests.post(
            f"{base_url}/alert/send",
            json=alert_payload,
            timeout=timeout
        )
        print(f"[ORCHESTRATOR] Alert API Response: {alert_response.status_code}")
        
        if alert_response.status_code != 200:
            print(f"[ORCHESTRATOR] WARNING: Alert API failed (non-critical)")
            print(f"[ORCHESTRATOR] Alert error: {alert_response.text}")
            alert_data = {"alerts_sent": [], "status": "failed"}
        else:
            alert_data = alert_response.json()
            print(f"[ORCHESTRATOR] Alert API Success")
            print(f"[ORCHESTRATOR]   - Alerts sent: {alert_data.get('total_alerts_sent', 0)}")
        
        # STEP 3: Analytics (future enhancement)
        print(f"[ORCHESTRATOR] STEP 3/3: Analytics")
        print(f"[ORCHESTRATOR] ℹ️  Analytics aggregation runs via scheduler")
        print(f"[ORCHESTRATOR] ℹ️  Usecase results already persisted to DB")
        
        print("")
        print("="*80)
        print("[ORCHESTRATOR] EDGE PIPELINE EXECUTION COMPLETED")
        print("="*80 + "\n")
        
        # Return combined results
        return {
            "status": "success",
            "mode": "edge",
            "camera_id": request.camera_id,
            "pipeline_results": {
                "camera": {
                    "status": "bypassed_edge_mode",
                    "note": "Camera capture handled by edge device"
                },
                "detection": {
                    "status": "bypassed_edge_mode",
                    "note": "Inference handled by edge device",
                    "detections_count": len(request.detection_output.get('detections', []))
                },
                "usecases": {
                    "evaluated": len(usecase_data.get('results', [])),
                    "triggered": len(triggered_usecases),
                    "results": usecase_data.get('results', [])
                },
                "alerts": {
                    "sent": alert_data.get('total_alerts_sent', 0),
                    "details": alert_data.get('alerts_sent', [])
                },
                "analytics": {
                    "status": "persisted",
                    "note": "Aggregation runs via scheduler"
                }
            }
        }
        
    except requests.exceptions.ConnectionError as e:
        print(f"[ORCHESTRATOR] ERROR: Connection failed - {str(e)}")
        raise HTTPException(status_code=503, detail=f"Service connection failed: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ORCHESTRATOR] ERROR: Edge pipeline execution failed - {str(e)}")
        raise HTTPException(status_code=500, detail=f"Edge pipeline execution failed: {str(e)}")


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """API Root - Welcome and Quick Links"""
    result = {
        "message": "Camera Management API with DeepStream",
        "version": "2.0.0",
        "status": "operational",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        },
        "endpoints": {
            "health": "/camera/health",
            "list_cameras": "/camera/list",
            "start_single": "/camera/start",
            "start_multi": "/camera/start-multi (recommended for 100+ cameras)"
        },
        "support": {
            "single_camera_mode": "< 10 cameras",
            "multi_stream_mode": "100+ cameras (GPU batched processing)",
            "hardware": "NVIDIA GPU with DeepStream"
        }
    }
    logger.info("✓ root endpoint completed")
    return result


@app.get("/info", tags=["root"])
async def api_info():
    """Get API and system information"""
    import platform
    from camera.service import camera_manager
    
    camera_list = camera_manager.list_cameras()
    
    info = {
        "api": {
            "name": "Camera Management API",
            "version": "2.0.0",
            "backend": "DeepStream + FastAPI"
        },
        "system": {
            "platform": platform.platform(),
            "python": platform.python_version()
        },
        "cameras": {
            "active": camera_list['total_count'],
            "mode": camera_list['mode'],
            "single_stream": len(camera_list['single_stream_cameras']),
            "multi_stream": len(camera_list['multi_stream_cameras'])
        },
        "capabilities": {
            "max_single_cameras": 10,
            "max_multi_cameras": "100+",
            "hardware_acceleration": "NVIDIA DeepStream",
            "roi_support": True,
            "real_time_processing": True
        }
    }
    
    # Add GStreamer version if available
    try:
        import gi
        gi.require_version('Gst', '1.0')
        from gi.repository import Gst
        info["gstreamer"] = {
            "version": Gst.version_string(),
            "available": True
        }
    except:
        info["gstreamer"] = {
            "available": False
        }
    
    logger.info("✓ api_info endpoint completed")
    return info


# Main entry point
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
        access_log=True
    )