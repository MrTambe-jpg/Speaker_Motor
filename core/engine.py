"""
OmniSound Engine - Main orchestrator for the OMNISOUND system
"""

import asyncio
import json
import logging
import os
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .audio_pipeline import get_audio_pipeline
from .config_manager import get_config_manager
from .event_bus import Events, get_event_bus
from .motor_controller import get_motor_controller
from .plugin_registry import PluginType, get_plugin_registry

logger = logging.getLogger(__name__)


class OmniSoundEngine:
    """
    Main orchestrator for the OMNISOUND system.

    - Loads configuration on startup
    - Instantiates all active plugins
    - Connects: AudioSource → AudioPipeline → MotorController → HardwarePlugin
    - Exposes FastAPI backend with WebSocket support
    - Broadcasts plugin events over EventBus
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config = get_config_manager(config_path)
        self.event_bus = get_event_bus()
        self.plugin_registry = get_plugin_registry()
        self.audio_pipeline = get_audio_pipeline()
        self.motor_controller = get_motor_controller()

        self.app: Optional[FastAPI] = None
        self.websocket_clients: set[WebSocket] = set()
        self.server = None
        self.is_running = False

        # Active plugins
        self.active_hardware = None
        self.active_audio_source = None
        self.active_processors: list[Any] = []

        # System info
        self.system_info: dict[str, Any] = {}
        self._collect_system_info()

        # Sequence recording state
        self._recording = False
        self._recorded_sequence: list[dict[str, Any]] = []
        self._record_start_time: Optional[float] = None

        # Setup event subscriptions
        self._setup_event_handlers()

    def _collect_system_info(self) -> None:
        """Collect system information."""
        self.system_info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "python_version": sys.version,
            "python_implementation": platform.python_implementation(),
            "cpu_count": os.cpu_count(),
            "hostname": platform.node(),
            "omnisound_version": "1.0.0",
        }

    def _setup_event_handlers(self) -> None:
        """Setup event handlers for WebSocket broadcasting."""
        # Subscribe to all relevant events
        for event_type in [
            Events.AUDIO_DATA,
            Events.AUDIO_STARTED,
            Events.AUDIO_STOPPED,
            Events.MOTOR_STATE,
            Events.BEAT,
            Events.FFT_DATA,
            Events.TRACK_CHANGED,
            Events.HARDWARE_CONNECTED,
            Events.HARDWARE_DISCONNECTED,
            Events.PLUGIN_LOADED,
            Events.CONFIG_CHANGED,
            Events.ERROR,
            Events.LOG,
        ]:
            self.event_bus.subscribe_async(event_type, self._broadcast_event)

        # Record motor state changes when recording
        self.event_bus.subscribe_async(Events.MOTOR_STATE, self._record_motor_state)

    async def _broadcast_event(self, event: Any) -> None:
        """Broadcast an event to all WebSocket clients."""
        message = json.dumps(
            {
                "event": event.name,
                "data": event.data,
                "source": event.source,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Send to all connected clients
        disconnected = set()
        for ws in self.websocket_clients:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.add(ws)

        # Remove disconnected clients
        for ws in disconnected:
            self.websocket_clients.discard(ws)

    async def _record_motor_state(self, event: Any) -> None:
        """Capture motor state during sequence recording."""
        if self._recording and event.data:
            timestamp = datetime.now().timestamp() - (self._record_start_time or 0)
            self._recorded_sequence.append({"timestamp": round(timestamp, 3), "motors": event.data})

    def create_app(self) -> FastAPI:
        """Create and configure the FastAPI application."""
        app = FastAPI(
            title="OMNISOUND", description="Universal Motor Speaker System", version="1.0.0"
        )

        # CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Mount static files for GUI
        gui_dist_path = Path(__file__).parent.parent / "gui" / "dist"
        if gui_dist_path.exists():
            app.mount(
                "/assets", StaticFiles(directory=str(gui_dist_path / "assets")), name="assets"
            )

        # API Routes
        @app.get("/api/plugins")
        async def get_plugins():
            """Get all available plugins."""
            return self.plugin_registry.get_all_plugins_info()

        @app.get("/api/plugins/{plugin_type}")
        async def get_plugins_by_type(plugin_type: str):
            """Get plugins by type."""
            try:
                ptype = PluginType(plugin_type)
                return self.plugin_registry.get_plugins_by_type(ptype)
            except ValueError as err:
                raise HTTPException(
                    status_code=400, detail=f"Invalid plugin type: {plugin_type}"
                ) from err

        @app.get("/api/config")
        async def get_config():
            """Get current configuration."""
            return self.config.to_dict()

        @app.put("/api/config")
        async def set_config(config: dict[str, Any]):
            """Update configuration."""
            for key, value in config.items():
                self.config.set(key, value, save_immediately=False)
            self.config.save()
            return {"status": "ok"}

        @app.get("/api/config/{key_path:path}")
        async def get_config_value(key_path: str):
            """Get a specific config value."""
            return {"key": key_path, "value": self.config.get(key_path)}

        @app.put("/api/config/{key_path:path}")
        async def set_config_value(key_path: str, value: Any):
            """Set a specific config value."""
            self.config.set(key_path, value)
            return {"status": "ok"}

        @app.get("/api/system")
        async def get_system_info():
            """Get system information."""
            return self.system_info

        @app.get("/api/motors")
        async def get_motors():
            """Get motor states."""
            return self.motor_controller.get_all_states()

        @app.post("/api/motors/{motor_id}/angle")
        async def set_motor_angle(motor_id: int, angle: float):
            """Set a motor angle (manual mode)."""
            await self.motor_controller.set_motor_angle(motor_id, angle)
            return {"status": "ok", "motor_id": motor_id, "angle": angle}

        @app.post("/api/motors/{motor_id}/test")
        async def test_motor(motor_id: int):
            """Test a motor."""
            await self.motor_controller.test_motor(motor_id)
            return {"status": "ok"}

        @app.post("/api/start")
        async def start_system():
            """Start the audio processing system."""
            await self.start_processing()
            return {"status": "started"}

        @app.post("/api/stop")
        async def stop_system():
            """Stop the audio processing system."""
            await self.stop_processing()
            return {"status": "stopped"}

        @app.get("/api/status")
        async def get_status():
            """Get system status."""
            return {
                "is_running": self.is_running,
                "hardware": self.active_hardware.plugin_id if self.active_hardware else None,
                "audio_source": (
                    self.active_audio_source.plugin_id if self.active_audio_source else None
                ),
                "processors": [p.plugin_id for p in self.active_processors],
                "websocket_clients": len(self.websocket_clients),
            }

        @app.post("/api/hardware/{plugin_id}")
        async def set_hardware_plugin(plugin_id: str):
            """Set active hardware plugin."""
            success = await self.plugin_registry.set_active_hardware(
                plugin_id, self.config.get_plugin_config("hardware", plugin_id)
            )
            if success:
                self.active_hardware = self.plugin_registry.active_hardware
                self.motor_controller.set_hardware_plugin(self.active_hardware)
                self.config.set("hardware.active_plugin", plugin_id)
                return {"status": "ok", "plugin": plugin_id}
            raise HTTPException(
                status_code=400, detail=f"Failed to activate hardware plugin: {plugin_id}"
            )

        @app.post("/api/audio/{plugin_id}")
        async def set_audio_source(plugin_id: str):
            """Set active audio source plugin."""
            success = await self.plugin_registry.set_active_audio_source(
                plugin_id, self.config.get_plugin_config("audio", plugin_id)
            )
            if success:
                self.active_audio_source = self.plugin_registry.active_audio_source
                self.config.set("audio.active_source", plugin_id)
                return {"status": "ok", "plugin": plugin_id}
            raise HTTPException(
                status_code=400, detail=f"Failed to activate audio source: {plugin_id}"
            )

        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time communication."""
            await websocket.accept()
            self.websocket_clients.add(websocket)

            self.event_bus.publish(
                Events.WEBSOCKET_CONNECTED,
                {"client_count": len(self.websocket_clients)},
                source="engine",
            )

            try:
                while True:
                    # Receive and handle commands
                    data = await websocket.receive_text()
                    try:
                        command = json.loads(data)
                        response = await self._handle_websocket_command(command)
                        if response:
                            await websocket.send_text(json.dumps(response))
                    except json.JSONDecodeError:
                        await websocket.send_text(
                            json.dumps({"error": "Invalid JSON", "message": data})
                        )
            except WebSocketDisconnect:
                self.websocket_clients.discard(websocket)
                self.event_bus.publish(
                    Events.WEBSOCKET_DISCONNECTED,
                    {"client_count": len(self.websocket_clients)},
                    source="engine",
                )

        @app.post("/api/config/export")
        async def export_config():
            """Export configuration."""
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                self.config.export_config(f.name)
                return FileResponse(f.name, filename="omnisound_config.json")

        @app.post("/api/config/import")
        async def import_config(file: bytes):
            """Import configuration."""
            import tempfile

            with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
                f.write(file)
                self.config.import_config(f.name)
            return {"status": "ok"}

        @app.post("/api/config/reset")
        async def reset_config():
            """Reset configuration to defaults."""
            self.config.reset_to_defaults()
            return {"status": "ok"}

        @app.get("/api/diagnostics")
        async def get_diagnostics():
            """Run system diagnostics."""
            return await self._run_diagnostics()

        # Serve GUI
        @app.get("/")
        async def serve_gui():
            """Serve the main GUI page."""
            index_path = gui_dist_path / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
            return {
                "message": "OMNISOUND API is running. GUI not built - run 'npm run build' in gui/"
            }

        @app.get("/{path:path}")
        async def serve_gui_routes(path: str):
            """Serve GUI for all routes (SPA fallback)."""
            # Try to serve the file directly
            file_path = gui_dist_path / path
            if file_path.exists() and file_path.is_file():
                return FileResponse(str(file_path))
            # Fall back to index.html for SPA routing
            index_path = gui_dist_path / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
            raise HTTPException(status_code=404, detail="Not found")

        self.app = app
        return app

    async def _handle_websocket_command(self, command: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Handle a WebSocket command from the client."""
        cmd = command.get("cmd")
        response = {"status": "error", "message": "Unknown command"}

        try:
            if cmd == "start":
                await self.start_processing()
                response = {"status": "ok", "message": "Started"}

            elif cmd == "stop":
                await self.stop_processing()
                response = {"status": "ok", "message": "Stopped"}

            elif cmd == "set_source":
                plugin_id = command.get("plugin_id")
                if plugin_id:
                    success = await self.plugin_registry.set_active_audio_source(
                        plugin_id, self.config.get_plugin_config("audio", plugin_id)
                    )
                    if success:
                        self.active_audio_source = self.plugin_registry.active_audio_source
                        response = {"status": "ok", "plugin": plugin_id}
                    else:
                        response = {"status": "error", "message": f"Failed to activate {plugin_id}"}

            elif cmd == "set_hardware":
                plugin_id = command.get("plugin_id")
                if plugin_id:
                    success = await self.plugin_registry.set_active_hardware(
                        plugin_id, self.config.get_plugin_config("hardware", plugin_id)
                    )
                    if success:
                        self.active_hardware = self.plugin_registry.active_hardware
                        self.motor_controller.set_hardware_plugin(self.active_hardware)
                        response = {"status": "ok", "plugin": plugin_id}
                    else:
                        response = {"status": "error", "message": f"Failed to activate {plugin_id}"}

            elif cmd == "set_config":
                path = command.get("path")
                value = command.get("value")
                if path:
                    self.config.set(path, value)
                    response = {"status": "ok", "path": path, "value": value}

            elif cmd == "manual_motor":
                motor_id = command.get("motor")
                angle = command.get("angle")
                if motor_id is not None and angle is not None:
                    await self.motor_controller.set_motor_angle(motor_id, angle)
                    response = {"status": "ok", "motor": motor_id, "angle": angle}

            elif cmd == "test_motor":
                motor_id = command.get("motor")
                if motor_id is not None:
                    await self.motor_controller.test_motor(motor_id)
                    response = {"status": "ok", "motor": motor_id}

            elif cmd == "record_start":
                self._recording = True
                self._recorded_sequence = []
                self._record_start_time = datetime.now().timestamp()
                self.event_bus.publish(
                    Events.RECORDING_STARTED,
                    {"timestamp": self._record_start_time},
                    source="engine",
                )
                response = {"status": "ok", "message": "Recording started"}

            elif cmd == "record_stop":
                if not self._recording:
                    response = {"status": "error", "message": "Not recording"}
                else:
                    self._recording = False
                    duration = datetime.now().timestamp() - self._record_start_time
                    name = command.get(
                        "name", f"Sequence_{len(self.config.get('sequences.saved', [])) + 1}"
                    )
                    sequence = {
                        "id": f"seq_{int(datetime.now().timestamp())}",
                        "name": name,
                        "duration": round(duration, 2),
                        "motor_count": self.config.get("motors.count", 4),
                        "frames": self._recorded_sequence,
                        "created_at": datetime.now().isoformat(),
                    }
                    saved = self.config.get("sequences.saved", [])
                    saved.append(sequence)
                    self.config.set("sequences.saved", saved)
                    self.event_bus.publish(
                        Events.RECORDING_STOPPED,
                        {"sequence_id": sequence["id"], "name": name, "duration": duration},
                        source="engine",
                    )
                    response = {
                        "status": "ok",
                        "message": f"Recording saved as {name}",
                        "sequence": sequence["id"],
                    }
                    self._recorded_sequence = []

            elif cmd == "get_status":
                response = {
                    "status": "ok",
                    "is_running": self.is_running,
                    "hardware": self.active_hardware.plugin_id if self.active_hardware else None,
                    "audio_source": (
                        self.active_audio_source.plugin_id if self.active_audio_source else None
                    ),
                    "motors": self.motor_controller.get_all_states(),
                }

        except Exception as e:
            logger.error(f"Error handling WebSocket command: {e}")
            response = {"status": "error", "message": str(e)}

        return response

    async def initialize(self) -> None:
        """Initialize the engine and all plugins."""
        logger.info("Initializing OMNISOUND engine...")

        # Discover plugins
        self.plugin_registry.discover_plugins()

        # Log plugin availability
        for ptype in PluginType:
            available = self.plugin_registry.get_available_plugins(ptype)
            unavailable = self.plugin_registry.get_unavailable_plugins(ptype)
            logger.info(
                f"{ptype.value}: {len(available)} available, {len(unavailable)} unavailable"
            )
            for info in unavailable:
                logger.warning(f"  - {info.plugin_id}: {info.unavailable_reason}")

        # Initialize hardware plugin from config
        hardware_plugin_id = self.config.get_active_hardware_plugin()
        hardware_config = self.config.get_plugin_config("hardware", hardware_plugin_id)

        if hardware_plugin_id == "simulation":
            # Simulation is always available
            await self.plugin_registry.initialize_plugin(hardware_plugin_id, hardware_config)
            self.active_hardware = self.plugin_registry.get_plugin(hardware_plugin_id)
            self.motor_controller.set_hardware_plugin(self.active_hardware)
            logger.info(f"Initialized hardware plugin: {hardware_plugin_id}")
        else:
            # Try to initialize the configured hardware
            plugin_info = self.plugin_registry.plugins.get(hardware_plugin_id)
            if plugin_info and plugin_info.is_available:
                success = await self.plugin_registry.set_active_hardware(
                    hardware_plugin_id, hardware_config
                )
                if success:
                    self.active_hardware = self.plugin_registry.active_hardware
                    self.motor_controller.set_hardware_plugin(self.active_hardware)
                    logger.info(f"Initialized hardware plugin: {hardware_plugin_id}")
                else:
                    logger.warning(f"Failed to initialize hardware plugin: {hardware_plugin_id}")
            else:
                logger.warning(f"Hardware plugin not available: {hardware_plugin_id}")

        # Initialize audio source from config
        audio_plugin_id = self.config.get_active_audio_source()
        audio_config = self.config.get_plugin_config("audio", audio_plugin_id)

        plugin_info = self.plugin_registry.plugins.get(audio_plugin_id)
        if plugin_info and plugin_info.is_available:
            success = await self.plugin_registry.set_active_audio_source(
                audio_plugin_id, audio_config
            )
            if success:
                self.active_audio_source = self.plugin_registry.active_audio_source
                logger.info(f"Initialized audio source: {audio_plugin_id}")
            else:
                logger.warning(f"Failed to initialize audio source: {audio_plugin_id}")
        else:
            logger.warning(f"Audio source not available: {audio_plugin_id}")

        # Initialize processors
        active_processors = self.config.get("processors.active", [])
        for proc_id in active_processors:
            proc_config = self.config.get_plugin_config("processors", proc_id)
            proc_info = self.plugin_registry.plugins.get(proc_id)
            if proc_info and proc_info.is_available:
                success = await self.plugin_registry.initialize_plugin(proc_id, proc_config)
                if success:
                    proc = self.plugin_registry.get_plugin(proc_id)
                    self.audio_pipeline.add_processor(proc)
                    self.active_processors.append(proc)
                    logger.info(f"Initialized processor: {proc_id}")

        logger.info("OMNISOUND engine initialized")

    async def start_processing(self) -> None:
        """Start audio processing."""
        if self.is_running:
            return

        self.is_running = True

        # Start audio pipeline
        await self.audio_pipeline.start()

        # Start motor controller
        await self.motor_controller.start()

        # Start audio source if available
        if self.active_audio_source:
            # Start streaming in background
            asyncio.create_task(self._stream_audio())

        logger.info("Processing started")

    async def _stream_audio(self) -> None:
        """Stream audio from the active source."""
        if not self.active_audio_source:
            return

        try:
            while self.is_running:
                chunk = await self.active_audio_source.get_audio_chunk()
                if chunk is None:
                    # Stream ended, wait before retrying
                    await asyncio.sleep(0.1)
                    continue

                # Push to pipeline
                from .audio_pipeline import AudioChunk

                audio_chunk = AudioChunk(
                    samples=chunk,
                    sample_rate=self.active_audio_source.get_sample_rate(),
                    timestamp=asyncio.get_event_loop().time(),
                    duration=len(chunk) / self.active_audio_source.get_sample_rate(),
                )
                await self.audio_pipeline.push_audio(audio_chunk)

        except Exception as e:
            logger.error(f"Error streaming audio: {e}")
            self.event_bus.publish(
                Events.AUDIO_ERROR,
                {
                    "error": str(e),
                    "source": (
                        self.active_audio_source.plugin_id if self.active_audio_source else None
                    ),
                },
                source="engine",
            )

    async def stop_processing(self) -> None:
        """Stop audio processing."""
        if not self.is_running:
            return

        self.is_running = False

        # Stop audio source
        if self.active_audio_source:
            try:
                await self.active_audio_source.stop_stream()
            except Exception as e:
                logger.error(f"Error stopping audio source: {e}")

        # Stop audio pipeline
        await self.audio_pipeline.stop()

        # Stop motor controller
        await self.motor_controller.stop()

        logger.info("Processing stopped")

    async def shutdown(self) -> None:
        """Shutdown the engine."""
        logger.info("Shutting down OMNISOUND engine...")

        # Stop processing
        await self.stop_processing()

        # Shutdown all plugins
        for plugin_id in list(self.plugin_registry.plugins.keys()):
            try:
                await self.plugin_registry.shutdown_plugin(plugin_id)
            except Exception as e:
                logger.error(f"Error shutting down plugin {plugin_id}: {e}")

        logger.info("OMNISOUND engine shutdown complete")

    async def _run_diagnostics(self) -> dict[str, Any]:
        """Run system diagnostics."""
        diagnostics = {
            "timestamp": datetime.now().isoformat(),
            "system": self.system_info,
            "plugins": {},
            "hardware": {},
            "audio": {},
            "config": {
                "file": self.config.get_config_file_path(),
                "last_saved": (
                    str(self.config.get_last_saved()) if self.config.get_last_saved() else None
                ),
            },
        }

        # Plugin diagnostics
        for ptype in PluginType:
            available = self.plugin_registry.get_available_plugins(ptype)
            unavailable = self.plugin_registry.get_unavailable_plugins(ptype)
            diagnostics["plugins"][ptype.value] = {
                "available": [p.plugin_id for p in available],
                "unavailable": [{p.plugin_id: p.unavailable_reason} for p in unavailable],
            }

        # Hardware diagnostics
        if self.active_hardware:
            try:
                can_ping = await self.active_hardware.ping()
                diagnostics["hardware"] = {
                    "connected": can_ping,
                    "plugin": self.active_hardware.plugin_id,
                }
            except Exception as e:
                diagnostics["hardware"] = {"connected": False, "error": str(e)}
        else:
            diagnostics["hardware"] = {"connected": False, "message": "No hardware plugin active"}

        # Audio pipeline diagnostics
        diagnostics["audio"] = self.audio_pipeline.get_stats()

        return diagnostics

    def run(self, host: str = None, port: int = None, open_browser: bool = None) -> None:
        """Run the server."""
        host = host or self.config.get("system.host", "0.0.0.0")
        port = port or self.config.get("system.port", 8000)
        open_browser = (
            open_browser
            if open_browser is not None
            else self.config.get("system.auto_open_browser", True)
        )

        # Create app
        app = self.create_app()

        # Lifespan context manager (replaces deprecated on_event)
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def lifespan(app):
            await self.initialize()
            if self.config.get("system.auto_start", False):
                await self.start_processing()
            yield
            await self.shutdown()

        app.router.lifespan_context = lifespan

        # Print startup banner
        self._print_banner(host, port)

        # Open browser if requested
        if open_browser:
            import webbrowser

            webbrowser.open(f"http://localhost:{port}")

        # Run server
        uvicorn.run(app, host=host, port=port, log_level="info")

    def _print_banner(self, host: str, port: int) -> None:
        """Print startup banner."""
        import socket

        # Get local IP
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
        except socket.gaierror:
            local_ip = "localhost"

        hardware = self.config.get_active_hardware_plugin()
        audio = self.config.get_active_audio_source()

        print("\n" + "=" * 50)
        print("  OMNISOUND v1.0 - Universal Motor Audio")
        print("=" * 50)
        print(f"  Dashboard → http://localhost:{port}")
        print(f"  Network  → http://{local_ip}:{port}")
        print(f"  Hardware → {hardware}")
        print(f"  Audio    → {audio}")
        print("=" * 50 + "\n")


# Global singleton
_engine: Optional[OmniSoundEngine] = None


def get_engine() -> OmniSoundEngine:
    """Get the global engine instance."""
    global _engine
    if _engine is None:
        _engine = OmniSoundEngine()
    return _engine
