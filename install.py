"""
OMNISOUND Universal Installer
Detects OS, installs dependencies, and sets up the system
"""

import os
import sys
import platform
import subprocess
import shutil
from typing import List, Tuple, Optional

# Banner
BANNER = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ██████╗ ███╗   ███╗███╗   ██╗██╗   ██╗███████╗         ║
║  ██╔═══██╗████╗ ████║████╗  ██║██║   ██║██╔════╝         ║
║  ██║   ██║██╔████╔██║██╔██╗ ██║██║   ██║███████╗         ║
║  ██║   ██║██║╚██╔╝██║██║╚██╗██║██║   ██║╚════██║         ║
║  ╚██████╔╝██║ ╚═╝ ██║██║ ╚████║╚██████╔╝███████║         ║
║   ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝         ║
║                                                           ║
║         Universal Motor Speaker System                     ║
║              Installer v1.0.0                             ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""


def run_command(
    cmd: List[str], check: bool = True, cwd: Optional[str] = None
) -> Tuple[int, str, str]:
    """Run a command and return result."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=cwd)
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"


def check_python_version() -> Tuple[bool, str]:
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        return False, f"Python 3.9+ required, found {version.major}.{version.minor}.{version.micro}"
    return True, f"Python {version.major}.{version.minor}.{version.micro}"


def detect_os() -> Tuple[str, str]:
    """Detect the operating system."""
    system = platform.system()
    release = platform.release()

    if system == "Linux":
        # Detect distribution
        try:
            with open("/etc/os-release", "r") as f:
                content = f.read()
                if "Ubuntu" in content:
                    return "linux", "ubuntu"
                elif "Debian" in content:
                    return "linux", "debian"
                elif "Fedora" in content:
                    return "linux", "fedora"
                elif "Arch" in content:
                    return "linux", "arch"
        except FileNotFoundError:
            pass
        return "linux", "unknown"

    return system.lower(), release


def find_package_manager() -> Optional[str]:
    """Find available package manager."""
    managers = {
        "apt": ["apt", "apt-get"],
        "dnf": ["dnf", "yum"],
        "pacman": ["pacman"],
        "brew": ["brew"],
        "choco": ["choco"],
        "winget": ["winget"],
    }

    for name, commands in managers.items():
        for cmd in commands:
            if shutil.which(cmd):
                return name

    return None


def install_system_dependencies(os_type: str, distro: str = None) -> bool:
    """Install system-level dependencies."""
    print("\n📦 Checking system dependencies...")

    package_manager = find_package_manager()

    if os_type == "linux":
        packages = ["portaudio19-dev", "ffmpeg", "libavcodec-extra"]

        if package_manager == "apt":
            print("  Installing via apt...")
            cmd = ["sudo", "apt", "update"]
            run_command(cmd, check=False)
            cmd = ["sudo", "apt", "install", "-y"] + packages
            code, _, err = run_command(cmd)
            return code == 0

        elif package_manager == "dnf":
            print("  Installing via dnf...")
            cmd = ["sudo", "dnf", "install", "-y"] + packages
            code, _, err = run_command(cmd)
            return code == 0

        elif package_manager == "pacman":
            print("  Installing via pacman...")
            cmd = ["sudo", "pacman", "-S", "--noconfirm"] + packages
            code, _, err = run_command(cmd)
            return code == 0

    elif os_type == "darwin":
        print("  Checking for Homebrew packages...")
        if shutil.which("brew"):
            cmd = ["brew", "install", "portaudio", "ffmpeg"]
            run_command(cmd, check=False)
        else:
            print("  ⚠️  Homebrew not found. Install from: https://brew.sh")

    elif os_type == "windows":
        print("  Windows: No system dependencies needed")
        print("  Note: sounddevice may require Visual C++ redistributable")

    return True


def install_python_packages(dev_mode: bool = False) -> bool:
    """Install Python packages from requirements.txt."""
    print("\n📦 Installing Python packages...")

    # Check for pip
    if not shutil.which("pip"):
        print("  ❌ pip not found")
        return False

    # Upgrade pip first
    print("  Upgrading pip...")
    code, _, err = run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    if code != 0:
        print(f"  ⚠️  Could not upgrade pip: {err}")

    # Install requirements
    print("  Installing requirements...")
    cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
    code, stdout, err = run_command(cmd)

    if code != 0:
        print(f"  ❌ Error installing requirements: {err}")
        return False

    print("  ✅ Python packages installed")
    return True


def install_optional_packages() -> None:
    """Offer to install optional packages."""
    print("\n📦 Optional Packages:")

    optional = {
        "Raspberry Pi GPIO": ["RPi.GPIO", "pigpio"],
        "MIDI Support": ["python-rtmidi"],
        "CREPE (Neural Pitch Detection)": ["crepe", "torch"],
    }

    for name, packages in optional.items():
        print(f"\n  {name}: {', '.join(packages)}")
        response = input("  Install? [y/N]: ").strip().lower()
        if response == "y":
            for pkg in packages:
                print(f"    Installing {pkg}...")
                cmd = [sys.executable, "-m", "pip", "install", pkg]
                run_command(cmd, check=False)


def check_nodejs() -> bool:
    """Check if Node.js is installed for GUI build."""
    print("\n📦 Checking Node.js...")

    if shutil.which("node"):
        code, version, _ = run_command(["node", "--version"])
        print(f"  ✅ Node.js {version.strip()} found")
        return True
    else:
        print("  ❌ Node.js not found")
        print("  Install from: https://nodejs.org")
        return False


def build_gui() -> bool:
    """Build the GUI."""
    print("\n🔨 Building GUI...")

    gui_path = os.path.join(os.path.dirname(__file__), "gui")

    if not os.path.exists(gui_path):
        print(f"  ⚠️  GUI directory not found at {gui_path}")
        return False

    # Check for package.json
    pkg_json = os.path.join(gui_path, "package.json")
    if not os.path.exists(pkg_json):
        print("  ⚠️  package.json not found")
        return False

    # Install npm dependencies
    print("  Installing npm dependencies...")
    code, _, err = run_command(["npm", "install"], cwd=gui_path)
    if code != 0:
        print(f"  ❌ npm install failed: {err}")
        return False

    # Build
    print("  Building...")
    code, _, err = run_command(["npm", "run", "build"], cwd=gui_path)
    if code != 0:
        print(f"  ❌ Build failed: {err}")
        return False

    print("  ✅ GUI built successfully")
    return True


def check_linux_permissions() -> None:
    """Check Linux permissions for serial/USB."""
    print("\n🔒 Checking Linux permissions...")

    if platform.system() != "Linux":
        return

    # Check dialout group for serial access
    import getpass

    username = getpass.getuser()

    try:
        import grp

        grp.getgrnam("dialout")
        user_groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]

        if "dialout" not in user_groups:
            print(f"  ⚠️  User '{username}' is not in 'dialout' group")
            print(f"  Run: sudo usermod -a -G dialout {username}")
            print("  Then log out and back in for changes to take effect")
        else:
            print("  ✅ User is in 'dialout' group")
    except KeyError:
        pass


def generate_default_config() -> None:
    """Generate default configuration file."""
    print("\n⚙️  Generating default configuration...")

    config_path = os.path.join(os.path.dirname(__file__), "..", "omnisound_config.json")

    if os.path.exists(config_path):
        print(f"  ⚠️  Configuration already exists at {config_path}")
        return

    from core.config_manager import DEFAULT_CONFIG
    import json

    with open(config_path, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)

    print(f"  ✅ Configuration created at {config_path}")


def print_success_message() -> None:
    """Print success message with instructions."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                    ✅ INSTALLATION COMPLETE               ║
