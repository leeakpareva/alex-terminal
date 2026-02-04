# ALEX Terminal

Desktop voice/chat UI for [ALEX](https://github.com/leeakpareva/alex) AI agent on Raspberry Pi.

A PyQt5 app that provides a terminal-style chat interface with voice input (Whisper STT) and output (OpenAI TTS) through a Bluetooth speaker.

## Features

- **Text chat** with ALEX via the Control API (port 9090)
- **Voice output** through Bluetooth speaker (K07) using OpenAI TTS with the "onyx" voice
- **Voice input** via USB microphone using OpenAI Whisper transcription
- **Autonomous notifications** from ALEX heartbeat tasks (market updates, briefings, alerts)
- **Separate conversation** context from Telegram — terminal and Telegram chats are independent
- **Terminal-aware responses** — ALEX knows it's a text-only interface and gives concise, focused answers
- **Dark terminal theme** with green ALEX text on navy background
- **Auto-launch** on Pi startup via labwc autostart

## Screenshot

```
┌─────────────────────────────────────────────┐
│ ALEX - Global Economist            ONLINE   │
├─────────────────────────────────────────────┤
│                                             │
│  Connected to ALEX (uptime: 2h 15m)        │
│                                             │
│  You: what is the price of bitcoin?         │
│                                             │
│  ALEX: Bitcoin is trading at $72,041 USD.   │
│                                             │
├─────────────────────────────────────────────┤
│ [Type a message...    ] [Send] [Mic] [Voice]│
└─────────────────────────────────────────────┘
```

## Requirements

- Raspberry Pi 5 (or any Linux with a display)
- Python 3.11+ with PyQt5 (system-wide)
- ALEX service running on port 9090
- OpenAI API key (for TTS/STT)
- Optional: Bluetooth speaker, USB microphone

## Setup

```bash
# Create venv (inherits system PyQt5)
python3 -m venv --system-site-packages venv

# Install dependencies
venv/bin/pip install openai requests python-dotenv

# Run
venv/bin/python3 alex_terminal.py
```

Ensure your OpenAI API key is in `~/.env`:
```
OPENAI_API_KEY=sk-...
```

## Files

| File | Purpose |
|------|---------|
| `alex_terminal.py` | Main PyQt5 app — window, chat, input, signals |
| `alex_client.py` | HTTP client for ALEX Control API |
| `voice_engine.py` | TTS (OpenAI onyx) + STT (Whisper) with QThread workers |
| `autonomous.py` | Polls for proactive messages from ALEX heartbeat tasks |
| `styles.py` | Dark terminal theme (QSS stylesheet) |

## Commands

Type these in the input field:

| Command | Effect |
|---------|--------|
| `/voice` | Toggle voice output on/off |
| `/clear` | Clear chat history |
| `/status` | Show ALEX health info |

## How It Works

1. Messages are sent to ALEX via `POST /api/command` with the `X-Terminal: true` header
2. This routes to a separate `terminal-chat` conversation (independent from Telegram)
3. ALEX receives terminal context instructions — be concise, avoid visual tools, format for small screens
4. Responses are cleaned up (duplicate lines and verbose tool narration stripped)
5. If voice is enabled, responses are spoken through the Bluetooth speaker via mpg123

### Autonomous Messages

When ALEX runs scheduled heartbeat tasks (morning briefing, market alerts, etc.), the results are:
1. Written to `~/.alex/terminal-queue.json` by `heartbeat.js`
2. Polled every 5 seconds by the terminal's `AutonomousPoller`
3. Displayed in the chat and spoken aloud if voice is on

### Marker File

The terminal writes its PID to `~/.alex/terminal-active` on startup and removes it on close. The heartbeat system checks for this file before queuing messages.

## Audio Setup

### Bluetooth Speaker (K07)

```bash
# Connect
bluetoothctl connect 3E:03:DA:9B:5B:8D

# Verify sink appeared
pactl list short sinks

# Set as default
pactl set-default-sink bluez_output.3E_03_DA_9B_5B_8D.1
```

The terminal auto-detects and routes to the Bluetooth sink on startup.

### USB Microphone

Configured for C-Media USB PnP Sound Device at `hw:2,0` (48kHz, mono, S16_LE). Recording is 5 seconds per press of the Mic button.

## Auto-Launch

Added to `~/.config/labwc/autostart`:
```bash
sleep 5 && /home/head/alex-terminal/venv/bin/python3 /home/head/alex-terminal/alex_terminal.py &
```

Desktop launcher at `~/.local/share/applications/alex-terminal.desktop`.

## License

MIT — Part of the [ALEX / NAVADA](https://github.com/leeakpareva/alex) ecosystem.
