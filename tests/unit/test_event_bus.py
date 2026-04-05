"""Tests for the EventBus class."""
import asyncio
import pytest

from core.event_bus import EventBus, Events


@pytest.fixture
def event_bus():
    """Create a fresh EventBus instance."""
    return EventBus()


class TestEventBusSubscribe:
    """Test event subscription."""

    def test_subscribe_sync(self, event_bus):
        """Test subscribing to an event with a sync handler."""
        results = []

        def handler(event):
            results.append(event.data)

        event_bus.subscribe(Events.AUDIO_DATA, handler)
        event_bus.publish(Events.AUDIO_DATA, {"test": True})

        assert len(results) == 1
        assert results[0] == {"test": True}

    def test_subscribe_multiple_handlers(self, event_bus):
        """Test multiple handlers for the same event."""
        results = []

        def handler1(event):
            results.append(1)

        def handler2(event):
            results.append(2)

        event_bus.subscribe(Events.AUDIO_DATA, handler1)
        event_bus.subscribe(Events.AUDIO_DATA, handler2)
        event_bus.publish(Events.AUDIO_DATA, {})

        assert set(results) == {1, 2}

    def test_unsubscribe(self, event_bus):
        """Test unsubscribing from an event."""
        results = []

        def handler(event):
            results.append(event.data)

        event_bus.subscribe(Events.AUDIO_DATA, handler)
        event_bus.publish(Events.AUDIO_DATA, "first")
        event_bus.unsubscribe(Events.AUDIO_DATA, handler)
        event_bus.publish(Events.AUDIO_DATA, "second")

        assert len(results) == 1
        assert results[0] == "first"

    def test_subscribe_to_all_events(self, event_bus):
        """Test subscribing to all events."""
        results = []

        def handler(event):
            results.append(event.name)

        event_types = [
            Events.AUDIO_DATA, Events.AUDIO_STARTED, Events.AUDIO_STOPPED,
            Events.BEAT, Events.FFT_DATA, Events.MOTOR_STATE,
        ]
        for event_type in event_types:
            event_bus.subscribe(event_type, handler)
        event_bus.publish(Events.AUDIO_DATA, {})
        event_bus.publish(Events.BEAT, {})

        assert Events.AUDIO_DATA in results
        assert Events.BEAT in results


class TestEventBusAsync:
    """Test async event handling."""

    @pytest.mark.asyncio
    async def test_subscribe_async(self, event_bus):
        """Test subscribing with an async handler."""
        results = []

        async def async_handler(event):
            results.append(event.data)

        event_bus.subscribe_async(Events.AUDIO_DATA, async_handler)
        await event_bus.publish_async(Events.AUDIO_DATA, {"async": True})

        assert len(results) == 1
        assert results[0] == {"async": True}


class TestEventBusPublish:
    """Test event publishing."""

    def test_publish_with_source(self, event_bus):
        """Test publishing with a source."""
        results = []

        def handler(event):
            results.append(event.source)

        event_bus.subscribe(Events.AUDIO_DATA, handler)
        event_bus.publish(Events.AUDIO_DATA, {}, source="test_source")

        assert results[0] == "test_source"

    def test_publish_no_handlers(self, event_bus):
        """Test publishing when no handlers are subscribed."""
        event_bus.publish(Events.AUDIO_DATA, {"orphan": True})


class TestEvents:
    """Test Events enum."""

    def test_events_have_expected_values(self):
        """Test that Events enum has expected values."""
        assert hasattr(Events, "AUDIO_DATA")
        assert hasattr(Events, "AUDIO_STARTED")
        assert hasattr(Events, "AUDIO_STOPPED")
        assert hasattr(Events, "MOTOR_STATE")
        assert hasattr(Events, "BEAT")
        assert hasattr(Events, "FFT_DATA")
        assert hasattr(Events, "ERROR")
        assert hasattr(Events, "LOG")
