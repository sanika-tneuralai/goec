# Live People Count Dashboard

A minimal real-time dashboard to monitor people count across all cameras.

## Features

- 🎥 Live people count per camera
- ⚡ Auto-refreshes every 3 seconds
- 📊 Clean, responsive card-based UI
- 🚀 No dependencies - pure HTML + JavaScript

## Quick Start

1. **Start the backend server** (if not already running):
   ```bash
   cd ../backend
   python3 main.py
   ```

2. **Open the dashboard**:
   - Simply open `dashboard.html` in your browser
   - Or use a local server:
     ```bash
     python3 -m http.server 8080
     ```
     Then visit: http://localhost:8080/dashboard.html

## API Endpoint

The dashboard polls:
```
GET http://localhost:8000/analytics/live/people-count
```

Response format:
```json
{
  "timestamp": "2026-02-28T10:30:00.123456",
  "cameras": [
    { "camera_id": "cam_01", "people_count": 3 },
    { "camera_id": "cam_02", "people_count": 0 }
  ]
}
```

## Configuration

Edit `dashboard.html` to change:
- `API_ENDPOINT`: Backend URL (default: `http://localhost:8000`)
- `POLL_INTERVAL`: Refresh rate in milliseconds (default: 3000)

## Requirements

- Backend must be running on port 8000
- CORS must be enabled for cross-origin requests (already configured in backend)
- Browser with JavaScript enabled

## Notes

- Dashboard pauses updates when browser tab is hidden (saves resources)
- Handles connection errors gracefully
- Shows "No Camera Data" if no cameras are active
- Works independently from alert system - displays informational `people_count` usecase data
