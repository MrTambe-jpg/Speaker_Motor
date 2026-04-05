"""
Event Bus - Internal pub/sub message bus for OMNISOUND
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Represents an event in the system."""

    name: str
    data: dict[str, Any]
    source: str = "unknown"


class EventBus:
    """
    Internal publish/subscribe message bus.

    Allows decoupled communication between components:
    - Audio sources publish 'audio_data' events
    - Processors subscribe to 'audio_data' and publish 'processed_data'
    - Motor controller subscribes to 'processed_data'
    - GUI subscribes to all events for visualization
    """

    def __init__(self):
        self._subscribers: dict[str, set[Callable]] = defaultdict(set)
        self._async_subscribers: dict[str, set[Callable]] = defaultdict(set)
        self._event_history: list[Event] = []
        self._max_history = 100
        self._lock = asyncio.Lock()

    def subscribe(self, event_name: str, callback: Callable) -> None:
        """
        Subscribe to an event.

        Args:
            event_name: Event to subscribe to (e.g., 'audio_data', 'beat')
            callback: Function to call when event is published
        """
        self._subscribers[event_name].add(callback)
        logger.debug(f"Subscribed to event '{event_name}'")

    def subscribe_async(self, event_name: str, callback: Callable) -> None:
        """
        Subscribe to an event with an async callback.

        Args:
            event_name: Event to subscribe to
            callback: Async function to call when event is published
        """
        self._async_subscribers[event_name].add(callback)
        logger.debug(f"Subscribed async to event '{event_name}'")

    def unsubscribe(self, event_name: str, callback: Callable) -> None:
        """Unsubscribe from an event."""
        self._subscribers[event_name].discard(callback)
        self._async_subscribers[event_name].discard(callback)
        logger.debug(f"Unsubscribed from event '{event_name}'")

    def publish(self, event_name: str, data: dict[str, Any], source: str = "unknown") -> None:
        """
        Publish an event synchronously.

        Calls all synchronous subscribers immediately.
        For async subscribers, schedules them on the event loop.

        Args:
            event_name: Name of the event
            data: Event data dictionary
            source: Source component name
        """
        event = Event(name=event_name, data=data, source=source)

        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Call synchronous subscribers
        for callback in self._subscribers.get(event_name, set()):
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in subscriber callback for '{event_name}': {e}")

        # Schedule async subscribers
        for callback in self._async_subscribers.get(event_name, set()):
            try:
                asyncio.create_task(callback(event))
            except Exception as e:
                logger.error(f"Error scheduling async subscriber for '{event_name}': {e}")

    async def publish_async(
        self, event_name: str, data: dict[str, Any], source: str = "unknown"
    ) -> None:
        """
        Publish an event and wait for all async subscribers to complete.

        Args:
            event_name: Name of the event
            data: Event data dictionary
            source: Source component name
        """
        event = Event(name=event_name, data=data, source=source)

        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Call synchronous subscribers
        for callback in self._subscribers.get(event_name, set()):
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in subscriber callback for '{event_name}': {e}")

        # Call async subscribers and wait for completion
        tasks = []
        for callback in self._async_subscribers.get(event_name, set()):
            try:
                tasks.append(callback(event))
            except Exception as e:
                logger.error(f"Error creating async task for '{event_name}': {e}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_history(self, event_name: str = None) -> list[Event]:
        """Get event history, optionally filtered by event name."""
        if event_name:
            return [e for e in self._event_history if e.name == event_name]
        return list(self._event_history)

    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()

    def list_events(self) -> list[str]:
        """List all event types with subscribers."""
        events = set(self._subscribers.keys()) | set(self._async_subscribers.keys())
        return list(events)


# Predefined event types for type hints
class Events:
    """Event type constants."""

    AUDIO_DATA = "audio_data"
    AUDIO_STARTED = "audio_started"
    AUDIO_STOPPED = "audio_stopped"
    AUDIO_ERROR = "audio_error"

    MOTOR_STATE = "motor_state"
    MOTOR_COMMAND = "motor_command"

    BEAT = "beat"
    BPM_UPDATE = "bpm_update"

    FFT_DATA = "fft_data"
    SPECTRUM_DATA = "spectrum_data"

    TRACK_CHANGED = "track_changed"
    TRACK_METADATA = "track_metadata"

    HARDWARE_CONNECTED = "hardware_connected"
    HARDWARE_DISCONNECTED = "hardware_disconnected"
    HARDWARE_ERROR = "hardware_error"
    HARDWARE_STATUS = "hardware_status"

    PLUGIN_LOADED = "plugin_loaded"
    PLUGIN_UNLOADED = "plugin_unloaded"
    PLUGIN_ERROR = "plugin_error"

    CONFIG_CHANGED = "config_changed"

    RECORDING_STARTED = "recording_started"
    RECORDING_STOPPED = "recording_stopped"

    ERROR = "error"
    LOG = "log"

    WEBSOCKET_CONNECTED = "websocket_connected"
    WEBSOCKET_DISCONNECTED = "websocket_disconnected"


# Global singleton instance
_event_bus: EventBus = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def reset_event_bus() -> None:
    """Reset the global event bus (useful for testing)."""
    global _event_bus
    _event_bus = EventBus()
