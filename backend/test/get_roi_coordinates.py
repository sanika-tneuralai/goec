import cv2
import subprocess
import os
import json
import numpy as np

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
RTSP_URL = "rtsp://admin:admin@132.154.208.136:570/cam/realmonitor?channel=3&subtype=0"
SNAPSHOT_PATH = "roi_snapshot.jpg"
ROI_OUTPUT_PATH = "roi_coordinates.json"

# ─────────────────────────────────────────────
#  GLOBALS for drawing
# ─────────────────────────────────────────────
drawing = False
roi_points = []
temp_point = None
img_display = None
img_original = None
roi_complete = False


def capture_snapshot(rtsp_url, output_path):
    """Capture a single frame from the RTSP stream using ffmpeg."""
    print("[*] Capturing frame from camera...")
    subprocess.run(["pkill", "-9", "ffmpeg"], capture_output=True)

    cmd = [
        "ffmpeg", "-y",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-frames:v", "1",
        "-q:v", "2",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

    if os.path.exists(output_path):
        print(f"[✓] Frame captured → {output_path}")
        return True
    else:
        print("[✗] Failed to capture frame.")
        print(result.stderr[-300:])
        return False


def draw_roi_on_image():
    """Draw current ROI points and lines on a fresh copy of the image."""
    global img_display, img_original, roi_points, temp_point, roi_complete

    img_display = img_original.copy()
    n = len(roi_points)

    # Draw filled polygon if complete
    if roi_complete and n >= 3:
        overlay = img_display.copy()
        pts = np.array(roi_points, dtype=np.int32)
        cv2.fillPoly(overlay, [pts], (0, 255, 100))
        cv2.addWeighted(overlay, 0.25, img_display, 0.75, 0, img_display)
        cv2.polylines(img_display, [pts], isClosed=True,
                      color=(0, 255, 100), thickness=2)

    # Draw lines between points
    for i in range(n - 1):
        cv2.line(img_display, roi_points[i], roi_points[i + 1],
                 (0, 200, 255), 2)

    # Draw live line from last point to current mouse
    if n > 0 and temp_point and not roi_complete:
        cv2.line(img_display, roi_points[-1], temp_point,
                 (100, 100, 255), 1, cv2.LINE_AA)
        if n >= 2:
            cv2.line(img_display, roi_points[0], temp_point,
                     (100, 100, 255), 1, cv2.LINE_AA)

    # Close polygon preview line
    if n >= 2 and not roi_complete and temp_point:
        pass  # Already drawn above

    # Draw points
    for i, pt in enumerate(roi_points):
        color = (0, 255, 255) if i == 0 else (0, 200, 255)
        cv2.circle(img_display, pt, 6, color, -1)
        cv2.circle(img_display, pt, 6, (255, 255, 255), 1)
        cv2.putText(img_display, str(i + 1), (pt[0] + 8, pt[1] - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # HUD
    draw_hud()


def draw_hud():
    """Overlay instructions and coordinates on the image."""
    global img_display, roi_points, roi_complete

    h, w = img_display.shape[:2]

    # Semi-transparent top bar
    overlay = img_display.copy()
    cv2.rectangle(overlay, (0, 0), (w, 36), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.7, img_display, 0.3, 0, img_display)

    if roi_complete:
        msg = "ROI Complete!  [S] Save & Print  [R] Reset  [Q] Quit"
        color = (0, 255, 100)
    elif len(roi_points) == 0:
        msg = "Left-click to add points  |  Right-click to undo  |  Double-click to close ROI  |  [Q] Quit"
        color = (0, 220, 255)
    else:
        msg = f"Points: {len(roi_points)}  |  Double-click or click near start to close  |  Right-click to undo  |  [Q] Quit"
        color = (0, 220, 255)

    cv2.putText(img_display, msg, (10, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, color, 1, cv2.LINE_AA)

    # Coordinate list bottom panel
    if roi_points:
        panel_h = min(len(roi_points) * 22 + 14, 200)
        panel_y = h - panel_h - 5
        overlay2 = img_display.copy()
        cv2.rectangle(overlay2, (5, panel_y), (220, h - 5), (20, 20, 20), -1)
        cv2.addWeighted(overlay2, 0.65, img_display, 0.35, 0, img_display)

        cv2.putText(img_display, "ROI Points:", (12, panel_y + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180, 180, 180), 1)
        for i, pt in enumerate(roi_points[-8:]):  # show max 8
            txt = f"  P{i+1}: ({pt[0]}, {pt[1]})"
            cv2.putText(img_display, txt, (12, panel_y + 16 + (i + 1) * 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 255, 200), 1)


def mouse_callback(event, x, y, flags, param):
    global roi_points, temp_point, roi_complete, drawing

    if roi_complete:
        return

    # Track mouse position for live preview
    temp_point = (x, y)

    if event == cv2.EVENT_LBUTTONDBLCLK:
        # Double-click closes the polygon
        if len(roi_points) >= 3:
            roi_complete = True
            print("\n[✓] ROI closed!")
            print_coordinates()

    elif event == cv2.EVENT_LBUTTONDOWN:
        # Check if clicking near the first point to close
        if len(roi_points) >= 3:
            fx, fy = roi_points[0]
            dist = ((x - fx) ** 2 + (y - fy) ** 2) ** 0.5
            if dist < 15:
                roi_complete = True
                print("\n[✓] ROI closed by clicking start point!")
                print_coordinates()
                return

        roi_points.append((x, y))
        print(f"  + Point {len(roi_points)}: ({x}, {y})")

    elif event == cv2.EVENT_RBUTTONDOWN:
        # Right-click to undo last point
        if roi_points:
            removed = roi_points.pop()
            print(f"  - Removed point: {removed}")

    elif event == cv2.EVENT_MOUSEMOVE:
        pass  # temp_point already updated

    draw_roi_on_image()
    cv2.imshow("ROI Selector", img_display)


def print_coordinates():
    """Print the ROI coordinates in multiple formats."""
    print("\n" + "=" * 50)
    print("  ROI COORDINATES")
    print("=" * 50)

    print("\n[List of tuples]")
    print(f"  roi = {roi_points}")

    print("\n[Numbered points]")
    for i, pt in enumerate(roi_points):
        print(f"  Point {i+1}: x={pt[0]}, y={pt[1]}")

    print("\n[NumPy array format]")
    print(f"  np.array({roi_points})")

    # Bounding box
    xs = [p[0] for p in roi_points]
    ys = [p[1] for p in roi_points]
    print("\n[Bounding Box]")
    print(f"  x_min={min(xs)}, y_min={min(ys)}, x_max={max(xs)}, y_max={max(ys)}")
    print(f"  width={max(xs)-min(xs)}, height={max(ys)-min(ys)}")
    print("=" * 50)


def save_coordinates():
    """Save coordinates to JSON."""
    xs = [p[0] for p in roi_points]
    ys = [p[1] for p in roi_points]

    data = {
        "roi_points": roi_points,
        "bounding_box": {
            "x_min": min(xs), "y_min": min(ys),
            "x_max": max(xs), "y_max": max(ys),
            "width": max(xs) - min(xs),
            "height": max(ys) - min(ys)
        },
        "num_points": len(roi_points)
    }

    with open(ROI_OUTPUT_PATH, "w") as f:
        json.dump(data, f, indent=2)

    # Save annotated image
    annotated_path = "roi_annotated.jpg"
    cv2.imwrite(annotated_path, img_display)

    print(f"\n[✓] Coordinates saved → {ROI_OUTPUT_PATH}")
    print(f"[✓] Annotated image saved → {annotated_path}")


def main():
    global img_display, img_original

    # Step 1: Capture frame
    if not os.path.exists(SNAPSHOT_PATH):
        if not capture_snapshot(RTSP_URL, SNAPSHOT_PATH):
            print("[!] Using blank canvas as fallback (1920x1080)")
            img_original = np.zeros((1080, 1920, 3), dtype=np.uint8)
        else:
            img_original = cv2.imread(SNAPSHOT_PATH)
    else:
        print(f"[*] Using existing snapshot: {SNAPSHOT_PATH}")
        img_original = cv2.imread(SNAPSHOT_PATH)

    if img_original is None:
        print("[✗] Could not load image!")
        return

    h, w = img_original.shape[:2]
    print(f"[*] Image size: {w}x{h}")
    print("\n[Controls]")
    print("  Left-click       → Add point")
    print("  Right-click      → Undo last point")
    print("  Double-click     → Close ROI")
    print("  Click near P1    → Close ROI")
    print("  S                → Save coordinates")
    print("  R                → Reset / redraw")
    print("  Q / ESC          → Quit\n")

    # Resize for display if too large
    scale = 1.0
    max_display_w = 1280
    if w > max_display_w:
        scale = max_display_w / w
        display_h = int(h * scale)
        img_original = cv2.resize(img_original, (max_display_w, display_h))
        print(f"[*] Resized for display: {max_display_w}x{display_h} (scale={scale:.2f})")
        print(f"    Note: Coordinates are in display resolution.")

    img_display = img_original.copy()

    cv2.namedWindow("ROI Selector", cv2.WINDOW_NORMAL)
    cv2.setMouseCallback("ROI Selector", mouse_callback)

    draw_roi_on_image()
    cv2.imshow("ROI Selector", img_display)

    while True:
        key = cv2.waitKey(20) & 0xFF

        if key == ord('q') or key == 27:  # Q or ESC
            print("\n[*] Exiting...")
            break

        elif key == ord('s'):  # Save
            if roi_points:
                save_coordinates()
                print_coordinates()
            else:
                print("[!] No points to save yet.")

        elif key == ord('r'):  # Reset
            roi_points.clear()
            globals()['roi_complete'] = False
            globals()['temp_point'] = None
            print("[*] ROI reset.")
            draw_roi_on_image()
            cv2.imshow("ROI Selector", img_display)

    cv2.destroyAllWindows()

    # Final print on exit
    if roi_points:
        print_coordinates()
        save_coordinates()


if __name__ == "__main__":
    main()