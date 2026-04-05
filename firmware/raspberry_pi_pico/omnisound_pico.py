"""
OMNISOUND Raspberry Pi Pico Motor Controller
MicroPython firmware for USB serial communication

Protocol:
  M{id} F{frequency} A{amplitude}\n  - Set motor frequency/amplitude
  A{id} {angle}\n                    - Set motor angle
  ?\n                                - Query config
  PING\n                             - Ping
"""

import machine
import uasyncio as asyncio
from machine import PWM, Pin
import sys

# Configuration
MOTOR_COUNT = 4
MOTOR_PINS = [0, 1, 2, 3]  # Default GPIO pins (PWM capable)
SERIAL_BAUD = 115200

# Motor state
motors = []
for i in range(MOTOR_COUNT):
    motors.append({
        'id': i,
        'angle': 90.0,
        'target_angle': 90.0,
        'frequency': 0.0,
        'amplitude': 0.0,
        'enabled': True
    })

# PWM frequency (50Hz for servos)
PWM_FREQ = 50

# Initialize PWM for motors
pwms = []
for i, pin in enumerate(MOTOR_PINS):
    pwm = PWM(Pin(pin))
    pwm.freq(PWM_FREQ)
    pwms.append(pwm)


def angle_to_duty(angle):
    """Convert angle (0-180) to duty cycle (0-65535)"""
    # Servo pulse: 0.5ms to 2.5ms at 50Hz (20ms period)
    # Duty: 3276 to 16383 (for 0.5ms to 2.5ms)
    min_duty = 1638  # 0.5ms pulse
    max_duty = 8191  # 2.5ms pulse

    duty = min_duty + (angle / 180.0) * (max_duty - min_duty)
    return int(duty)


def set_motor_angle(motor_id, angle):
    """Set motor angle directly"""
    if motor_id < 0 or motor_id >= MOTOR_COUNT:
        return False

    angle = max(0, min(180, angle))
    motors[motor_id]['angle'] = angle
    motors[motor_id]['target_angle'] = angle

    duty = angle_to_duty(angle)
    pwms[motor_id].duty_u16(duty)
    return True


def update_motors():
    """Update motor positions (smoothing)"""
    for i in range(MOTOR_COUNT):
        if not motors[i]['enabled']:
            continue

        diff = motors[i]['target_angle'] - motors[i]['angle']
        if abs(diff) > 0.5:
            motors[i]['angle'] += diff * 0.3
            duty = angle_to_duty(motors[i]['angle'])
            pwms[i].duty_u16(duty)


def process_command(command):
    """Process incoming serial command"""
    global motors

    command = command.strip()
    if not command:
        return

    try:
        if command.startswith('M'):
            # Motor command: M{id} F{freq} A{amp}
            parts = command.split()
            motor_id = int(parts[0][1:])
            freq = 0.0
            amp = 0.0

            for part in parts[1:]:
                if part.startswith('F'):
                    freq = float(part[1:])
                elif part.startswith('A'):
                    amp = float(part[1:]) / 100.0

            if 0 <= motor_id < MOTOR_COUNT:
                motors[motor_id]['frequency'] = freq
                motors[motor_id]['amplitude'] = amp

                # Map amplitude to angle
                angle = 90.0 + (amp * 45.0)
                motors[motor_id]['target_angle'] = angle

                print(f"OK M{motor_id}")
            else:
                print(f"ERROR Invalid motor ID: {motor_id}")

        elif command.startswith('A'):
            # Angle command: A{id} {angle}
            parts = command.split()
            motor_id = int(parts[0][1:])
            angle = float(parts[1])

            if 0 <= motor_id < MOTOR_COUNT:
                set_motor_angle(motor_id, angle)
                print(f"OK A{motor_id}")
            else:
                print(f"ERROR Invalid motor ID: {motor_id}")

        elif command == '?':
            # Query config
            print(f"CONFIG:M{MOTOR_COUNT},END")

        elif command == 'PING':
            print("PONG")

        elif command.startswith('ENABLE '):
            motor_id = int(command[7:])
            if 0 <= motor_id < MOTOR_COUNT:
                motors[motor_id]['enabled'] = True
                print(f"OK ENABLE {motor_id}")

        elif command.startswith('DISABLE '):
            motor_id = int(command[8:])
            if 0 <= motor_id < MOTOR_COUNT:
                motors[motor_id]['enabled'] = False
                print(f"OK DISABLE {motor_id}")

        else:
            print(f"ERROR Unknown command: {command}")

    except Exception as e:
        print(f"ERROR {e}")


async def serial_reader():
    """Read from serial port"""
    buffer = ""

    while True:
        if sys.stdin in select([sys.stdin], [], [], 0)[0]:
            char = sys.stdin.read(1)
            if char == '\n':
                process_command(buffer)
                buffer = ""
            else:
                buffer += char
        else:
            await asyncio.sleep(0.01)


async def motor_updater():
    """Update motors periodically"""
    while True:
        update_motors()
        await asyncio.sleep(0.02)  # 50Hz


async def state_broadcaster():
    """Broadcast state periodically"""
    while True:
        # Build state message
        state_parts = []
        for i in range(MOTOR_COUNT):
            state_parts.append(f"{i}:{int(motors[i]['angle'])}")

        print("STATE:" + ",".join(state_parts))
        await asyncio.sleep(0.1)  # 10Hz


async def main():
    """Main entry point"""
    print("OMNISOUND Pico Ready")
    print(f"Motor Count: {MOTOR_COUNT}")

    # Initialize motors to center position
    for i in range(MOTOR_COUNT):
        set_motor_angle(i, 90)

    # Start tasks
    await asyncio.gather(
        serial_reader(),
        motor_updater(),
        state_broadcaster()
    )


# Import select for async serial reading
import select

# Run main
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Stopped")
    for pwm in pwms:
        pwm.deinit()