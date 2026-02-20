"""
Common utilities and configuration across all modules.
"""

from common.utils import (
    validate_rtsp_url,
    create_roi_mask,
    apply_roi_to_frame,
    draw_roi_on_frame,
    resize_frame,
    preprocess_frame_for_detection
)

__all__ = [
    "validate_rtsp_url",
    "create_roi_mask",
    "apply_roi_to_frame",
    "draw_roi_on_frame",
    "resize_frame",
    "preprocess_frame_for_detection"
]
