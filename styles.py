"""
ALEX Terminal - Dark Terminal Theme (QSS Stylesheet)
"""

DARK_THEME = """
QMainWindow {
    background-color: #1a1a2e;
}

QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: 'Monospace', 'Courier New', monospace;
}

/* Top bar */
QLabel#titleLabel {
    color: #00ff88;
    font-size: 14px;
    font-weight: bold;
    padding: 2px 6px;
}

QLabel#statusDot {
    font-size: 12px;
    padding: 2px 6px;
}

/* Chat area */
QTextBrowser#chatArea {
    background-color: #0f0f23;
    color: #e0e0e0;
    border: 1px solid #2a2a4a;
    border-radius: 4px;
    padding: 6px;
    font-size: 13px;
    selection-background-color: #3a3a5a;
}

/* Input field */
QLineEdit#inputField {
    background-color: #16213e;
    color: #ffffff;
    border: 2px solid #2a2a4a;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 14px;
}

QLineEdit#inputField:focus {
    border: 1px solid #00ff88;
}

/* Send button */
QPushButton#sendBtn {
    background-color: #00ff88;
    color: #1a1a2e;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: bold;
    font-size: 13px;
}

QPushButton#sendBtn:hover {
    background-color: #00cc6a;
}

QPushButton#sendBtn:pressed {
    background-color: #009950;
}

QPushButton#sendBtn:disabled {
    background-color: #2a2a4a;
    color: #666;
}

/* Mic button */
QPushButton#micBtn {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #2a2a4a;
    border-radius: 4px;
    padding: 8px 12px;
    font-size: 13px;
}

QPushButton#micBtn:hover {
    border-color: #00ff88;
    color: #00ff88;
}

QPushButton#micBtn:pressed, QPushButton#micBtn:checked {
    background-color: #ff4444;
    color: white;
    border-color: #ff4444;
}

/* Voice toggle button */
QPushButton#voiceBtn {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #2a2a4a;
    border-radius: 4px;
    padding: 8px 12px;
    font-size: 13px;
}

QPushButton#voiceBtn:hover {
    border-color: #00ff88;
}

QPushButton#voiceBtn[voiceOn="true"] {
    color: #00ff88;
    border-color: #00ff88;
}

/* Scrollbar */
QScrollBar:vertical {
    background-color: #0f0f23;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #2a2a4a;
    border-radius: 5px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #3a3a5a;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
"""
