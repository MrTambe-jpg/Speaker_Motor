# OMNISOUND - Universal Motor Speaker System

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-ESP32%20%7C%20Arduino%20%7C%20Pico-orange)](https://www.espressif.com/)
[![Language](https://img.shields.io/badge/language-C%2B%2B%20%7C%20Python%20%7C%20MicroPython-blue)](https://www.python.org/)
[![WebUI](https://img.shields.io/badge/WebUI-React%20%7C%20Vanilla%20JS-green)](https://reactjs.org)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

*A revolutionary audio-reactive motor speaker system using thin-client microcontroller architecture*

</div>

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Hardware Setup](#hardware-setup)
5. [Installation](#installation)
6. [Usage Guide](#usage-guide)
7. [Configuration](#configuration)
8. [API Reference](#api-reference)
9. [Troubleshooting](#troubleshooting)
10. [Development](#development)
11. [FAQ](#faq)
12. [License](#license)

---

## Overview

OMNISOUND is an innovative audio visualization and motor control system that uses servos to create physical sound representation. Unlike traditional speakers that produce sound waves through air vibration, OMNISOUND creates visible, physical movement in response to audio frequencies.

### What Makes OMNISOUND Unique?

Traditional audio-reactive projects often overwhelm microcontrollers with heavy DSP processing (FFT, beat detection, etc.). OMNISOUND uses a **thin-client architecture** that:

- **Minimizes MCU resource usage** - Only ~10KB RAM on ESP32
- **Offloads processing** - All audio analysis happens on your phone/laptop
- **Extends battery life** - MCU does minimal work
- **Works offline** - No internet required after initial setup

### Why This Architecture?

The connected device (phone/tablet/computer) has orders of magnitude more processing power than any microcontroller. By leveraging Web Audio API and WebSockets, we create a system where:

1. **ESP32** captures audio → streams raw PCM → moves servos
2. **Phone** receives audio → performs FFT → detects beats → maps to motor angles → sends commands back

This results in:
- Instant visual feedback (< 50ms latency)
- Professional-grade audio analysis
- Beautiful real-time visualizations
- Zero compilation needed for algorithm changes

---

## Features

### Core Features

| Feature | Description |
|---------|-------------|
| **Real-time Waveform** | Visualize audio waveform in real-time |
| **FFT Spectrum Analyzer** | See frequency distribution |
| **Beat Detection** | Detect kicks, snares, onsets |
| **Frequency Band Mapping** | Map specific frequencies to motors |
| **4-Channel Servo Control** | Control up to 4 servos independently |
| **Responsive Web UI** | Works on mobile and desktop |

### Technical Features

- **Captive Portal** - Auto-connect WiFi setup
- **mDNS Support** - Access via `omnisound.local`
- **Binary WebSocket** - Efficient audio streaming
- **Embedded App** - No external server needed
- **Multiple Hardware Support** - ESP32, Arduino, Raspberry Pi Pico

### ESP32 Firmware Features

- I2S MEMS microphone capture (16kHz)
- WebSocket server (port 81)
- Servo PWM control (4 channels)
- Captive portal DNS
- Embedded HTML/CSS/JavaScript UI
- NVS configuration storage
- BLE fallback (optional)

---

## Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            OMNISOUND SYSTEM ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────┐           ┌───────────────────────────────┐  │
│  │      ESP32 (MCU)          │           │     CONNECTED DEVICE          │  │
│  │                           │           │                               │  │
│  │  ┌─────────────────────┐  │           │  ┌─────────────────────────┐  │  │
│  │  │ I2S MEMS Microphone │──┼─Stream──▶│  │    Web Audio API         │ │  │
│  │  │ (Audio Capture)     │  │  (Binary) │  │   (AudioContext)        │  │  │
│  │  └─────────────────────┘  │           │  └───────────┬─────────────┘  │  │
│  │              │            │           │              │                │  │
│  │              ▼            │           │              ▼                │  │
│  │  ┌─────────────────────┐  │           │  ┌─────────────────────────┐  │  │
│  │  │ WebSocket Server    │◀─┼──────────┼──│   FFT Analyzer          │  │  │
│  │  │ (Port 81)           │  │  (Text)   │  │   (AnalyserNode)        │  │  │
│  │  └──────────┬──────────┘  │           │  └───────────┬─────────────┘  │  │
│  │             │             │           │              │                │  │
│  │             ▼             │           │              ▼                │  │
│  │  ┌─────────────────────┐  │           │  ┌─────────────────────────┐  │  │
│  │  │ Command Parser      │──┼──Parse───▶│  │   Beat Detector        │  │  │
│  │  │ (Motor Angles)      │  │           │  │   (Energy Detection)    │  │  │
│  │  └──────────┬──────────┘  │           │  └───────────┬─────────────┘  │  │
│  │             │             │           │              │                │  │
│  │             ▼             │           │              ▼                │  │
│  │  ┌─────────────────────┐  │           │  ┌─────────────────────────┐  │  │
│  │  │ Servo PWM Control   │◀─┼───────────┼──│   Motor Mapping         │ │  │
│  │  │ (4 Channels)        │  │  Angles  │  │   (Frequency→Angle)       │ │  │
│  │  └─────────────────────┘  │           │  └───────────┬─────────────┘  │  │
│  │                           │           │              │                │  │
│  └───────────────────────────┘           │              ▼                │  │
│                                          │  ┌─────────────────────────┐  │  │
│                                          │  │   WebSocket Client      │  │  │
│                                          │  │   (Send Commands)       │  │  │
│                                          │  └─────────────────────────┘  │  │
│                                          │                               │  │
│                                          └───────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW DIAGRAM                               │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   TIMESTAMP   │  ESP32 ACTION              │  DEVICE ACTION                  │
│   ─────────── │  ──────────────────────────│─────────────────────────────────│
│               │                            │                                 │
│   T+0ms       │  Capture I2S audio         │                                 │
│               │  ──────────────────────▶  │                                 │
│               │                            │                                 │
│   T+5ms       │  Send raw PCM (binary)     │                                 │
│               │  ──────────────────────▶  │                                 │
│               │                             │                                 │
│               │                             │  Receive PCM buffer             │
│               │                             │  ─────────────────────▶        │
│               │                             │                                 │
│               │                             │  Web Audio API Processing       │
│               │                             │  • FFT Analysis                 │
│               │                             │  • Beat Detection               │
│               │                             │  • Band Splitting               │
│               │                             │                                 │
│               │                             │  Calculate motor angles         │
│               │                             │  ──────────────▶               │
│               │                             │                                 │
│               │  Receive angle command      │                                 │
│               │  ◀────────────────────────  │  Send: {"m0":90,"m1":45,...}   │
│               │                             │                                 │
│   T+30ms      │  Update servo positions     │                                 │
│               │  ──────────────────────▶   │                                 │
│               │                             │                                 │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Memory Optimization

| Component | Traditional (KB) | OMNISOUND (KB) | Savings |
|-----------|------------------|----------------|---------|
| Audio Buffer | 64 | 1 | 63 |
| FFT Buffer | 32 | 0 | 32 |
| JSON Parser | 16 | 0.5 | 15.5 |
| Motor States | 1 | 0.03 | 0.97 |
| WebSocket | 8 | 4 | 4 |
| **TOTAL** | **121** | **~10** | **~111** |

---

## Hardware Setup

### Required Components

#### Core Components

| Component | Model | Quantity | Cost (Approx) |
|-----------|-------|----------|---------------|
| Microcontroller | ESP32 Dev Board | 1 | $5-10 |
| Microphone | INMP441 (I2S) | 1 | $3-5 |
| Servo Motors | SG90 (180°) | 4 | $4-8 |
| Power Supply | 5V 2A | 1 | $5-10 |
| Jumper Wires | Various | 20+ | $2-5 |
| Breadboard/PCB | Mini | 1 | $2-5 |

**Total: ~$25-45**

#### Optional Components

| Component | Purpose | Cost |
|-----------|----------|------|
| PCA9685 | 16-channel servo driver | $5-10 |
| Level Shifter | 3.3V→5V logic | $2-5 |
| Battery Pack | Portable power | $10-20 |
| 3D Printed Case | Enclosure | $5-15 |
| Enclosure Box | Project box | $5-10 |

### Pinout Diagram

#### ESP32 Pin Configuration

```
┌────────────────────────────────────────────────────────────────────┐
│                         ESP32 DEVKIT V1                            │
│                                                                    │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│   │     GND  │  │      3V3 │  │     EN   │  │    GND   │           │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│                                                                    │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│   │    SVP   │  │    SVN   │  │    IO34  │  │    IO35  │           │
│   │  (VP)    │  │  (VN)    │  │ (ADC4)   │  │ (ADC5)   │           │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│                                                                    │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│   │    IO32  │  │    IO33  │  │    IO25  │  │    IO26  │           │
│   │   (T0)   │  │   (T1)   │  │   (T2)   │  │   (T3)   │           │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│         │                                                          │
│         │         ╔═══════════════════════════════════════╗        │
│         └─────────║  I2S MEMS MICROPHONE (INMP441)        ║        │
│                   ║                                       ║        │
│         ┌─────────║  PIN: WS   → ESP32 GPIO 25            ║        │
│         │         ║  PIN: SCK  → ESP32 GPIO 26            ║        │
│         │         ║  PIN: SD   → ESP32 GPIO 27            ║        │
│         │         ║  PIN: VCC → ESP32 3V3                 ║        │
│         │         ║  PIN: GND → ESP32 GND                 ║        │
│         └─────────╚═══════════════════════════════════════╝        │
│                                                                    │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│   │    IO27  │  │    IO14  │  │    IO13  │  │    IO12  │           │
│   │          │  │          │  │          │  │          │           │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│         │              │             │             │               │
│         │              │             │             │               │
│         ▼              ▼             ▼             ▼               │
│       SERVO 1        SERVO 2      SERVO 3       SERVO 4            │
│       (GPIO 27)     (GPIO 14)    (GPIO 13)    (GPIO 12)            │
│                                                                    │
│   Power: 5V → Servo VCC, 3.3V → ESP32                              │
│   Ground: Common ground for all components                         │
└────────────────────────────────────────────────────────────────────┘
```

### Wiring Instructions

#### Step 1: I2S Microphone

```
INMP441 Pin    →    ESP32 Pin
─────────────────────────────────
VCC           →    3.3V
GND           →    GND
WS            →    GPIO 25 (I2S WS)
SCK           →    GPIO 26 (I2S SCK)
SD            →    GPIO 27 (I2S SD)
LR            →    3.3V (Left channel)
```

**Note**: Some microphones have SEL pin - connect to GND for left channel mode.

#### Step 2: Servo Motors

```
SG90 Servo     →    ESP32 Pin
─────────────────────────────────
Red (VCC)      →    5V (Use external supply if >2 servos)
Brown (GND)    →    GND
Orange (SIG)   →    GPIO 13, 14, 27, 26 (configurable)
```

**Warning**: Do not power more than 2 servos directly from ESP32 5V. Use external 5V 2A supply for 4 servos.

#### Complete Wiring Diagram

```
                    ┌─────────────────┐
                    │   5V 2A Power   │
                    │    Supply       │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
        │ SERVO 1 │   │ SERVO 2 │   │ SERVO 3 │   | SERVO 4 |
        │ GPIO13  │   │ GPIO14  │   │ GPIO27  │   │ GPIO26  |
        └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘
             │             │             │             │
             │             │             │             │
    ┌────────┴─────────────┴─────────────┴─────────────┴───┐
    │                      ESP32                           │
    │                                                      │
    │    ┌─────────────────────────────────────────────┐   │
    │    │         I2S MEMS Microphone                 │   │
    │    │  GPIO 25 (WS)  GPIO 26 (SCK)  GPIO 27 (SD)  │   │
    │    └─────────────────────────────────────────────┘   │
    │                                                      │
    └──────────────────────────────────────────────────────┘
```

---

## Installation

### Option 1: ESP32 (Recommended)

The ESP32 firmware includes the embedded web app. Just flash and go!

#### Prerequisites

- [PlatformIO](https://platformio.org/) (or Arduino IDE with ESP32 board)
- ESP32 Dev Board
- USB Cable

#### Upload Firmware

**Using PlatformIO:**

```bash
# Navigate to firmware directory
cd omnisound/firmware/esp32

# Build and upload
pio run upload

# Or using Arduino IDE:
# 1. Open src/main.cpp
# 2. Select Board: "ESP32 Dev Module"
# 3. Upload
```

**Configuration:**

Edit `src/main.cpp` before building:

```cpp
// Required configurations
#define DEVICE_NAME "OMNISOUND"     // WiFi AP name
#define WS_PORT 81                   // WebSocket port
#define SAMPLE_RATE 16000           // Audio sample rate
#define MOTOR_COUNT 4               // Number of servos
const uint8_t MOTOR_PINS[] = {13, 14, 27, 26};  // Servo pins
```

#### Post-Flash Setup

1. Power on ESP32
2. Connect to WiFi: `OMNISOUND` (password: `12345678`)
3. Open browser to `http://192.168.1.1` or `http://omnisound.local`
4. That's it! 🎉

---

### Option 2: Arduino (Uno/Nano/Mega)

For simpler projects without WiFi.

#### Hardware Required

- Arduino Uno/Nano/Mega
- USB Serial connection
- 4x Servo motors
- 5V 2A power supply

#### Upload Sketch

```bash
# Using Arduino IDE
# 1. Open omnisound/firmware/arduino/omnisound_arduino.ino
# 2. Select Board: Arduino Uno/Nano/Mega
# 3. Upload
```

#### Serial Commands

```
M0 F440 A50     → Set Motor 0, freq 440Hz, amplitude 50%
A0 90           → Set Motor 0 angle to 90°
?               → Query configuration
PING            → Test connection
ENABLE 0        → Enable Motor 0
DISABLE 0       → Disable Motor 0
```

---

### Option 3: Raspberry Pi Pico (MicroPython)

For projects requiring Python flexibility.

#### Setup

```bash
# Install MicroPython
# https://micropython.org/download/rp2/

# Upload omnisound/firmware/raspberry_pi_pico/omnisound_pico.py
ampy put omnisound_pico.py main.py
```

---

### Option 4: Full React GUI (Optional)

For a more comprehensive interface, build the separate React app.

```bash
cd omnisound/gui

# Install dependencies
npm install

# Development server
npm run dev

# Production build
npm run build

# Output in dist/ folder - host anywhere
```

---

## Usage Guide

### First Time Setup

1. **Power On ESP32**
   - Connect USB or 5V power supply
   - Wait for boot (LED blinks)

2. **Connect to WiFi**
   - Scan for WiFi networks
   - Connect to "OMNISOUND"
   - Password: `12345678`

3. **Open Web App**
   - A popup may appear automatically (captive portal)
   - Or visit: `http://192.168.1.1`

4. **Start Audio Processing**
   - Click "Start" button
   - Allow microphone access when prompted
   - Play music or speak

5. **Watch Motors Move**
   - Motors respond to audio frequencies
   - Motor 0: Bass (20-200 Hz)
   - Motor 1: Mids (200-800 Hz)
   - Motor 2: Highs (800-8000 Hz)
   - Motor 3: Beat detection

### Controls

| Control | Function |
|---------|----------|
| **Start/Stop** | Toggle audio processing |
| **Sensitivity** | Adjust response threshold |
| **Waveform** | Real-time waveform display |
| **Spectrum** | FFT frequency visualization |
| **Motor Sliders** | Manual angle control |

### Testing Motors

```cpp
// Via WebSocket (JavaScript console)
ws.send('{"m0":135,"m1":90,"m2":45,"m3":90}');

// Via Serial (Arduino)
M0 F1000 A100
A0 90
```

---

## Configuration

### Motor Configuration

Default frequency mapping:

| Motor | Name | Frequency Range | Mode |
|-------|------|-----------------|------|
| M0 | Bass | 20-200 Hz | frequency_band |
| M1 | Mid | 200-800 Hz | frequency_band |
| M2 | High | 800-8000 Hz | frequency_band |
| M3 | Beat | N/A | beat |

### Customizing in Code

```cpp
// In main.cpp - Motor frequency ranges
const float MOTOR_FREQ_MIN[] = {20, 200, 800, 0};
const float MOTOR_FREQ_MAX[] = {200, 800, 8000, 0};

// Angle ranges
const int ANGLE_MIN[] = {45, 45, 45, 90};
const int ANGLE_MAX[] = {135, 135, 135, 135};
```

### WebSocket Commands

```json
// Set individual motor
{"m0": 90, "m1": 45, "m2": 135, "m3": 90}

// Set via array
{"motors": [90, 45, 135, 90}

// Query status
{"cmd": "get_status"}

// Start processing
{"cmd": "start"}

// Stop processing
{"cmd": "stop"}
```

---

## API Reference

### WebSocket Events

#### ESP32 → Device

| Event | Format | Description |
|-------|--------|-------------|
| `binary` | `Int16Array` | Raw PCM audio |
| `status` | JSON | Motor positions, counters |
| `config` | JSON | Device configuration |

#### Device → ESP32

| Command | Format | Description |
|---------|--------|-------------|
| `{"m0":90}` | JSON | Set motor 0 angle |
| `{"motors":[...]}` | JSON | Set all motors |
| `{"cmd":"start"}` | JSON | Start streaming |
| `{"cmd":"ping"}` | JSON | Ping/pong |

### Serial Protocol (Arduino)

| Command | Example | Description |
|---------|---------|-------------|
| `M{id} F{freq} A{amp}` | `M0 F440 A50` | Set motor frequency/amplitude |
| `A{id} {angle}` | `A0 90` | Set motor angle directly |
| `?` | `?` | Query config |
| `PING` | `PING` | Test connection |

### HTTP Endpoints (ESP32)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main web app |
| `/app.js` | GET | Embedded JavaScript |
| `/style.css` | GET | Embedded styles |
| `/status` | GET | JSON status |
| `/stream` | GET | Server-Sent Events |

---

## Troubleshooting

### Common Issues

#### Issue: ESP32 Not Connecting to WiFi

**Symptoms**: No WiFi network "OMNISOUND" visible

**Solutions**:
1. Check serial monitor for boot messages
2. Verify power supply (needs 5V 2A minimum)
3. Press EN/RST button to reboot
4. Check GPIO 0 is not grounded (causes flash mode)

---

#### Issue: Microphone Not Working

**Symptoms**: No audio data, silent motors

**Solutions**:
1. Verify I2S wiring (WS→25, SCK→26, SD→27)
2. Check 3.3V power to microphone
3. Ensure microphone is in left-channel mode (SEL→GND)
4. Test with: `pio device monitor` to see raw data

---

#### Issue: Motors Not Moving

**Symptoms**: Motors stuck at 90°

**Solutions**:
1. Check servo power (5V sufficient?)
2. Verify servo signal wires
3. Try manual test: `A0 45` then `A0 135`
4. Check servo grounds are connected

---

#### Issue: High Latency

**Symptoms**: Motors respond slowly (>100ms)

**Solutions**:
1. Reduce `AUDIO_BUFFER_SIZE` in code
2. Increase sample rate
3. Use smaller FFT size
4. Check WiFi signal strength

---

#### Issue: WebSocket Disconnects

**Symptoms**: "Disconnected" status

**Solutions**:
1. Move closer to ESP32
2. Reduce audio buffer size
3. Check for interference
4. Verify no firewall blocking port 81

---

### Debug Mode

Enable debug output in `main.cpp`:

```cpp
#define DEBUG true
Serial.begin(115200);
```

View with: `pio device monitor`

---

## Development

### Project Structure

```
omnisound/
├── README.md                    # This file
│
├── core/                        # Python engine (optional)
│   ├── __init__.py
│   ├── engine.py               # Main engine
│   ├── audio_pipeline.py       # Audio processing
│   ├── motor_controller.py     # Motor control
│   ├── config_manager.py       # Configuration
│   ├── event_bus.py            # Event system
│   └── plugin_registry.py      # Plugin system
│
├── plugins/                     # Plugin modules
│   ├── hardware/               # Hardware backends
│   │   ├── simulation.py       # Software simulation
│   │   ├── esp32_wifi.py       # ESP32 WiFi
│   │   ├── arduino_serial.py   # Arduino Serial
│   │   └── raspberry_pi_gpio.py # Raspberry Pi
│   ├── audio_sources/          # Audio inputs
│   │   ├── microphone.py       # System mic
│   │   ├── file_player.py      # Audio files
│   │   └── system_audio.py    # System audio
│   └── processors/             # Audio processors
│       ├── fft_analyzer.py     # FFT
│       ├── beat_detector.py    # Beat detection
│       └── band_splitter.py    # Frequency bands
│
├── gui/                        # React web interface
│   ├── src/
│   │   ├── components/         # UI components
│   │   ├── pages/             # Page views
│   │   ├── api/               # API clients
│   │   ├── store.js           # State management
│   │   └── App.jsx            # Main app
│   └── package.json
│
└── firmware/                   # Microcontroller code
    ├── esp32/                 # ESP32 (PlatformIO)
    │   └── src/main.cpp       # Main firmware
    ├── arduino/               # Arduino
    │   └── omnisound_arduino.ino
    └── raspberry_pi_pico/     # Raspberry Pi Pico
        └── omnisound_pico.py
```

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

### Adding New Hardware Support

1. Create new plugin in `plugins/hardware/`
2. Implement base hardware interface
3. Add to plugin registry

### Adding New Audio Sources

1. Create source in `plugins/audio_sources/`
2. Implement audio stream interface
3. Register in engine

---

### 🛒 Hardware Shopping List

| Item | AliExpress | Amazon | Adafruit |
|------|-----------|--------|----------|
| ESP32 Dev Board | ~$2.50 | ~$8 | ~$10 |
| SG90 Servo (4-pack) | ~$4 | ~$10 | — |
| INMP441 Microphone | ~$2 | ~$6 | — |
| 5V 3A Power Supply | ~$5 | ~$8 | — |
| 100µF Capacitor (10-pack) | ~$2 | ~$5 | — |
| Jumper Wires | ~$2 | ~$6 | — |
| Breadboard | ~$2 | ~$5 | — |

**Total (ESP32 build): ~$35 USD**

### 🔧 CLI Reference

```bash
python omnisound.py                    # Start with defaults
python omnisound.py --port 9000        # Custom port
python omnisound.py --host 0.0.0.0    # Bind to all interfaces (LAN access)
python omnisound.py --simulation       # Force simulation (no hardware)
python omnisound.py --no-browser       # Don't auto-open browser
python omnisound.py --config ./my.json # Use custom config file
python omnisound.py --reset            # Reset config to defaults
python omnisound.py --diagnose         # Print system capability report
python omnisound.py --version          # Print version info
```

### 🐳 Docker

```bash
docker compose up                 # Start with Docker
docker compose --profile dev up   # Development mode with hot reload
```

### 🧪 Testing

```bash
pip install -r requirements-dev.txt
pytest tests/                     # All tests
pytest tests/unit/                # Unit tests only
pytest tests/ --cov=core          # With coverage
```

### 🔌 Plugin Development

Creating a hardware plugin requires just 15 lines minimum:

```python
from plugins.hardware import BaseHardware

class MyHardware(BaseHardware):
    plugin_id = "my_hardware"
    plugin_name = "My Custom Board"

    async def send_command(self, command):
        # Send command to your hardware
        pass
```

Config schemas auto-generate settings forms in the GUI. See [Creating a Hardware Plugin](docs/plugins/creating-hardware-plugin.md) for the full guide.

### 🗺️ Roadmap

**v1.1.0 (Q1 2025)**
- [ ] WebSocket command batching for ultra-low latency
- [ ] CREPE neural pitch detection
- [ ] Pico W wireless support
- [ ] Homebrew formula for macOS

**v1.2.0 (Q2 2025)**
- [ ] Mobile app (React Native) as companion controller
- [ ] Cloud sync for sequences via optional backend
- [ ] VST plugin bridge (control motors from DAW)
- [ ] Motor calibration wizard with auto-tuning

**v2.0.0 (Future)**
- [ ] Stepper motor support
- [ ] Multi-server mesh (many PCs → many MCUs)
- [ ] Edge ML: on-device beat detection on ESP32

---

## FAQ

### Q: Why do motors move when there's no music?

**A**: The system responds to all audio including ambient noise. Adjust the sensitivity slider or use a lower threshold in code.

### Q: Can I use more than 4 motors?

**A**: Yes! Change `MOTOR_COUNT` in code and add more servo pins. For >4 servos, use PCA9685 servo driver.

### Q: Can I use this with speakers instead of servos?

**A**: The architecture is designed for servos, but you could add a DAC output for speaker control. See the Python engine for more options.

### Q: Does this work without WiFi?

**A**: The ESP32 creates its own WiFi network - no internet required. For offline use, upload the firmware and connect to the AP.

### Q: What's the latency?

**A**: ~30-50ms typical. Depends on audio buffer size and WiFi quality.

### Q: Can I use Bluetooth instead of WiFi?

**A**: BLE support is optional in the firmware. Currently WiFi is the primary connection method.

### Q: How do I power this outdoors?

**A**: Use a USB power bank (5V 2A+) or LiPo battery with protection circuit.

### Q: Can I control this from a computer?

**A**: Yes! Connect to the same WiFi and open the web interface, or use the Python engine for direct control.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2024 OMNISOUND

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

- Report bugs via [GitHub Issues](https://github.com/omnisound-project/omnisound/issues)
- Join discussions on [GitHub Discussions](https://github.com/omnisound-project/omnisound/discussions)
- Check out [good first issues](https://github.com/omnisound-project/omnisound/labels/good%20first%20issue) to get started

---

## 🙏 Acknowledgments

This project builds on the incredible work of many open-source communities:

- [FastAPI](https://fastapi.tiangolo.com/) — Modern Python web framework
- [librosa](https://librosa.org/) — Audio and music analysis
- [sounddevice](https://python-sounddevice.readthedocs.io/) — Audio I/O
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — YouTube downloader
- [ESP32Servo](https://github.com/madhephaestus/ESP32Servo) — ESP32 servo library
- [WebSockets](https://github.com/Links2004/arduinoWebSockets) — Arduino WebSocket library
- [React](https://react.dev/) — UI framework
- [Vite](https://vitejs.dev/) — Frontend build tool
- [Tailwind CSS](https://tailwindcss.com/) — Utility-first CSS
- [Zustand](https://github.com/pmndrs/zustand) — State management
- [bleak](https://github.com/hbldh/bleak) — BLE library
- [mido](https://mido.readthedocs.io/) — MIDI library
- The [Arduino](https://www.arduino.cc/) and [ESP-IDF](https://docs.espressif.com/projects/esp-idf/) communities

---

## 📄 License

MIT © 2024 OmniSound Project — see [LICENSE](LICENSE)

---

<div align="center">

**Made with ♥ by the community**

*Create something amazing today!*

</div>
