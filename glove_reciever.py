import socket
import json
import time

try:
    import robot_arm
    HAS_ARM = True
except ImportError:
    HAS_ARM = False

# Define the network port to listen for wireless signals
UDP_IP = "0.0.0.0"  # listens to all incoming network interfaces
UDP_PORT = 5005

class GloveReceiver:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((UDP_IP, UDP_PORT))
        self.running = True

    def listen_loop(self):
        print(f"📡 Wireless tracking link active. Listening on port {UDP_PORT}...")
        print("Press 'Ctrl + C' in the terminal to terminate the stream.")
        
        while self.running:
            try:
                # Read incoming data pack from the Wi-Fi network buffer
                data, addr = self.sock.recvfrom(1024) 
                
                # Decode the incoming string back into a Python dictionary
                glove_data = json.loads(data.decode('utf-8'))
                
                # Example JSON structure sent by the glove: 
                # {"thumb": 500, "index": 620, "wrist_pitch": 450}
                index_finger = glove_data.get("index", 500)
                wrist_angle = glove_data.get("wrist_pitch", 500)
                
                if HAS_ARM:
                    # Map your index finger bending directly to the xArm Claw (Servo 6)
                    robot_arm._controller.move_servo(6, index_finger, duration=50)
                    # Map wrist tilt to the Wrist Joint (Servo 4)
                    robot_arm._controller.move_servo(4, wrist_angle, duration=50)
                else:
                    print(f"📡 [SIMULATOR WIRELESS DATA] Received from Glove: {glove_data}")
                    
            except Exception as e:
                print(f"⚠️ Data packet drop: {e}")
                time.sleep(0.01)

if __name__ == "__main__":
    receiver = GloveReceiver()
    try:
        receiver.listen_loop()
    except KeyboardInterrupt:
        print("\n🔴 Wireless receiver closed.")
