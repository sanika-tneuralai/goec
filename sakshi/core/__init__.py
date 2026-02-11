# Initialize GStreamer and add DeepStream to path
import sys
import os

# Add DeepStream Python bindings to path (version 6.4)
deepstream_path = '/opt/nvidia/deepstream/deepstream-6.4/lib'
if deepstream_path not in sys.path:
    sys.path.insert(0, deepstream_path)

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
Gst.init(None)