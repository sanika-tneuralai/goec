"""
Central configuration management for the entire application.
"""
import os
from pathlib import Path


# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"

# Camera settings
DEFAULT_FPS = 5
MAX_FPS = 30
MIN_FPS = 1
MAX_CAMERAS_SINGLE_MODE = 50
DEFAULT_CAMERA_TIMEOUT = 30  # seconds

# Detection settings
DEFAULT_CONFIDENCE_THRESHOLD = 0.5
DEFAULT_IOU_THRESHOLD = 0.45
YOLO_MODEL_PATH = str(MODELS_DIR / "yolo11n.pt")

# Device settings
USE_GPU = True  # Auto-detect GPU, fallback to CPU

# API settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_RELOAD = os.getenv("API_RELOAD", "false").lower() == "true"

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = "camera_api.log"

# ROI settings
ROI_COLOR = (0, 255, 255)  # Yellow in BGR
ROI_THICKNESS = 2
ROI_FILL_ALPHA = 0.3

# Frame processing
MAX_FRAME_WIDTH = 1920
MAX_FRAME_HEIGHT = 1080
JPEG_QUALITY = 85

# Multi-stream settings (DeepStream)
MULTI_STREAM_BATCH_SIZE = 4
MULTI_STREAM_WIDTH = 1280
MULTI_STREAM_HEIGHT = 720

print("✓ config module loaded")
