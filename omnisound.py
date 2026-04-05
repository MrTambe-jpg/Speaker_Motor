"""
OMNISOUND - Universal Motor Speaker System
Entry point script
"""

import asyncio
import argparse
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.engine import OmniSoundEngine
from core.config_manager import reset_config_manager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="OMNISOUND - Universal Motor Speaker System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=None,
        help="Port to run server on (default: from config or 8000)",
    )

    parser.add_argument(
        "--host",
        "-H",
        type=str,
        default=None,
        help="Host to bind to (default: from config or 0.0.0.0)",
    )

    parser.add_argument(
        "--no-browser", "-n", action="store_true", help="Do not open browser automatically"
    )

    parser.add_argument("--config", "-c", type=str, default=None, help="Path to config file")

    parser.add_argument(
        "--simulation", "-s", action="store_true", help="Force simulation mode (no hardware)"
    )

    parser.add_argument("--reset", action="store_true", help="Reset configuration to defaults")

    parser.add_argument("--diagnose", "-d", action="store_true", help="Run diagnostics and exit")

    parser.add_argument(
        "--log-level",
        "-l",
        type=str,
        choices=["debug", "info", "warning", "error"],
        default="info",
        help="Log level (default: info)",
    )

    return parser.parse_args()


def run_diagnostics():
    """Run system diagnostics."""
    import platform

    print("\n" + "=" * 60)
    print("OMNISOUND SYSTEM DIAGNOSTICS")
    print("=" * 60)

    # System info
    print("\n--- System Information ---")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Architecture: {platform.machine()}")
    print(f"Python: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")

    # Check required packages
    print("\n--- Required Packages ---")
    required_packages = [
        "fastapi",
        "uvicorn",
        "websockets",
        "numpy",
        "scipy",
        "pydantic",
        "sounddevice",
        "soundfile",
        "pydub",
        "librosa",
        "pyserial",
    ]

    for pkg in required_packages:
        try:
            __import__(pkg.replace("-", "_"))
            print(f"  {pkg}: OK")
        except ImportError:
            print(f"  {pkg}: NOT INSTALLED")

    # Check optional packages
    print("\n--- Optional Packages ---")
    optional_packages = ["websockets", "bleak", "zeroconf", "RPi.GPIO", "pigpio"]

    for pkg in optional_packages:
        try:
            __import__(pkg.replace("-", "_"))
            print(f"  {pkg}: OK")
        except ImportError:
            print(f"  {pkg}: NOT INSTALLED (optional)")

    # Check audio devices
    print("\n--- Audio Devices ---")
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                print(f"  Input [{i}]: {dev['name']}")
            if dev["max_output_channels"] > 0:
                print(f"  Output [{i}]: {dev['name']}")
    except Exception as e:
        print(f"  Error listing audio devices: {e}")

    # Check serial ports
    print("\n--- Serial Ports ---")
    try:
        import serial.tools.list_ports

        ports = list(serial.tools.list_ports.comports())
        if ports:
            for port in ports:
                print(f"  {port.device}: {port.description}")
        else:
            print("  No serial ports found")
    except ImportError:
        print("  pyserial not installed")

    print("\n" + "=" * 60)
    print("DIAGNOSTICS COMPLETE")
    print("=" * 60 + "\n")


async def main_async():
    """Main async entry point."""
    args = parse_args()

    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))

    # Run diagnostics if requested
    if args.diagnose:
        run_diagnostics()
        return

    # Reset config if requested
    if args.reset:
        config = reset_config_manager(args.config)
        config.reset_to_defaults()
        print("Configuration reset to defaults")

    # Create engine
    engine = OmniSoundEngine(config_path=args.config)

    # Override settings from command line
    if args.host:
        engine.config.set("system.host", args.host)
    if args.port:
        engine.config.set("system.port", args.port)
    if args.no_browser:
        engine.config.set("system.auto_open_browser", False)
    if args.simulation:
        engine.config.set("hardware.active_plugin", "simulation")

    # Initialize
    await engine.initialize()

    # Get settings
    host = engine.config.get("system.host", "0.0.0.0")
    port = engine.config.get("system.port", 8000)
    open_browser = engine.config.get("system.auto_open_browser", True)

    # Run server
    engine.run(host=host, port=port, open_browser=open_browser)


def main():
    """Main entry point."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
