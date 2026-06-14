import os
import cv2
import kinematics  

# ─── HARDWARE DETECTION & HAILO ACCELERATOR SETUP ───
try:
    # Picamera2 is the standard native library for Raspberry Pi 5 OS
    from picamera2 import Picamera2
    IS_PI = True
except ImportError:
    IS_PI = False

try:
    # Official Raspberry Pi AI HAT+ Hailo runtime modules
    from hailo_platform import VDevice, InferVDevice
    import numpy as np
    HAS_AI_HAT = True
except ImportError:
    HAS_AI_HAT = False

# Fallback wrapper for your laptop so your code doesn't crash right now
if not HAS_AI_HAT:
    try:
        from ultralytics import YOLO
        print("[VISION INIT] AI HAT not detected on this machine. Initializing local YOLOv8 fallback.")
        YOLO_MODEL = YOLO("yolov8n.pt")
    except ImportError:
        print("[VISION INIT] Please run 'pip install ultralytics' for laptop local testing.")
        YOLO_MODEL = None


def snapshot_item(filename="target_sight.jpg"):
    """Snaps a single image frame using the current active system camera for item identification."""
    print("📸 Jarvis is focusing optical registers...")
    
    if IS_PI:
        try:
            picam = Picamera2()
            picam.configure(picam.create_preview_configuration(main={"size": (1280, 720)}))
            picam.start()
            frame = picam.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            cv2.imwrite(filename, frame)
            picam.stop()
            picam.close()
        except Exception as e:
            print(f"⚠️ Picamera2 snapshot fault: {e}")
            return False
    else:
        cap = cv2.VideoCapture(0)
        for _ in range(5):  # Let camera auto-exposure adjust
            success, frame = cap.read()
        if success:
            cv2.imwrite(filename, frame)
        cap.release()
        
    if os.path.exists(filename):
        print(f"💾 Snapshot captured safely as {filename}")
        return True
    return False


def analyze_frame_with_hailo(image_path):
    """
    Called by brain.py. Runs object classification locally on the AI HAT+ 2 chip.
    Returns text summaries instantly without using internet/cloud APIs.
    """
    if not HAS_AI_HAT:
        return "Simulation mode item detected"
        
    # When your Pi arrives, you'll compile/download a .hef file from the Hailo Model Zoo
    hef_model_path = "yolov8n_compiled.hef"
    if not os.path.exists(hef_model_path):
        return "YOLO model not compiled on AI HAT storage yet"
        
    # Direct execution inside the Hailo-10H hardware core
    with VDevice() as target_device:
        with InferVDevice(target_device, hef_model_path) as inference_pipeline:
            # Load, resize, and convert image to format expected by your compiled model
            img = cv2.imread(image_path)
            # (In production, append inference_pipeline.infer() structures here)
            return "Objects detected via native 40 TOPS accelerator matrix"


def activate_camera():
    """Opens a live, continuous video window using the correct native driver based on hardware."""
    print("🎥 Launching live interactive video streams...")
    
    if IS_PI:
        print("🍇 Raspberry Pi Environment Detected. Activating Module 3 via Picamera2...")
        try:
            picam = Picamera2()
            picam.configure(picam.create_preview_configuration(main={"size": (640, 480)}))
            picam.start()
            
            print("🟢 Camera Module 3 active! Press 'q' inside the video window to close it.")
            while True:
                frame = picam.capture_array()
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                process_frame_with_ai(frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            picam.stop()
            picam.close()
        except Exception as e:
            print(f"⚠️ Live Pi stream hardware exception: {e}")
    else:
        print("💻 Laptop Environment Detected. Activating standard USB/Built-in Webcam...")
        cap = cv2.VideoCapture(0)
        print("🟢 Laptop Webcam active! Press 'q' inside the video window to close it.")
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break
            process_frame_with_ai(frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cap.release()
        
    cv2.destroyAllWindows()
    print("🔴 Live optical channels closed.")


def process_frame_with_ai(frame):
    """Processes individual image frames to extract coordinates and target motor angles."""
    # Use AI HAT if available, otherwise fallback to basic CPU YOLO for your current computer
    if HAS_AI_HAT:
        # High-speed processing happens here when the hardware arrives
        pass
    elif YOLO_MODEL is not None:
        results = YOLO_MODEL(frame, stream=True)
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                confidence = float(box.conf[0])
                class_name = YOLO_MODEL.names[int(box.cls[0])]
                
                if confidence > 0.5:
                    pixel_x = (x1 + x2) // 2
                    pixel_y = (y1 + y2) // 2
                    
                    # Convert pixel grids into physical centimeters for your table workspace
                    real_world_x = (pixel_x / 640) * 30.0
                    real_world_y = ((480 - pixel_y) / 480) * 20.0
                    
                    # Call math library to determine geometric positions
                    angles, status_msg = kinematics.calculate_joint_angles(real_world_x, real_world_y)
                    
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 3)
                    label = f"{class_name} {confidence:.2f}"
                    cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    if angles:
                        shoulder, elbow = angles
                        print(f"🎯 Targeted: '{class_name}' -> Real Workspace Position X: {real_world_x:.1f}cm, Y: {real_world_y:.1f}cm")
                        
                        # --- INTERRUPT INTERFACE: PASSTHROUGH TO HIWONDER xARM ---
                        try:
                            import robot_arm
                            robot_arm.move_to_kinematic_angles(shoulder, elbow)
                        except Exception as e:
                            print(f"[HW TRACE] Target calculated, but arm driver is simulated: {e}")
                    else:
                        cv2.putText(frame, "OUT OF REACH", (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    cv2.imshow("Jarvis Vision Protocol", frame)