╚═══════════════════════════════════════════════════════════╝

To start OMNISOUND:
    python omnisound.py

For command line options:
    python omnisound.py --help

For diagnostics:
    python omnisound.py --diagnose

To open the dashboard:
    http://localhost:8000

Documentation: https://github.com/omnisound/omnisound

Enjoy making music with your motors! 🎵
""")


def main():
    """Main installer function."""
    print(BANNER)

    # Check Python version
    ok, msg = check_python_version()
    print(f"\n🐍 {msg}")
    if not ok:
        print("  Please upgrade Python to 3.9 or later")
        sys.exit(1)

    # Detect OS
    os_type, distro = detect_os()
    print(f"\n💻 Detected OS: {os_type} ({distro})")

    # Install system dependencies
    if os_type == "linux":
        check_linux_permissions()

    install_system_dependencies(os_type, distro)

    # Install Python packages
    if not install_python_packages():
        print("\n❌ Failed to install Python packages")
        sys.exit(1)

    # Optional packages
    try:
        install_optional_packages()
    except KeyboardInterrupt:
        print("\n  Skipping optional packages")

    # Check Node.js and build GUI
    if check_nodejs():
        build_gui()
    else:
        print("\n  ⚠️  GUI will not be built. Install Node.js to build the GUI.")

    # Generate default config
    generate_default_config()

    # Success
    print_success_message()


if __name__ == "__main__":
    main()
