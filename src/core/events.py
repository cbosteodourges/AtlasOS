"""
ATLAS OS
Event Bus
"""


class EventBus:
    def __init__(self):
        self._listeners = {}

    def subscribe(self, event_name, callback):
        """Abonne une fonction à un événement."""
        if event_name not in self._listeners:
            self._listeners[event_name] = []

        self._listeners[event_name].append(callback)

    def emit(self, event_name, data=None):
        """Déclenche un événement."""
        if event_name not in self._listeners:
            return

        for callback in self._listeners[event_name]:
            callback(data)


events = EventBus()