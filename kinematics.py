import numpy as np

# ─── PHYSICAL LINK MEASUREMENTS (HIWONDER xARM 1S STRUCTURAL SPECS) ───
# Lengths measured in centimeters from pivot center to pivot center.
L1 = 10.5  # Shoulder to Elbow bone length 
L2 = 9.0   # Elbow to Wrist/Claw extension length

def calculate_joint_angles(x, y):
    """
    Converts real-world X, Y coordinates (in cm) into raw Hiwonder digital servo
    position values (0 to 1000) instead of old 0-180 degree limits.
    """
    try:
        # Distance calculation from base origin to coordinates
        distance_squared = x**2 + y**2
        
        # 1. Calculate the Elbow Angle (Theta 2) using the Law of Cosines
        cos_theta2 = (distance_squared - L1**2 - L2**2) / (2 * L1 * L2)
        
        # Reach verification: Is the coordinate too far or too close to physically touch?
        if abs(cos_theta2) > 1.0:
            return None, "Target coordinates break extension bounds, sir."
            
        theta2_raw = np.arccos(cos_theta2)
        
        # 2. Calculate the Shoulder Angle (Theta 1)
        theta1_raw = np.arctan2(y, x) - np.arctan2(L2 * np.sin(theta2_raw), L1 + L2 * np.cos(theta2_raw))
        
        # 3. Convert mathematical radians into standard physical rotation degrees
        shoulder_deg = np.degrees(theta1_raw)
        elbow_deg = np.degrees(theta2_raw)
        
        # 4. HIWONDER SERVO MAPPING: Convert 0-240° physical sweep to 0-1000 digital range
        # Note: 500 is the exact center point for all Hiwonder serial bus servos.
        shoulder_pos = int(500 + (shoulder_deg * (1000 / 240.0)))
        elbow_pos = int(500 + (elbow_deg * (1000 / 240.0)))
        
        # 5. HARDWARE MECHANICAL SAFEGUARDS (Prevents arm from hitting its own chassis)
        # We clip the positions strictly inside safe operational windows
        shoulder_safe = np.clip(shoulder_pos, 200, 800)
        elbow_safe = np.clip(elbow_pos, 150, 850)
        
        return (shoulder_safe, elbow_safe), "Kinematic trajectories calculated successfully."
        
    except Exception as e:
        return None, f"Mathematical trajectory calculation failure: {str(e)}"
