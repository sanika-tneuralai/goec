#!/bin/bash

# Quick Test Commands for Camera Management API
# ============================================

echo "🔍 Testing Camera Management API"
echo ""

# 1. Health Check
echo "1️⃣  Health Check:"
curl -s http://localhost:8000/camera/health | jq
echo ""

# 2. Test with public RTSP stream
echo "2️⃣  Starting test camera with public stream:"
curl -X POST http://localhost:8000/camera/start \
  -H "Content-Type: application/json" \
  -d '{
    "rtsp_url": "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4",
    "camera_id": "test_camera",
    "fps": 5,
    "roi_points": [[100, 100], [300, 100], [300, 300], [100, 300]]
  }' | jq
echo ""

# 3. Wait for frames
echo "3️⃣  Waiting 5 seconds for frame capture..."
sleep 5
echo ""

# 4. Check status
echo "4️⃣  Camera Status:"
curl -s http://localhost:8000/camera/status/test_camera | jq
echo ""

# 5. Get frame
echo "5️⃣  Downloading frame..."
curl -s http://localhost:8000/camera/frame/test_camera | jq -r '.frame' | base64 -d > test_frame.jpg

if [ -f test_frame.jpg ]; then
    file_size=$(stat -f%z test_frame.jpg 2>/dev/null || stat -c%s test_frame.jpg 2>/dev/null)
    echo "✅ Frame saved: test_frame.jpg (${file_size} bytes)"
    echo "   Open with: xdg-open test_frame.jpg"
else
    echo "❌ Failed to save frame"
fi
echo ""

# 6. Stop camera
echo "6️⃣  Stopping test camera:"
curl -X POST http://localhost:8000/camera/stop/test_camera | jq
echo ""

echo "✅ Test complete!"
echo ""
echo "📝 Notes:"
echo "   - If frame_count = 0, check RTSP connectivity"
echo "   - Your camera IP (132.154.208.136) is currently unreachable"
echo "   - See TESTING.md for detailed troubleshooting"
