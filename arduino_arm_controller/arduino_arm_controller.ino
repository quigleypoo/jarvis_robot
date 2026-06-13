#include <Servo.h>

// 1. Structural Joint Names
Servo baseServo;
Servo shoulderServo;
Servo elbowServo;
Servo wristServo;
Servo handClaw;

// 2. Pin Assignments
const int BASE_PIN = 3;
const int SHOULDER_PIN = 5;
const int ELBOW_PIN = 6;
const int WRIST_PIN = 9;
const int CLAW_PIN = 10;

// Current angles (0 to 180 degrees)
int currentBase = 90;
int currentShoulder = 90;
int currentElbow = 90;
int currentWrist = 90;
int currentClaw = 45;

void setup() {
  Serial.begin(9600);
  
  // --- HARDWARE FALLBACK FEATURE ---
  // We check if the pins are electrically open or floating. If no servos are plugged 
  // into the board yet, the software runs in a "Virtual Mode" so it never freezes.
  bool hardwareDetected = (analogRead(A0) < 1000); 

  if (hardwareDetected) {
    baseServo.attach(BASE_PIN);
    shoulderServo.attach(SHOULDER_PIN);
    elbowServo.attach(ELBOW_PIN);
    wristServo.attach(WRIST_PIN);
    handClaw.attach(CLAW_PIN);
    Serial.println("🔌 PHYSICAL HARDWARE DETECTED: Initialization successful.");
  } else {
    Serial.println("🤖 HARDWARE NOT DETECTED: Running in Virtual Simulator Mode.");
  }
  
  goHome();
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command == "CMD:GRAB") {
      Serial.println("Executing Action: Closing Claw Grippers...");
      moveSmoothSCurve(handClaw, currentClaw, 150); 
      currentClaw = 150;
    } 
    else if (command == "CMD:RELEASE") {
      Serial.println("Executing Action: Releasing Claw Grippers...");
      moveSmoothSCurve(handClaw, currentClaw, 45);  
      currentClaw = 45;
    } 
    else if (command == "CMD:HOME") {
      goHome();
    }
  }
}

// 3. S-CURVE KINEMATICS: Moves the arm using a smooth, natural acceleration profile
void moveSmoothSCurve(Servo targetedServo, int startingAngle, int endingAngle) {
  int totalDistance = abs(endingAngle - startingAngle);
  if (totalDistance == 0) return;

  // Split the physical movement up into 30 granular speed steps
  int totalSteps = 30; 
  
  for (int step = 0; step <= totalSteps; step++) {
    // Generate an S-Curve scaling factor between 0.0 and 1.0 using a cosine wave
    float progress = (float)step / totalSteps;
    float sCurveFactor = (1.0 - cos(progress * PI)) / 2.0;
    
    // Calculate the precise destination angle for this millisecond fraction
    int nextAngle;
    if (startingAngle < endingAngle) {
      nextAngle = startingAngle + (totalDistance * sCurveFactor);
    } else {
      nextAngle = startingAngle - (totalDistance * sCurveFactor);
    }
    
    // Safety check: Only push electrical data if a servo motor object is safely attached
    if (targetedServo.attached()) {
      targetedServo.write(nextAngle);
    }
    
    // Print a rolling status so you can watch the movement simulation on your laptop screen
    if (step % 10 == 0) {
      Serial.print("Simulating Joint Position -> ");
      Serial.println(nextAngle);
    }
    
    // A 20ms pause gives the motor time to breathe, creating a cinematic, intentional movement
    delay(20); 
  }
}

void goHome() {
  Serial.println("System Routing: Moving all active joints back to resting pose...");
  moveSmoothSCurve(baseServo, currentBase, 90);       currentBase = 90;
  moveSmoothSCurve(shoulderServo, currentShoulder, 90); currentShoulder = 90;
  moveSmoothSCurve(elbowServo, currentElbow, 90);       currentElbow = 90;
  moveSmoothSCurve(wristServo, currentWrist, 90);       currentWrist = 90;
  moveSmoothSCurve(handClaw, currentClaw, 45);          currentClaw = 45;
  Serial.println("System Ready, Sir.");
}

