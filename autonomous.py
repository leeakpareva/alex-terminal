"""
ALEX Terminal - Autonomous Message Poller
Polls for proactive messages from ALEX (heartbeat tasks, alerts, etc.)
"""

import json
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal, QTimer

from alex_client import AlexClient


QUEUE_FILE = Path.home() / ".alex" / "terminal-queue.json"
POLL_INTERVAL_MS = 5000  # 5 seconds


class AutonomousPoller(QThread):
    """Polls for autonomous messages from ALEX."""
    message_received = pyqtSignal(str, str)  # (title, body)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._client = AlexClient()

    def run(self):
        self._running = True
        while self._running:
            self._poll()
            self.msleep(POLL_INTERVAL_MS)

    def stop(self):
        self._running = False

    def _poll(self):
        """Check both the file queue and the API endpoint."""
        # 1. Try API endpoint first
        try:
            messages = self._client.get_terminal_messages()
            for msg in messages:
                title = msg.get("title", "ALEX")
                body = msg.get("body", msg.get("text", ""))
                if body:
                    self.message_received.emit(title, body)
        except Exception:
            pass

        # 2. Also check file-based queue (fallback)
        try:
            if QUEUE_FILE.exists():
                data = json.loads(QUEUE_FILE.read_text())
                if isinstance(data, list) and data:
                    # Clear the file first, then emit
                    QUEUE_FILE.write_text("[]")
                    for msg in data:
                        title = msg.get("title", "ALEX")
                        body = msg.get("body", msg.get("text", ""))
                        if body:
                            self.message_received.emit(title, body)
        except (json.JSONDecodeError, OSError):
            pass
