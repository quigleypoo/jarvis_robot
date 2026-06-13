import os
import cv2
from ultralytics import YOLO

# 1. Check if we are running on a Raspberry Pi or a standard laptop
try:
    from picamera import PiCamera # Legacy or fallback check
    import PyQt5 # Picamera2 helper framework
    IS_PI = True
except ImportError:
    # If the libraries fail to import, we are on your Windows laptop!
    IS_PI = False

def activate_camera():
    """Opens the optics using the correct native driver based on your hardware platform."""
    print("🎥 Initializing Jarvis Optical Sensors...")
    model = YOLO("yolov8n.pt") 
    
    # ----------------------------------------------------
    # PATH A: CODE ENGINES FOR YOUR UPCOMING RASPBERRY PI 5
    # ----------------------------------------------------
    if IS_PI:
        print("🍇 Raspberry Pi Environment Detected. Activating Module 3 via Picamera2...")
        from picamera2 import Picamera2
        
        # Initialize the official Pi camera ribbon cable connection
        picam = Picamera2()
        
        # Configure the resolution to match what YOLO expects
        picam.configure(picam.create_preview_configuration(main={"size": (640, 480)}))
        picam.start()
        
        print("🟢 Camera Module 3 active! Press 'q' to close optical streams.")
        
        while True:
            # Grab a crisp 12-Megapixel sensor frame matrix directly from system memory
            frame = picam.capture_array()
            
            # The Pi sensor captures colors in RGB; OpenCV expects BGR formatting
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Pass the frame to our tracking algorithm
            process_frame_with_yolo(frame, model)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        picam.stop()
        picam.close()

    # ----------------------------------------------------
    # PATH B: SYSTEM CODE FOR YOUR LAPTOP WEBCOM SIMULATOR
    # ----------------------------------------------------
    else:
        print("💻 Laptop Environment Detected. Activating standard USB/Built-in Webcam...")
        cap = cv2.VideoCapture(0)
        
        print("🟢 Webcam active! Press 'q' on your keyboard to close the window.")
        
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                continue
                
            process_frame_with_yolo(frame, model)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        cap.release()
        
    cv2.destroyAllWindows()
    print("🔴 Optical sensors deactivated.")

def process_frame_with_yolo(frame, model):
    """Processes individual image frames to extract targeted structural shapes."""
    results = model(frame, stream=True)
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            confidence = float(box.conf[0])
            class_name = model.names[int(box.cls[0])]
            
            if confidence > 0.5:
                # Draw structural graphics overlays onto the image screen window
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 3)
                label = f"{class_name} {confidence:.2f}"
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # Spatial vectors meant to map the robot arm movements later
                print(f"🎯 Targeted Object: {class_name} coordinates -> X: {(x1+x2)//2}, Y: {(y1+y2)//2}")
                
    cv2.imshow("Jarvis Vision Protocol", frame)
