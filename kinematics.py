import numpy as np

# Define your physical arm segment lengths in centimeters (Measure your kit!)
L1 = 15.0  # Length from Shoulder to Elbow
L2 = 12.0  # Length from Elbow to Claw

def calculate_joint_angles(x, y):
    """Converts a real-world X, Y target location into degree angles for the Arduino servos."""
    try:
        # 1. Calculate the Elbow Angle (Theta 2) using the Law of Cosines
        cos_theta2 = (x**2 + y**2 - L1**2 - L2**2) / (2 * L1 * L2)
        
        # Safety Check: If the target is physically too far away to reach, stop!
        if abs(cos_theta2) > 1.0:
            return None, "Target is completely out of reach, sir."
            
        theta2_raw = np.arccos(cos_theta2)
        
        # 2. Calculate the Shoulder Angle (Theta 1)
        theta1_raw = np.arctan2(y, x) - np.arctan2(L2 * np.sin(theta2_raw), L1 + L2 * np.cos(theta2_raw))
        
        # 3. Convert the raw mathematical radians into standard motor degrees (0 to 180)
        shoulder_deg = int(np.degrees(theta1_raw))
        elbow_deg = int(np.degrees(theta2_raw))
        
        # Adjust angles to match standard physical servo mounting alignments
        shoulder_deg = np.clip(shoulder_deg, 0, 180)
        elbow_deg = np.clip(elbow_deg, 0, 180)
        
        return (shoulder_deg, elbow_deg), "Angles computed successfully."
        
    except Exception as e:
        return None, f"Mathematical trajectory calculation failure: {str(e)}"
