# OMNISOUND Hardware Setup Guide

This comprehensive guide covers all hardware configurations and wiring options for OMNISOUND.

## Table of Contents

1. [Hardware Components](#hardware-components)
2. [Pinout Configurations](#pinout-configurations)
3. [Power Requirements](#power-requirements)
4. [Wiring Diagrams](#wiring-diagrams)
5. [Troubleshooting Hardware](#troubleshooting-hardware)

---

## Hardware Components

### Microcontrollers

#### ESP32 (Recommended)

| Specification | Value |
|--------------|-------|
| Processor | Xtensa LX6 Dual-Core |
| Clock Speed | 240 MHz |
| Flash | 4MB |
| RAM | 520 KB |
| WiFi | 802.11 b/g/n |
| Bluetooth | 4.2 / BLE |
| Operating Voltage | 3.3V |
| GPIO | 34 pins |

**Recommended Boards:**
- ESP32 DevKit V1 (DOIT)
- ESP32-WROOM-32
- ESP32-S3 (for more RAM)

#### Arduino Options

| Board | Servo Channels | WiFi | Notes |
|-------|---------------|------|-------|
| Arduino Uno | 6 (native) | No | Simple, no WiFi |
| Arduino Mega 2560 | 12 (native) | No | More servos |
| Arduino Nano | 6 (native) | No | Compact |

#### Raspberry Pi Pico

| Specification | Value |
|--------------|-------|
| Processor | RP2040 Dual-Core |
| Clock Speed | 133 MHz |
| Flash | 2MB |
| RAM | 264 KB |
| GPIO | 40 pins |

---

### I2S Microphones

#### Supported Microphones

| Microphone | Interface | Sample Rate | SNR | Notes |
|------------|-----------|-------------|-----|-------|
| INMP441 | I2S | 8-16kHz | 61 dB | Most common |
| SPH0645 | I2S | 4-48kHz | 65 dB | Analog Devices |
| ICS-43434 | I2S | 8-48kHz | 65 dB | Low profile |
| MSMF-2610 | I2S | 48kHz | 62 dB | Tiny form factor |

#### Microphone Pinouts

**INMP441 Pinout:**
```
┌─────────────────────────┐
│    INMP441 Module       │
├─────────────────────────┤
│ VCC   │ 3.3V            │
│ GND   │ Ground          │
│ WS    │ Word Select     │
│ SCK   │ Serial Clock    │
│ SD    │ Serial Data     │
│ L/R   │ Left/Right Sel  │
└─────────────────────────┘
```

#### Microphone Selection Guide

| Use Case | Recommended | Reason |
|----------|-------------|--------|
| General Use | INMP441 | Best price/performance |
| High Quality | SPH0645 | Higher SNR |
| Space Limited | ICS-43434 | Small footprint |
| Maximum Sample Rate | Any 48kHz | High-res audio |

---

### Servo Motors

#### Supported Servo Types

| Servo Type | Torque | Speed | Voltage | Resolution |
|------------|--------|-------|---------|-------------|
| SG90 | 1.8 kg·cm | 0.12s/60° | 4.8-6V | 1° |
| SG92R | 2.5 kg·cm | 0.10s/60° | 4.8-6V | 1° |
| MG996R | 9.4 kg·cm | 0.14s/60° | 4.8-7.2V | 1° |
| MG995 | 10 kg·cm | 0.20s/60° | 4.8-6V | 1° |

#### Servo Control Methods

1. **Direct PWM (Native GPIO)**
   - Pros: Simple, no extra hardware
   - Cons: Limited to 4-8 servos

2. **PCA9685 (I2C Servo Driver)**
   - Pros: 16 channels, stackable
   - Cons: Requires I2C wiring

3. **Custom Servo Shield**
   - Pros: Dedicated solution
   - Cons: More complex

---

## Pinout Configurations

### ESP32 Default Configuration

```
═══════════════════════════════════════════════════════════════════════════════
                            ESP32 PINOUT (DEFAULT)
═══════════════════════════════════════════════════════════════════════════════

                        ┌───────────────────────┐
                        │   ESP32 DEVKIT V1    │
                        │                       │
   ─────────────────────┤                       ├────────────────────────────
                        │                       │
   3.3V ───────────────┤ 3V3   ────   EN      ├────── RST/EN Button
                        │                       │
   GND ────────────────┤ GND   ────  VP (36)   ├────── SENSOR_VP (ADC0)
                        │                       │
   NC ─────────────────┤ SVN   ────  VN (39)   ├────── SENSOR_VN (ADC3)
                        │                       │
   GPIO34 ─────────────┤ IO34  ────  IO35      ├────── ADC5
   (Input Only)        │ (ADC4)     (ADC6)     │
                        │                       │
   GPIO32 ─────────────┤ IO32  ────  IO33      ├────── GPIO33
   (T0)                │ (T1)       (T2)       │
                        │                       │
   GPIO25 ─────────────┤ IO25  ────  IO26      ├────── GPIO26
   (I2S WS) ←─────────│ (DAC1)      (DAC2)    │← (To be used)
                        │                       │
   GPIO27 ─────────────┤ IO27  ────  IO14     ├────── GPIO14
   (I2S SD) ←─────────│ (T3)       (T4)       │← SERVO_2 SIG
                        │                       │
   GPIO13 ─────────────┤ IO13  ────  IO12     ├────── GPIO12
   (SERVO_1) ←─────────│ (T5)       (T6)       │← (Pull-down issue)
                        │                       │
   GPIO15 ─────────────┤ IO15  ────  IO2      ├────── GPIO2
   (T7)                │ (T8)       (T9)      │← Built-in LED
                        │                       │
   GPIO4 ──────────────┤ IO4   ────  IO0      ├────── GPIO0
   (T10)               │ (T11)      (T12)      │← BOOT Button
                        │                       │
                        └───────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
                            GPIO ASSIGNMENTS
═══════════════════════════════════════════════════════════════════════════════

Audio Input (I2S):
  • GPIO25 (WS)   - I2S Word Select
  • GPIO26 (SCK)  - I2S Serial Clock
  • GPIO27 (SD)   - I2S Serial Data

Servo Output:
  • GPIO13 - Servo 1 (Bass)
  • GPIO14 - Servo 2 (Mid)
  • GPIO27 - Servo 3 (High) - OR use different pin
  • GPIO26 - Servo 4 (Beat)

Optional:
  • GPIO2 - Built-in LED (status)
  • GPIO4 - Additional servo (if needed)

═══════════════════════════════════════════════════════════════════════════════
```

### Custom Pin Configuration

Edit `firmware/esp32/src/main.cpp` to change pins:

```cpp
// Audio pins
#define I2S_WS_PIN  25      // Word Select
#define I2S_SCK_PIN 26      // Serial Clock
#define I2S_SD_PIN 27       // Serial Data

// Servo pins (change these)
const uint8_t MOTOR_PINS[] = {13, 14, 27, 26};
//                              │  │  │  │
//                              │  │  │  └── Servo 4
//                              │  │  └──── Servo 3
//                              │  └──────── Servo 2
//                              └─────────── Servo 1
```

---

## Power Requirements

### Power Budget

| Component | Voltage | Current (Idle) | Current (Active) |
|-----------|---------|----------------|------------------|
| ESP32 | 3.3V | 80mA | 180mA |
| INMP441 | 3.3V | 600μA | 600μA |
| SG90 ×4 | 5V | 0mA | 2.4A (600mA each) |
| **Total** | - | ~81mA | ~2.6A |

### Power Supply Recommendations

| Configuration | Recommended PSU | Notes |
|--------------|-----------------|-------|
| Testing Only | USB Cable (500mA) | Limited servo movement |
| 2 Servos | 5V 1A USB Charger | Basic operation |
| 4 Servos | 5V 2A Power Supply | Full operation |
| Maximum | 5V 3A Power Supply | All servos + ESP32 |

### Power Wiring Diagrams

**Basic Setup (USB Power):**
```
┌─────────────┐        USB        ┌─────────────┐
│  Computer   │───────────────────│   ESP32     │
│             │                   │             │
│             │                   │  ┌───────┐  │
└─────────────┘                   │  │ Servo │  │
                                 │  │  1-2 │  │
                                 │  └───────┘  │
                                 └─────────────┘
```

**External Power Setup (Recommended):**
```
                    ┌─────────────────────────────────────┐
                    │         5V 2A Power Supply          │
                    └──────────────────┬──────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
            ┌───────────┐       ┌────────────┐       ┌───────────┐
            │   ESP32   │       │ Servo 1-2  │       │ Servo 3-4 │
            │           │       │            │       │           │
            │ 3.3V ─────┼───────│ 5V (share) │       │ 5V (share)│
            │           │       │            │       │           │
            │ GND ──────┼───────┤ GND        │───────┤ GND        │
            └───────────┘       └────────────┘       └───────────┘

    IMPORTANT: Always connect ALL grounds together!
```

---

## Wiring Diagrams

### Complete System Diagram

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                        OMNISOUND COMPLETE WIRING DIAGRAM                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║                    ┌──────────────────────┐                                  ║
║                    │   5V 2A Power Supply │                                  ║
║                    └──────────┬─────────────┘                                  ║
║                               │                                               ║
║              ┌────────────────┼────────────────┐                              ║
║              │                │                │                              ║
║              ▼                ▼                ▼                              ║
║     ┌────────────┐   ┌────────────┐   ┌────────────┐                         ║
║     │  ESP32     │   │ SERVO 1-2  │   │ SERVO 3-4  │                         ║
║     │            │   │            │   │            │                         ║
║     │ ┌────────┐ │   │  ┌──────┐ │   │  ┌──────┐ │                         ║
║     │ │I2S Mic │ │   │  │ SG90 │ │   │  │ SG90 │ │                         ║
║     │ └────────┘ │   │  └──────┘ │   │  └──────┘ │                         ║
║     │            │   │            │   │            │                         ║
║     │ 3.3V ──────┼───┼───────5V ──┼───┼───────5V   │                         ║
║     │            │   │            │   │            │                         ║
║     │ GND ───────┼───┼───────GND ─┼───┼───────GND  │                         ║
║     └────────────┘   └────────────┘   └────────────┘                         ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                          DETAILED CONNECTIONS                                ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  I2S MEMPHONE (INMP441):                                                    ║
║  ──────────────────────────                                                   ║
║  INMP441 Pin    →    ESP32 Pin                                               ║
║  ─────────────────────────────────                                          ║
║  VCC            →    3.3V (ESP32)                                          ║
║  GND            →    GND (ESP32)                                            ║
║  WS (L/R)       →    GPIO 25                                                 ║
║  SCK            →    GPIO 26                                                 ║
║  SD             →    GPIO 27                                                 ║
║  L/R (SEL)      →    GND (for Left channel)                                 ║
║                                                                              ║
║  SERVO MOTORS:                                                              ║
║  ────────────                                                               ║
║  Servo Pin     →    ESP32 Pin                                               ║
║  ─────────────────────────────────                                          ║
║  Servo 1 VCC   →    5V (External PSU)                                      ║
║  Servo 1 GND   →    GND (Common)                                            ║
║  Servo 1 SIG   →    GPIO 13                                                 ║
║                                                                              ║
║  Servo 2 VCC   →    5V (External PSU)                                      ║
║  Servo 2 GND   →    GND (Common)                                            ║
║  Servo 2 SIG   →    GPIO 14                                                 ║
║                                                                              ║
║  Servo 3 VCC   →    5V (External PSU)                                      ║
║  Servo 3 GND   →    GND (Common)                                            ║
║  Servo 3 SIG   →    GPIO 27                                                 ║
║                                                                              ║
║  Servo 4 VCC   →    5V (External PSU)                                      ║
║  Servo 4 GND   →    GND (Common)                                            ║
║  Servo 4 SIG   →    GPIO 26                                                 ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                          POWER DISTRIBUTION                                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║   ┌─────────────────┐                                                       ║
║   │ 5V 2A Supply    │                                                       ║
║   └────────┬────────┘                                                       ║
║            │                                                                ║
║     ┌──────┼──────┐                                                         ║
║     │      │      │                                                         ║
║     ▼      ▼      ▼                                                         ║
║   ┌───┐  ┌───┐  ┌───┐                                                       ║
║   │ESP│  │S1 │  │S2 │  Servos powered by external supply!                  ║
║   │32 │  │S3 │  │S4 │                                                       ║
║   └───┘  └───┘  └───┘                                                       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## Troubleshooting Hardware

### Diagnostic Checklist

- [ ] Power LED on ESP32 lit?
- [ ] 3.3V present at microphone?
- [ ] 5V present at servos?
- [ ] All grounds connected together?
- [ ] Correct GPIO pins for I2S?

### Common Issues

#### Issue: Servos Jitter or Don't Move

**Causes:**
1. Insufficient power
2. Ground not connected
3. Wrong PWM frequency

**Solutions:**
```cpp
// In main.cpp - adjust servo parameters
#define PWM_FREQUENCY 50  // Standard servo frequency

// Initialize servo with proper bounds
servos[i].attach(MOTOR_PINS[i], 500, 2500);  // min, max pulse width
```

#### Issue: Microphone No Audio

**Causes:**
1. Wrong I2S pins
2. Microphone in wrong channel mode
3. Missing 3.3V power

**Solutions:**
```cpp
// Verify I2S configuration
i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,  // Important!
    // ...
};
```

#### Issue: ESP32 Not Booting

**Causes:**
1. Power supply insufficient
2. GPIO0 grounded (forces boot mode)
3. Damaged flash

**Solutions:**
1. Use 5V 2A power supply
2. Ensure GPIO0 is not connected to GND
3. Try pressing EN button to reset

### Testing Individual Components

#### Test I2S Microphone

```bash
# Using esptool
esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash
esptool.py --chip esp32 --port /dev/ttyUSB0 write_flash 0x1000 firmware.bin

# Monitor serial output
pio device monitor --port /dev/ttyUSB0 --baud 115200
```

#### Test Servos Manually

```cpp
// Add to main.cpp for testing
void testServos() {
    for(int i = 0; i < MOTOR_COUNT; i++) {
        servos[i].write(45);
        delay(500);
        servos[i].write(135);
        delay(500);
        servos[i].write(90);
    }
}
```

#### Test I2S Microphone

```cpp
// Read raw I2S data
size_t bytesRead = 0;
i2s_read(I2S_PORT, audioBuffer, sizeof(audioBuffer), &bytesRead, 0);

// Print to serial
for(int i = 0; i < bytesRead/sizeof(int16_t); i++) {
    Serial.println(audioBuffer[i]);
}
```

---

## Advanced Configurations

### Using PCA9685 Servo Driver

```cpp
// Connections:
// PCA9685 VCC → 5V
// PCA9685 GND → GND
// PCA9685 SDA → ESP32 GPIO 21 (SDA)
// PCA9685 SCL → ESP32 GPIO 22 (SCL)

// Code to use PCA9685 (requires Adafruit_PWMServoDriver library)
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

void setServoPCA(uint8_t num, uint8_t angle) {
    uint16_t pulselength = map(angle, 0, 180, 500, 2500);
    pwm.setPWM(num, 0, pulselength);
}
```

### Using External Power for All Servos

```
Power Supply (5V 3A)
     │
     ├────────► Servo 1 VCC
     ├────────► Servo 2 VCC
     ├────────► Servo 3 VCC
     ├────────► Servo 4 VCC
     │
     └────────► ESP32 5V (optional, for stability)

Common Ground: All components share one ground.
```

---

## Safety Notes

⚠️ **IMPORTANT SAFETY GUIDELINES:**

1. **Never power servos from ESP32 5V** - Can damage the ESP32
2. **Always use common ground** - All components must share ground
3. **Use appropriate power supply** - Insufficient power causes unpredictable behavior
4. **Check polarity** - Reversed power can destroy components
5. **Secure connections** - Loose wires cause intermittent failures
6. **Ventilation** - Servos can get warm under load

---

## Next Steps

- [Configuration Guide](CONFIGURATION.md)
- [API Reference](API.md)
- [Troubleshooting](TROUBLESHOOTING.md)