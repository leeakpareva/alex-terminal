"""
ALEX Terminal - Voice Engine (TTS + STT)
Reuses the proven pattern from voice_agent.py.
"""

import os
import json
import subprocess
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from PyQt5.QtCore import QThread, pyqtSignal


# Load OpenAI key from ~/.env
load_dotenv(Path.home() / ".env")

CONFIG_DIR = Path.home() / ".alex"
CONFIG_FILE = CONFIG_DIR / "terminal-config.json"

# Audio input settings for USB mic (C-Media USB PnP Sound Device)
MIC_DEVICE = "hw:2,0"
MIC_SAMPLE_RATE = 48000
MIC_CHANNELS = 1
MIC_FORMAT = "S16_LE"
MIC_DURATION = 5
MIN_AUDIO_SIZE = 1000  # bytes - filter out silence


def _load_config():
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text())
    except Exception:
        pass
    return {}


def _save_config(data):
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def get_voice_enabled():
    return _load_config().get("voice_enabled", True)


def set_voice_enabled(enabled):
    cfg = _load_config()
    cfg["voice_enabled"] = enabled
    _save_config(cfg)


def detect_bt_sink():
    """Detect the K07 Bluetooth speaker sink via pactl."""
    try:
        result = subprocess.run(
            ["pactl", "list", "short", "sinks"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.strip().split("\n"):
            if "bluez" in line.lower():
                parts = line.split("\t")
                if len(parts) >= 2:
                    return parts[1]  # sink name
    except Exception:
        pass
    return None


def set_default_sink(sink_name):
    """Set PipeWire/PulseAudio default sink."""
    try:
        subprocess.run(
            ["pactl", "set-default-sink", sink_name],
            capture_output=True, timeout=5,
        )
        return True
    except Exception:
        return False


class TTSWorker(QThread):
    """Generate and play TTS audio in a background thread."""
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text
        self._client = None

    def run(self):
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                self.error.emit("OpenAI API key not configured")
                return

            self._client = OpenAI(api_key=api_key)

            # Generate speech
            response = self._client.audio.speech.create(
                model="tts-1",
                voice="onyx",
                input=self.text[:4096],  # API limit
            )

            # Write to temp file
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tmp_path = tmp.name
            try:
                tmp.write(response.content)
                tmp.close()

                # Route to BT speaker if available
                bt_sink = detect_bt_sink()
                if bt_sink:
                    set_default_sink(bt_sink)

                # Play via mpg123 -> ffplay fallback
                try:
                    subprocess.run(
                        ["mpg123", "-q", tmp_path],
                        check=True, timeout=60,
                    )
                except (FileNotFoundError, subprocess.CalledProcessError):
                    try:
                        subprocess.run(
                            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", tmp_path],
                            check=True, timeout=60,
                        )
                    except FileNotFoundError:
                        self.error.emit("No audio player found (install mpg123 or ffmpeg)")
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))


class STTWorker(QThread):
    """Record from USB mic, transcribe via Whisper, return text."""
    transcription_ready = pyqtSignal(str)
    error = pyqtSignal(str)
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()

    def run(self):
        tmp_path = None
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                self.error.emit("OpenAI API key not configured")
                return

            # Record audio
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp_path = tmp.name
            tmp.close()

            cmd = [
                "arecord",
                "-D", MIC_DEVICE,
                "-f", MIC_FORMAT,
                "-r", str(MIC_SAMPLE_RATE),
                "-c", str(MIC_CHANNELS),
                "-d", str(MIC_DURATION),
                tmp_path,
            ]

            self.recording_started.emit()
            result = subprocess.run(cmd, capture_output=True, timeout=MIC_DURATION + 3)
            self.recording_stopped.emit()

            if result.returncode != 0:
                self.error.emit(f"Recording failed: {result.stderr.decode(errors='replace')}")
                return

            if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) < MIN_AUDIO_SIZE:
                self.error.emit("No speech detected")
                return

            # Transcribe
            client = OpenAI(api_key=api_key)
            with open(tmp_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en",
                )

            text = transcript.text.strip()
            if len(text) < 2:
                self.error.emit("No speech detected")
                return

            self.transcription_ready.emit(text)

        except Exception as e:
            self.error.emit(str(e))
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
