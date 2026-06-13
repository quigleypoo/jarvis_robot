import os
import cv2
import kinematics  # Imports your custom trigonometric trajectory solver module

try:
    from picamera import PiCamera
    IS_PI = True
except ImportError:
    # If the system library errors out, we are running on your Windows laptop!
    IS_PI = False

def snapshot_item(filename="target_sight.jpg"):
    """Snaps a single image frame using the current active system camera for item identification."""
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
        # Flush the hardware camera buffer lines to ensure clear focus
        for _ in range(5):
            success, frame = cap.read()
        if success:
            cv2.imwrite(filename, frame)
        cap.release()
        
    if os.path.exists(filename):
        print(f"💾 Snapshot captured safely as {filename}")
        return True
    return False

def activate_camera():
    """Opens a live, continuous video window using the correct native driver based on hardware."""
    print("🎥 Launching live interactive video streams...")
    
    # Load the ultra-lightweight local object detection AI model
    from ultralytics import YOLO
    model = YOLO("yolov8n.pt") 
    
    if IS_PI:
        print("🍇 Raspberry Pi Environment Detected. Activating Module 3 via Picamera2...")
        from picamera2 import Picamera2
        picam = Picamera2()
        picam.configure(picam.create_preview_configuration(main={"size": (640, 480)}))
        picam.start()
        
        print("🟢 Camera Module 3 active! Press 'q' inside the video window to close it.")
        while True:
            frame = picam.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            process_frame_with_yolo(frame, model)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        picam.stop()
        picam.close()
    else:
        print("💻 Laptop Environment Detected. Activating standard USB/Built-in Webcam...")
        cap = cv2.VideoCapture(0)
        print("🟢 Laptop Webcam active! Press 'q' inside the video window to close it.")
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break
            process_frame_with_yolo(frame, model)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cap.release()
        
    cv2.destroyAllWindows()
    print("🔴 Live optical channels closed.")

def process_frame_with_yolo(frame, model):
    """Processes individual image frames to extract coordinates and target motor angles."""
    results = model(frame, stream=True)
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy)
            confidence = float(box.conf)
            class_name = model.names[int(box.cls)]
            
            if confidence > 0.5:
                # Calculate the center pixel location of the object on the screen window matrix
                pixel_x = (x1 + x2) // 2
                pixel_y = (y1 + y2) // 2
                
                # --- PIXEL TO PHYSICAL SPACE MAPPING ---
                # Standard camera frames are 640x480 pixels. 
                # We map pixel coordinate frames to represent a workspace 30cm wide and 20cm deep.
                real_world_x = (pixel_x / 640) * 30.0
                real_world_y = ((480 - pixel_y) / 480) * 20.0
                
                # Run the Inverse Kinematics math solver function to find joint targets
                angles, status_msg = kinematics.calculate_joint_angles(real_world_x, real_world_y)
                
                # Draw structural graphics bounding box highlights onto the image window canvas
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 3)
                label = f"{class_name} {confidence:.2f}"
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                if angles:
                    shoulder, elbow = angles
                    # Print out the exact physical instructions ready for the Arduino microcontroller
                    print(f"🎯 Targeted: '{class_name}' -> Real Workspace Position X: {real_world_x:.1f}cm, Y: {real_world_y:.1f}cm")
                    print(f"⚙️ TRANSMITTING TO ARDUINO -> [CMD:MOVE_{shoulder}_{elbow}]")
                else:
                    # If an item drifts too far to the edges or out of range, let the log know
                    cv2.putText(frame, "OUT OF REACH", (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    cv2.imshow("Jarvis Vision Protocol", frame)
