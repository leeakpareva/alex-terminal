#!/usr/bin/env python3
"""
ALEX Terminal - Desktop Voice/Chat UI
Main PyQt5 application for interacting with ALEX on the Pi.
"""

import sys
import os
import html
import time
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextBrowser, QLineEdit, QPushButton, QLabel, QSizePolicy,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QTextCursor

from styles import DARK_THEME
from alex_client import AlexClient
from voice_engine import (
    TTSWorker, STTWorker, get_voice_enabled, set_voice_enabled, detect_bt_sink,
)
from autonomous import AutonomousPoller


MARKER_FILE = Path.home() / ".alex" / "terminal-active"


class CommandWorker(QThread):
    """Send a message to ALEX in a background thread."""
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, client, message, parent=None):
        super().__init__(parent)
        self.client = client
        self.message = message

    def run(self):
        response, error = self.client.send_message(self.message)
        if error:
            self.error_occurred.emit(error)
        else:
            self.response_ready.emit(response)


class HealthCheckWorker(QThread):
    """Health check with retries."""
    connected = pyqtSignal(dict)
    failed = pyqtSignal()

    def __init__(self, client, retries=5, delay=2, parent=None):
        super().__init__(parent)
        self.client = client
        self.retries = retries
        self.delay = delay

    def run(self):
        for i in range(self.retries):
            result = self.client.health_check()
            if result:
                self.connected.emit(result)
                return
            if i < self.retries - 1:
                time.sleep(self.delay)
        self.failed.emit()


