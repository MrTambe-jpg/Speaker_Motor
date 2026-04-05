# Contributing to OMNISOUND

Thank you for your interest in contributing to OMNISOUND! This document provides guidelines for contributing to this project.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Coding Standards](#coding-standards)
5. [Pull Request Process](#pull-request-process)
6. [Types of Contributions](#types-of-contributions)
7. [Documentation](#documentation)
8. [Testing](#testing)
9. [Adding a Hardware Plugin](#adding-a-hardware-plugin)
10. [Adding an Audio Source Plugin](#adding-an-audio-source-plugin)

---

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to maintain a respectful and inclusive environment.

**Summary:** Be welcoming, respectful, and constructive. Harassment, trolling, and personal attacks are not tolerated.

**Enforcement:** Report violations to conduct@omnisound-project.org. All reports are handled confidentially.

## Getting Started

### Prerequisites

Before contributing, ensure you have:

1. **Git** installed on your system
2. **Python 3.9+** (for Python engine)
3. **Node.js 18+** (for GUI development)
4. **PlatformIO** (for ESP32 firmware)
5. **Arduino IDE** (optional, for Arduino firmware)

### Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork

git clone https://github.com/YOUR_USERNAME/omnisound.git
cd omnisound

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/omnisound.git
```

### Setting Up Development Environment

#### Python Engine Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dev dependencies (includes core deps + testing tools)
pip install -r requirements-dev.txt
```

#### GUI Setup

```bash
cd gui
npm install
```

#### ESP32 Firmware Setup

```bash
# Install PlatformIO
# https://platformio.org/install

# Build firmware
cd firmware/esp32
pio run build
```

---

## Development Workflow

### 1. Create a Branch

Always create a new branch for your feature or fix:

```bash
# Update your fork
git fetch upstream
git checkout main
git merge upstream/main

# Create new branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
# or
git checkout -b docs/improve-setup-guide
```

### 2. Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/) format:

```
type: short description

Optional longer description

Optional footer (e.g., Closes #123)
```

**Types:**
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `chore:` — Maintenance, config, build
- `refactor:` — Code refactoring (no behavior change)
- `test:` — Adding or updating tests
- `ci:` — CI/CD changes
- `perf:` — Performance improvements

**Examples:**
```
feat: add CREPE pitch detection processor
fix: resolve numpy import order in motor_controller
docs: update wiring diagram for ESP32-S3
test: add unit tests for ConfigManager
ci: add docs deployment workflow
```

### 3. Keep Your Fork Updated

```bash
# Fetch from upstream
git fetch upstream

# Rebase on main
git rebase upstream/main

# Force push (if needed)
git push origin your-branch-name --force
```

### 4. Submit a Pull Request

1. Push your branch to your fork
2. Open a Pull Request on GitHub
3. Fill in the PR template
4. Wait for review

---

## Coding Standards

### Python

- Use [black](https://black.readthedocs.io/) formatter
- Use [ruff](https://docs.astral.sh/ruff/) linter
- Google-style docstrings
- Type hints where possible
- Maximum line length: 100 characters

```bash
# Format
black .

# Lint
ruff check .

# Type check (optional)
mypy core/
```

```python
# Good
def calculate_motor_angle(frequency: float, min_freq: float, max_freq: float) -> float:
    """Calculate motor angle based on frequency.

    Args:
        frequency: Current frequency in Hz.
        min_freq: Minimum frequency threshold.
        max_freq: Maximum frequency threshold.

    Returns:
        Motor angle in degrees (0-180).
    """
    normalized = (frequency - min_freq) / (max_freq - min_freq)
    return int(45 + normalized * 90)
```

### C++ (ESP32/Arduino)

- Follow [Arduino Coding Standards](https://www.arduino.cc/en/Reference/StyleGuide)
- Use 4 spaces for indentation
- Maximum line length: 100 characters
- Comment complex code sections
- Use meaningful variable names

```cpp
// Good
const uint8_t MOTOR_PIN_ARRAY[] = {13, 14, 27, 26};

// Avoid
int p[] = {13, 14, 27, 26};
```

### JavaScript/React

- Use functional components
- Follow component naming conventions (PascalCase)
- Keep components focused (single responsibility)

```jsx
// Good
function MotorArcWidget({ motor, config }) {
  return (
    <div className="motor-arc">
      <SVGComponent />
    </div>
  );
}

// Avoid
function motorArcWidget(props) {
  return <div>...</div>;
}
```

### CSS

- Use Tailwind CSS classes when possible
- Follow BEM naming for custom classes
- Keep styles scoped to components

---

## Pull Request Process

### Before Submitting

1. **Run tests** — `pytest tests/`
2. **Format code** — `black .`
3. **Lint** — `ruff check .`
4. **Update docs** — README, CHANGELOG if needed
5. **Review your changes** — no debug code, no console logs

### PR Checklist

- [ ] Tests pass (`pytest tests/`)
- [ ] Code formatted (`black .`)
- [ ] Linted (`ruff check .`)
- [ ] CHANGELOG.md updated
- [ ] Docs updated (if new feature)
- [ ] New hardware plugin: firmware sketch included
- [ ] New audio source: availability check implemented
- [ ] Breaking change? (version bump needed)

See [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md) for the full template.

---

## Types of Contributions

### Ways to Contribute

- **Code** — New features, bug fixes, performance improvements
- **Docs** — Tutorials, API reference, hardware guides
- **Hardware Testing** — Test on physical boards, report results
- **Bug Reports** — Detailed reports with reproduction steps
- **Feature Requests** — Clear descriptions with use cases

### Areas Needing Contributions

1. **New Hardware Support** — Teensy, STM32, additional servo drivers
2. **Audio Processing** — Better beat detection, pitch tracking, CREPE integration
3. **Web Interface** — New dashboard widgets, mobile optimizations
4. **Documentation** — Video tutorials, translation, wiring diagrams
5. **Testing** — More unit tests, integration tests, hardware-in-loop tests

---

## Documentation

### Code Documentation

- Comment complex logic
- Document public APIs with docstrings
- Update function/class docstrings when behavior changes

### README Updates

Update the README when:
- Adding new features
- Changing configuration
- Adding new hardware support
- Fixing outdated information

---

## Testing

### Python Tests

```bash
# All tests
pytest tests/

# Unit tests only
pytest tests/unit/

# With coverage
pytest tests/ --cov=core --cov=plugins

# Specific test file
pytest tests/unit/test_config_manager.py
```

**Requirement:** New features need unit tests. Bug fixes should include regression tests.

### ESP32 Firmware

```bash
# Build
pio run build

# Upload
pio run upload

# Monitor
pio device monitor
```

### GUI

```bash
# Development
npm run dev

# Build
npm run build
```

---

## Adding a Hardware Plugin

1. Create a new file in `plugins/hardware/`
2. Inherit from `BaseHardware`
3. Implement required methods: `initialize()`, `send_command()`, `ping()`, `shutdown()`
4. Define `plugin_id`, `plugin_name`, and `get_config_schema()`
5. Add availability check in `is_available()`

```python
from plugins.hardware import BaseHardware

class MyBoard(BaseHardware):
    plugin_id = "my_board"
    plugin_name = "My Custom Board"

    def is_available(self):
        return True

    def get_config_schema(self):
        return {
            "port": {"type": "string", "default": "/dev/ttyUSB0"},
            "baud_rate": {"type": "int", "default": 115200},
        }

    async def initialize(self, config):
        self.port = config.get("port", "/dev/ttyUSB0")
        self.baud_rate = config.get("baud_rate", 115200)

    async def send_command(self, command):
        # Send to hardware
        pass

    async def ping(self):
        return True

    async def shutdown(self):
        pass
```

---

## Adding an Audio Source Plugin

1. Create a new file in `plugins/audio_sources/`
2. Inherit from `BaseAudioSource`
3. Implement: `initialize()`, `start_stream()`, `stop_stream()`, `get_audio_chunk()`, `get_sample_rate()`
4. Define `plugin_id`, `plugin_name`, and `get_config_schema()`

```python
from plugins.audio_sources import BaseAudioSource

class MySource(BaseAudioSource):
    plugin_id = "my_source"
    plugin_name = "My Audio Source"

    def is_available(self):
        return True

    def get_config_schema(self):
        return {
            "url": {"type": "string", "default": ""},
        }

    async def initialize(self, config):
        self.url = config.get("url", "")

    async def start_stream(self):
        pass

    async def stop_stream(self):
        pass

    async def get_audio_chunk(self):
        # Return numpy array of audio samples
        return None

    def get_sample_rate(self):
        return 44100
```

---

## Questions?

If you have questions, feel free to:

1. Open a [GitHub Discussion](https://github.com/omnisound-project/omnisound/discussions)
2. Ask in the [issue tracker](https://github.com/omnisound-project/omnisound/issues)
3. Contact maintainers directly

Thank you for contributing!