/**
 * OMNISOUND Arduino Motor Controller
 * Serial communication protocol
 *
 * Protocol:
 *   M{id} F{frequency} A{amplitude}\n  - Set motor frequency/amplitude
 *   A{id} {angle}\n                    - Set motor angle directly
 *   ?\n                                - Query config
 *   PING\n                             - Ping
 *
 * Response:
 *   OK M{id}\n                         - Acknowledgment
 *   ERROR {message}\n                  - Error
 *   CONFIG:{motor_count},{...}\n       - Config response
 *   STATE:{motor_id}:{angle},...\n     - State broadcast
 */

#include <Servo.h>

// Configuration
#define MOTOR_COUNT 4
#define BAUD_RATE 115200
#define SERIAL_TIMEOUT 1000

// Motor pins (default: PWM capable pins)
const int MOTOR_PINS[MOTOR_COUNT] = {3, 5, 6, 9};

// Servo objects
Servo motors[MOTOR_COUNT];

// Motor state
struct MotorState {
  int id;
  float angle;
  float targetAngle;
  float frequency;
  float amplitude;
  unsigned long lastUpdate;
  bool enabled;
};

MotorState motorState[MOTOR_COUNT];

// Input buffer
char inputBuffer[128];
int bufferIndex = 0;

// Status LED
#define LED_PIN 13

void setup() {
  Serial.begin(BAUD_RATE);
  Serial.setTimeout(SERIAL_TIMEOUT);

  pinMode(LED_PIN, OUTPUT);

  // Initialize motors
  for (int i = 0; i < MOTOR_COUNT; i++) {
    motors[i].attach(MOTOR_PINS[i]);
    motorState[i].id = i;
    motorState[i].angle = 90.0;
    motorState[i].targetAngle = 90.0;
    motorState[i].frequency = 0.0;
    motorState[i].amplitude = 0.0;
    motorState[i].enabled = true;
    motorState[i].lastUpdate = millis();

    // Set initial position
    motors[i].write(90);
  }

  // Signal ready
  digitalWrite(LED_PIN, HIGH);
  delay(500);
  digitalWrite(LED_PIN, LOW);

  Serial.println("OMNISOUND Arduino Ready");
  Serial.print("Motor Count: ");
  Serial.println(MOTOR_COUNT);
}

void loop() {
  // Read serial data
  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n') {
      inputBuffer[bufferIndex] = '\0';
      processCommand(inputBuffer);
      bufferIndex = 0;
    } else if (bufferIndex < sizeof(inputBuffer) - 1) {
      inputBuffer[bufferIndex++] = c;
    }
  }

  // Update motors
  updateMotors();

  // Broadcast state
  static unsigned long lastBroadcast = 0;
  if (millis() - lastBroadcast > 100) { // 10Hz
    broadcastState();
    lastBroadcast = millis();
  }
}

void processCommand(const char* command) {
  // Skip empty commands
  if (strlen(command) == 0) return;

  // Parse command
  if (command[0] == 'M') {
    // Motor command: M{id} F{freq} A{amp}
    int id = -1;
    float freq = 0.0, amp = 0.0;

    // Parse using sscanf
    if (sscanf(command, "M%d F%f A%f", &id, &freq, &amp) == 3) {
      if (id >= 0 && id < MOTOR_COUNT) {
        motorState[id].frequency = freq;
        motorState[id].amplitude = amp / 100.0; // Convert percentage to 0-1

        // Map to angle
        float angle = 90.0 + (motorState[id].amplitude * 45.0);
        motorState[id].targetAngle = angle;

        Serial.print("OK M");
        Serial.println(id);
      } else {
        Serial.print("ERROR Invalid motor ID: ");
        Serial.println(id);
      }
    } else {
      Serial.println("ERROR Parse error");
    }
  }
  else if (command[0] == 'A') {
    // Angle command: A{id} {angle}
    int id = -1;
    float angle = 0.0;

    if (sscanf(command, "A%d %f", &id, &angle) == 2) {
      if (id >= 0 && id < MOTOR_COUNT) {
        setMotorAngle(id, angle);
        Serial.print("OK A");
        Serial.println(id);
      } else {
        Serial.print("ERROR Invalid motor ID: ");
        Serial.println(id);
      }
    }
  }
  else if (strcmp(command, "?") == 0) {
    // Query config
    Serial.print("CONFIG:");
    Serial.print("M");
    Serial.print(MOTOR_COUNT);
    Serial.println(",END");
  }
  else if (strcmp(command, "PING") == 0) {
    Serial.println("PONG");
  }
  else if (strncmp(command, "ENABLE ", 7) == 0) {
    int id = atoi(command + 7);
    if (id >= 0 && id < MOTOR_COUNT) {
      motorState[id].enabled = true;
      Serial.print("OK ENABLE ");
      Serial.println(id);
    }
  }
  else if (strncmp(command, "DISABLE ", 8) == 0) {
    int id = atoi(command + 8);
    if (id >= 0 && id < MOTOR_COUNT) {
      motorState[id].enabled = false;
      Serial.print("OK DISABLE ");
      Serial.println(id);
    }
  }
  else {
    Serial.print("ERROR Unknown command: ");
    Serial.println(command);
  }
}

void setMotorAngle(int id, float angle) {
  if (id < 0 || id >= MOTOR_COUNT) return;

  // Constrain angle
  angle = constrain(angle, 0, 180);

  motorState[id].angle = angle;
  motorState[id].targetAngle = angle;

  // Apply to servo
  if (motorState[id].enabled) {
    motors[id].write((int)angle);
  }
}

void updateMotors() {
  // Smooth motor movement
  for (int i = 0; i < MOTOR_COUNT; i++) {
    if (!motorState[i].enabled) continue;

    float diff = motorState[i].targetAngle - motorState[i].angle;
    if (abs(diff) > 0.5) {
      motorState[i].angle += diff * 0.3; // Smoothing
      motors[i].write((int)motorState[i].angle);
    }
  }
}

void broadcastState() {
  // Send state update
  Serial.print("STATE:");
  for (int i = 0; i < MOTOR_COUNT; i++) {
    if (i > 0) Serial.print(",");
    Serial.print(i);
    Serial.print(":");
    Serial.print((int)motorState[i].angle);
  }
  Serial.println();
}