class AlexTerminal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.client = AlexClient()
        self.voice_on = get_voice_enabled()
        self._tts_worker = None
        self._stt_worker = None
        self._cmd_worker = None
        self._health_worker = None
        self._poller = None

        self._init_ui()
        self._write_marker()
        self._start_health_check()

    def _init_ui(self):
        self.setWindowTitle("ALEX Terminal")
        self.setStyleSheet(DARK_THEME)

        # Compact size so user can multitask on 800x480 display
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            w = min(480, geom.width() - 20)
            h = min(340, geom.height() - 40)
            self.resize(w, h)
            # Position at bottom-right corner
            self.move(geom.width() - w - 10, geom.height() - h - 10)
        else:
            self.resize(480, 340)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        # --- Top bar ---
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel("ALEX - Global Economist")
        self.title_label.setObjectName("titleLabel")
        top_bar.addWidget(self.title_label)

        top_bar.addStretch()

        self.status_dot = QLabel()
        self.status_dot.setObjectName("statusDot")
        self._set_status(False)
        top_bar.addWidget(self.status_dot)

        layout.addLayout(top_bar)

        # --- Chat area ---
        self.chat_area = QTextBrowser()
        self.chat_area.setObjectName("chatArea")
        self.chat_area.setOpenExternalLinks(True)
        self.chat_area.setFont(QFont("Monospace", 11))
        layout.addWidget(self.chat_area, stretch=1)

        # --- Input bar ---
        input_bar = QHBoxLayout()
        input_bar.setSpacing(4)
        input_bar.setContentsMargins(0, 0, 0, 0)

        self.input_field = QLineEdit()
        self.input_field.setObjectName("inputField")
        self.input_field.setPlaceholderText("Type a message to ALEX...")
        self.input_field.setMinimumHeight(36)
        self.input_field.returnPressed.connect(self._on_send)
        input_bar.addWidget(self.input_field, stretch=1)

        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.setMinimumHeight(36)
        self.send_btn.clicked.connect(self._on_send)
        input_bar.addWidget(self.send_btn)

        self.mic_btn = QPushButton("Mic")
        self.mic_btn.setObjectName("micBtn")
        self.mic_btn.setMinimumHeight(36)
        self.mic_btn.clicked.connect(self._on_mic)
        input_bar.addWidget(self.mic_btn)

        self.voice_btn = QPushButton()
        self.voice_btn.setObjectName("voiceBtn")
        self.voice_btn.setMinimumHeight(36)
        self.voice_btn.clicked.connect(self._on_voice_toggle)
        self._update_voice_btn()
        input_bar.addWidget(self.voice_btn)

        layout.addLayout(input_bar)

    # --- Status management ---

    def _set_status(self, online):
        if online:
            self.status_dot.setText("ONLINE")
            self.status_dot.setStyleSheet("color: #00ff88; font-weight: bold;")
        else:
            self.status_dot.setText("OFFLINE")
            self.status_dot.setStyleSheet("color: #ff4444; font-weight: bold;")

    # --- Health check ---

    def _start_health_check(self):
        self._append_system("Connecting to ALEX...")
        self._health_worker = HealthCheckWorker(self.client)
        self._health_worker.connected.connect(self._on_connected)
        self._health_worker.failed.connect(self._on_connection_failed)
        self._health_worker.start()

    def _on_connected(self, health_data):
        self._set_status(True)
        uptime = health_data.get("uptime_seconds", 0)
        uptime_str = f"{uptime // 3600}h {(uptime % 3600) // 60}m"
        self._append_system(f"Connected to ALEX (uptime: {uptime_str})")

        # Welcome banner
        self._append_html(
            '<br>'
            '<span style="color:#00ff88; font-size:16px; font-weight:bold;">'
            '  ___   __    ____  _  _<br>'
            ' / __) / /   ( ___)( \\/ )<br>'
            '( (__ / /_    )__)  )  ( <br>'
            ' \\___)(____)  (____)(_/\\_)<br>'
            '</span>'
            '<span style="color:#888;">ALEX Terminal v1.0 | '
            'Type a message or use /voice, /clear, /status</span><br>'
        )

        # Detect Bluetooth audio
        bt_sink = detect_bt_sink()
        if bt_sink:
            self._append_system(f"Bluetooth audio: {bt_sink}")
        else:
            self._append_system("No Bluetooth speaker detected (using default audio)")

        # Welcome TTS
        if self.voice_on:
            self._speak("Welcome Lee")

        # Start autonomous poller
        self._start_poller()

    def _on_connection_failed(self):
        self._set_status(False)
        self._append_system("Failed to connect to ALEX. Is the service running?")
        self._append_system("Retry with /status or restart ALEX: sudo systemctl restart alex")

    # --- Message handling ---

    def _on_send(self):
        text = self.input_field.text().strip()
        if not text:
            return

        self.input_field.clear()

        # Handle special commands
        if text.startswith("/"):
            self._handle_command(text)
            return

        # Display user message
        self._append_user(text)

        # Send to ALEX
        self._set_input_enabled(False)
        self._append_thinking()

        self._cmd_worker = CommandWorker(self.client, text)
        self._cmd_worker.response_ready.connect(self._on_response)
        self._cmd_worker.error_occurred.connect(self._on_error)
        self._cmd_worker.start()

    def _on_response(self, response):
        self._remove_thinking()
        self._append_alex(response)
        self._set_input_enabled(True)
        self.input_field.setFocus()

        if self.voice_on and response:
            self._speak(response)

    def _on_error(self, error):
        self._remove_thinking()
        self._append_system(f"Error: {error}")
        self._set_input_enabled(True)
        self.input_field.setFocus()

    def _handle_command(self, cmd):
        parts = cmd.split(None, 1)
        command = parts[0].lower()

        if command == "/voice":
            self.voice_on = not self.voice_on
            set_voice_enabled(self.voice_on)
            self._update_voice_btn()
            state = "ON" if self.voice_on else "OFF"
            self._append_system(f"Voice output {state}")

        elif command == "/clear":
            self.chat_area.clear()

        elif command == "/status":
            self._append_system("Checking ALEX status...")
            self._health_worker = HealthCheckWorker(self.client, retries=1, delay=0)
            self._health_worker.connected.connect(self._on_status_check)
            self._health_worker.failed.connect(
                lambda: (self._set_status(False), self._append_system("ALEX is offline"))
            )
            self._health_worker.start()

        else:
            self._append_system(f"Unknown command: {command}")
            self._append_system("Available: /voice, /clear, /status")

    def _on_status_check(self, health):
        self._set_status(True)
        uptime = health.get("uptime_seconds", 0)
        mem = health.get("memory", {})
        self._append_system(
            f"ALEX Status: OK | Uptime: {uptime // 3600}h {(uptime % 3600) // 60}m | "
            f"RAM: {mem.get('rss_mb', '?')}MB | "
            f"Telegram: {health.get('telegram', '?')} | "
            f"Redis: {health.get('redis', '?')}"
        )

    # --- Voice ---

    def _on_voice_toggle(self):
        self.voice_on = not self.voice_on
        set_voice_enabled(self.voice_on)
        self._update_voice_btn()
        state = "ON" if self.voice_on else "OFF"
        self._append_system(f"Voice output {state}")

    def _update_voice_btn(self):
        if self.voice_on:
            self.voice_btn.setText("Voice ON")
            self.voice_btn.setProperty("voiceOn", "true")
        else:
            self.voice_btn.setText("Voice OFF")
            self.voice_btn.setProperty("voiceOn", "false")
        # Force style refresh
        self.voice_btn.style().unpolish(self.voice_btn)
        self.voice_btn.style().polish(self.voice_btn)

    def _speak(self, text):
        # Don't overlap TTS
        if self._tts_worker and self._tts_worker.isRunning():
            return
        self._tts_worker = TTSWorker(text)
        self._tts_worker.error.connect(
            lambda e: self._append_system(f"TTS error: {e}")
        )
        self._tts_worker.start()

    def _on_mic(self):
        if self._stt_worker and self._stt_worker.isRunning():
            return

        self._stt_worker = STTWorker()
        self._stt_worker.recording_started.connect(
            lambda: (self.mic_btn.setText("Recording..."), self.mic_btn.setEnabled(False))
        )
        self._stt_worker.recording_stopped.connect(
            lambda: (self.mic_btn.setText("Mic"), self.mic_btn.setEnabled(True))
        )
        self._stt_worker.transcription_ready.connect(self._on_transcription)
        self._stt_worker.error.connect(self._on_stt_error)
        self._stt_worker.start()

    def _on_transcription(self, text):
        self.mic_btn.setText("Mic")
        self.mic_btn.setEnabled(True)
        self.input_field.setText(text)
        # Auto-send
        self._on_send()

    def _on_stt_error(self, error):
        self.mic_btn.setText("Mic")
        self.mic_btn.setEnabled(True)
        self._append_system(f"Mic: {error}")

    # --- Autonomous messages ---

    def _start_poller(self):
        self._poller = AutonomousPoller()
        self._poller.message_received.connect(self._on_autonomous_message)
        self._poller.start()

    def _on_autonomous_message(self, title, body):
        self._append_alex(f"[{title}] {body}")
        if self.voice_on:
            self._speak(body)

    # --- Chat display helpers ---

    def _append_html(self, html_str):
        self.chat_area.moveCursor(QTextCursor.End)
        self.chat_area.insertHtml(html_str)
        self.chat_area.moveCursor(QTextCursor.End)

    def _append_user(self, text):
        escaped = html.escape(text)
        self._append_html(
            f'<p style="color:#ffffff;"><b>You:</b> {escaped}</p>'
        )

    def _append_alex(self, text):
        escaped = html.escape(text)
        # Preserve line breaks
        escaped = escaped.replace("\n", "<br>")
        self._append_html(
            f'<p style="color:#00ff88;"><b>ALEX:</b> {escaped}</p>'
        )

    def _append_system(self, text):
        escaped = html.escape(text)
        self._append_html(
            f'<p style="color:#888888; font-style:italic;">{escaped}</p>'
        )

    def _append_thinking(self):
        self._append_html(
            '<p id="thinking" style="color:#888888; font-style:italic;">'
            'ALEX is thinking...</p>'
        )

    def _remove_thinking(self):
        content = self.chat_area.toHtml()
        content = content.replace(
            "ALEX is thinking...", ""
        )
        self.chat_area.setHtml(content)
        self.chat_area.moveCursor(QTextCursor.End)

    def _set_input_enabled(self, enabled):
        self.input_field.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)

    # --- Marker file ---

    def _write_marker(self):
        try:
            MARKER_FILE.parent.mkdir(parents=True, exist_ok=True)
            MARKER_FILE.write_text(str(os.getpid()))
        except Exception:
            pass

    def _remove_marker(self):
        try:
            if MARKER_FILE.exists():
                MARKER_FILE.unlink()
        except Exception:
            pass

    # --- Cleanup ---

    def closeEvent(self, event):
        self._remove_marker()
        if self._poller:
            self._poller.stop()
            self._poller.wait(2000)
        if self._tts_worker and self._tts_worker.isRunning():
            self._tts_worker.wait(2000)
        if self._stt_worker and self._stt_worker.isRunning():
            self._stt_worker.wait(2000)
        event.accept()


def main():
    # Ensure ~/.alex directory exists
    (Path.home() / ".alex").mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)
    app.setApplicationName("ALEX Terminal")

    window = AlexTerminal()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
