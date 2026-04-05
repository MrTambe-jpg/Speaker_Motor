# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- CODE_OF_CONDUCT.md (Contributor Covenant v2.1)
- pyproject.toml for modern Python packaging
- requirements-dev.txt for development dependencies
- GitHub Issue Templates (bug report, hardware support)
- GitHub Pull Request Template
- MkDocs documentation site configuration
- Docker and docker-compose support
- Comprehensive test suite (unit + integration tests)
- Conventional Commits format for commit messages
- Black + Ruff linting configuration
- CI workflow for docs deployment

### Changed
- Improved .gitignore (cleaner, more comprehensive)
- Updated CONTRIBUTING.md with plugin development guides
- Updated README.md with shopping list, CLI reference, Docker, testing, roadmap
- Enhanced SECURITY.md with GitHub Security Advisories link

## [1.0.0] - 2024-01-15

### Added
- **Thin Client Architecture**: ESP32 now only handles audio capture and servo control
- **Embedded Web App**: Full UI served directly from ESP32 firmware
- **WebSocket Communication**: Binary audio streaming and text commands
- **Web Audio API**: FFT analysis and beat detection on connected device
- **Responsive UI**: Works on mobile and desktop browsers
- **Multiple Hardware Support**:
  - ESP32 (WiFi/WebSocket)
  - Arduino (Serial)
  - Raspberry Pi Pico (MicroPython)
- **Plugin System**: Modular audio sources and processors
- **Python Engine**: Full PC-based processing option

### Changed
- **Memory Optimization**: Reduced ESP32 RAM usage from ~120KB to ~10KB
- **Power Efficiency**: Minimal MCU processing extends battery life
- **Latency**: Reduced to ~30-50ms round-trip

### Fixed
- I2S microphone initialization
- Servo PWM control timing
- WebSocket binary data handling
- Captive portal DNS configuration

### Removed
- On-device FFT processing (now on connected device)
- Heavy JSON parsing (simplified protocol)
- Large audio buffers

---

## [0.2.0] - 2023-12-01

### Added
- Beat detection with visual feedback
- Frequency band splitting (Bass/Mid/High)
- Motor configuration UI
- Settings page with audio source selection

### Changed
- Improved motor smoothing algorithm
- Better frequency range mapping

---

## [0.1.0] - 2023-11-01

### Added
- Initial ESP32 firmware with basic servo control
- WebSocket server for motor commands
- Basic HTML visualization
- Arduino sketch support

---

## Future Plans

### Planned Features
- [ ] BLE fallback for lower power consumption
- [ ] Multi-room synchronization
- [ ] Spotify/YouTube integration
- [ ] Recording and playback
- [ ] Multiple ESP32 mesh network
- [ ] Custom motor driver support (PCA9685)
- [ ] Audio file playback from SD card

---

## Version History

| Version | Date | Status |
|---------|------|--------|
| 1.0.0 | 2024-01-15 | Current |
| 0.2.0 | 2023-12-01 | Deprecated |
| 0.1.0 | 2023-11-01 | Deprecated |

---

## Migration Guides

### Upgrading from 0.x to 1.0

The 1.0 release introduced significant architectural changes:

1. **Audio Processing Location**: All FFT/beat detection now happens on your phone/computer, not the ESP32
2. **WebSocket Protocol**: Use the new compact command format
3. **UI Access**: Visit `http://192.168.1.1` instead of local server

### API Changes (0.x → 1.0)

```javascript
// Old format
{ "command": "set_motor", "motor": 0, "angle": 90 }

// New format
{ "m0": 90 }
```

---

## Deprecation Notices

- Python 2.7 support was removed in v0.2.0
- Legacy serial protocol documentation was moved to deprecated folder in v1.0