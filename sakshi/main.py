import sys
import os

# Add DeepStream path FIRST, before any other imports
deepstream_path = '/opt/nvidia/deepstream/deepstream-6.4/lib'
if deepstream_path not in sys.path:
    sys.path.insert(0, deepstream_path)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
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
    from api.camera_manager import camera_manager
    from core.utils import log_system_info
    
    # Startup
    logger.info("=" * 60)
    logger.info("Starting Camera Management API with DeepStream")
    logger.info("=" * 60)
    log_system_info()
    
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
    
    logger.info("API server shut down successfully")


# Create FastAPI application
app = FastAPI(
    title="Camera Management API with DeepStream",
    description="""
    ## High-Performance RTSP Camera Stream Management for Queue Monitoring
    
    ### Features:
    - **Single Camera Mode**: For < 10 cameras with independent processing
    - **Multi-Stream Mode**: For 100+ cameras with batched GPU processing
    - **Hardware Acceleration**: NVIDIA DeepStream for optimal performance
    - **ROI Support**: Define custom regions of interest for queue monitoring
    - **Real-time Processing**: Low-latency frame extraction and processing
    
    ### Modes:
    
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
    1. Start a single camera: `POST /camera/start`
    2. Check status: `GET /camera/status/{camera_id}`
    3. Get frame: `GET /camera/frame/{camera_id}`
    4. Stop camera: `DELETE /camera/stop/{camera_id}`
    
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


# Import and include router AFTER app creation
from api.camera_api import router as camera_router
app.include_router(camera_router)


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """API Root - Welcome and Quick Links"""
    return {
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


@app.get("/info", tags=["root"])
async def api_info():
    """Get API and system information"""
    import platform
    from api.camera_manager import camera_manager
    
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