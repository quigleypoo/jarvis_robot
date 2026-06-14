import time

try:
    import xarm  # Hiwonder Serial Bus Servo Controller Library
    HAS_ARM = True
except ImportError:
    HAS_ARM = False

class ArmController:
    def __init__(self):
        self.arm = None
        if HAS_ARM:
            try:
                # Connected via physical USB cable to the Raspberry Pi 5
                self.arm = xarm.Controller('USB')
                print("[HARDWARE] Connected to Hiwonder xArm 1S Controller.")
            except Exception as e:
                print(f"[HW WARN] Failed to open xArm USB serial connection: {e}")

    def move_servo(self, servo_id, position, duration=600):
        """Moves an individual servo (1-6) to a target position (0-1000)."""
        if self.arm:
            self.arm.setPosition(servo_id, position, wait=True, duration=duration)
        else:
            print(f"[SIMULATOR] Arm Servo {servo_id} moving to digital step {position}")
            time.sleep(duration / 1000.0)

# Instantiate a global instance for brain.py and vision.py to tap into
_controller = ArmController()

def execute_movement(command_text):
    """Processes spoken intent strings passed down from brain.py."""
    if "wave" in command_text:
        # Servo 6 is the gripper claw, Servo 3 is the upper elbow joint
        _controller.move_servo(6, 300, 300)   # Open claw wide
        _controller.move_servo(3, 700, 500)   # Lift elbow up
        _controller.move_servo(3, 400, 500)   # Swing elbow down
        _controller.move_servo(6, 600, 300)   # Close claw gently
        return "Wave routine executed successfully"
        
    elif "grab" in command_text or "pick up" in command_text:
        _controller.move_servo(6, 200, 400)   # Open claw wide
        _controller.move_servo(2, 650, 800)   # Lower shoulder arm forward
        _controller.move_servo(6, 750, 400)   # Close claw tight around item
        _controller.move_servo(2, 400, 800)   # Lift shoulder up high
        return "Item object acquisition sequence executed"
        
    return "Unknown command signature"

def move_to_kinematic_angles(shoulder_pos, elbow_pos):
    """Receives target coordinates from vision.py object tracking frames."""
    # Servo 2 handles shoulder angles, Servo 3 handles elbow adjustments
    _controller.move_servo(2, shoulder_pos, duration=150)
    _controller.move_servo(3, elbow_pos, duration=150)
