import os
import cv2

try:
    from picamera import PiCamera
    IS_PI = True
except ImportError:
    IS_PI = False

def snapshot_item(filename="target_sight.jpg"):
    """Snaps a single image frame using the current active system camera."""
    print("📸 Jarvis is focusing optical registers...")
    
    if IS_PI:
        from picamera2 import Picamera2
        picam = Picamera2()
        picam.configure(picam.create_preview_configuration(main={"size": (1280, 720)}))
        picam.start()
        # Capture raw multi-megapixel sensor array matrix frame
        frame = picam.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imwrite(filename, frame)
        picam.stop()
        picam.close()
    else:
        cap = cv2.VideoCapture(0)
        # Flush buffer to ensure clear focus
        for _ in range(5):
            success, frame = cap.read()
        if success:
            cv2.imwrite(filename, frame)
        cap.release()
        
    if os.path.exists(filename):
        print(f"💾 Snapshot captured safely as {filename}")
        return True
    return False
