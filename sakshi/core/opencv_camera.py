import logging
import cv2
import numpy as np
import asyncio
from datetime import datetime
from typing import Optional, List
from threading import Thread, Lock

logger = logging.getLogger(__name__)


class OpenCVCamera:
    """OpenCV-based RTSP camera handler (better compatibility than GStreamer for some cameras)"""
    
    def __init__(self, camera_id: str, rtsp_url: str, fps: int = 5, roi_points: Optional[List] = None):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.fps = fps
        self.roi_points = roi_points
        self.roi_mask = None
        
        # OpenCV capture object
        self.cap = None
        self.is_running = False
        self.thread = None
        
        # Frame management
        self.current_frame = None
        self.frame_count = 0
        self.last_frame_time = 0
        self.error_count = 0
        self.max_errors = 10
        self.frame_lock = Lock()
        
    def _create_roi_mask(self, frame_shape: tuple) -> Optional[np.ndarray]:
        """Create binary mask from polygon ROI points"""
        if not self.roi_points or len(self.roi_points) < 3:
            return None
        
        try:
            mask = np.zeros(frame_shape[:2], dtype=np.uint8)
            points = np.array(self.roi_points, dtype=np.int32)
            cv2.fillPoly(mask, [points], 255)
            logger.info(f"[{self.camera_id}] ROI mask created")
            return mask
        except Exception as e:
            logger.error(f"[{self.camera_id}] Failed to create ROI mask: {str(e)}")
            return None
    
    def _capture_loop(self):
        """Background thread for frame capture"""
        frame_interval = 1.0 / self.fps
        
        try:
            while self.is_running and self.error_count < self.max_errors:
                ret, frame = self.cap.read()
                
                if not ret:
                    self.error_count += 1
                    logger.warning(f"[{self.camera_id}] Failed to read frame (errors: {self.error_count}/{self.max_errors})")
                    asyncio.run(asyncio.sleep(0.5))
                    continue
                
                # Create ROI mask on first successful frame
                if self.roi_points and self.roi_mask is None:
                    self.roi_mask = self._create_roi_mask(frame.shape)
                
                # Update frame data
                with self.frame_lock:
                    self.current_frame = frame.copy()
                    self.frame_count += 1
                    self.last_frame_time = datetime.now().timestamp()
                    self.error_count = 0  # Reset error count on success
                
                # Rate limiting
                asyncio.run(asyncio.sleep(frame_interval))
                
        except Exception as e:
            logger.error(f"[{self.camera_id}] Error in capture loop: {str(e)}")
        finally:
            logger.info(f"[{self.camera_id}] Capture loop stopped")
    
    async def start(self) -> bool:
        """Start camera stream"""
        try:
            if self.is_running:
                logger.warning(f"[{self.camera_id}] Already running")
                return False
            
            logger.info(f"[{self.camera_id}] Opening RTSP stream: {self.rtsp_url}")
            
            # Open with OpenCV + FFmpeg backend
            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            
            # Configure for RTSP
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            if not self.cap.isOpened():
                raise Exception("Failed to open RTSP stream")
            
            # Test read
            ret, test_frame = self.cap.read()
            if not ret:
                raise Exception("Failed to read first frame from stream")
            
            logger.info(f"[{self.camera_id}] Stream opened successfully, frame shape: {test_frame.shape}")
            
            # Start capture thread
            self.is_running = True
            self.thread = Thread(target=self._capture_loop, daemon=True, name=f"Capture-{self.camera_id}")
            self.thread.start()
            
            logger.info(f"[{self.camera_id}] Started successfully")
            return True
            
        except Exception as e:
            logger.error(f"[{self.camera_id}] Failed to start: {str(e)}")
            if self.cap:
                self.cap.release()
            return False
    
    async def stop(self) -> bool:
        """Stop camera stream"""
        try:
            logger.info(f"[{self.camera_id}] Stopping...")
            
            self.is_running = False
            
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=2.0)
            
            if self.cap:
                self.cap.release()
            
            logger.info(f"[{self.camera_id}] Stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"[{self.camera_id}] Error stopping: {str(e)}")
            return False
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get current frame"""
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
        return None
    
    async def get_preprocessed_frame(self) -> Optional[dict]:
        """Get preprocessed frame data for API (async compatible)"""
        frame = self.get_frame()
        if frame is None:
            return None
        
        return {
            "frame": frame,
            "timestamp": self.last_frame_time,
            "shape": frame.shape,
            "roi_points": self.roi_points,
            "roi_mask": self.roi_mask,
            "frame_count": self.frame_count
        }
    
    def get_status(self) -> dict:
        """Get camera status"""
        return {
            "camera_id": self.camera_id,
            "is_running": self.is_running,
            "backend": "opencv-ffmpeg",
            "fps": self.fps,
            "frame_count": self.frame_count,
            "last_frame_time": self.last_frame_time,
            "rtsp_url": self.rtsp_url
        }
