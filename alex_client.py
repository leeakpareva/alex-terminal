"""
ALEX Terminal - Control API Client
Communicates with ALEX via the Control API on port 9090.
"""

import os
import requests


API_BASE = "http://127.0.0.1:9090"
TIMEOUT_HEALTH = 5
TIMEOUT_COMMAND = 120  # ALEX can take a while to respond


class AlexClient:
    def __init__(self):
        self.base_url = API_BASE
        self.token = os.environ.get("ALEX_API_TOKEN")

    def _headers(self, terminal=True):
        headers = {"Content-Type": "application/json"}
        if terminal:
            headers["X-Terminal"] = "true"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def health_check(self):
        """Check if ALEX is online. Returns dict or None."""
        try:
            resp = requests.get(
                f"{self.base_url}/api/health",
                headers=self._headers(),
                timeout=TIMEOUT_HEALTH,
            )
            if resp.status_code == 200:
                return resp.json()
        except requests.RequestException:
            pass
        return None

    def send_message(self, text):
        """
        Send a message to ALEX via /api/command.
        Returns (response_text, error_string).
        """
        try:
            resp = requests.post(
                f"{self.base_url}/api/command",
                json={
                    "message": text,
                    "send_to_telegram": False,
                },
                headers=self._headers(),
                timeout=TIMEOUT_COMMAND,
            )
            data = resp.json()
            if resp.status_code == 200 and data.get("success"):
                return data.get("response", ""), None
            else:
                return None, data.get("error", f"HTTP {resp.status_code}")
        except requests.Timeout:
            return None, "Request timed out"
        except requests.ConnectionError:
            return None, "Cannot connect to ALEX"
        except Exception as e:
            return None, str(e)

    def get_terminal_messages(self):
        """Fetch queued autonomous messages from ALEX."""
        try:
            resp = requests.get(
                f"{self.base_url}/api/terminal-messages",
                headers=self._headers(),
                timeout=TIMEOUT_HEALTH,
            )
            if resp.status_code == 200:
                return resp.json().get("messages", [])
        except requests.RequestException:
            pass
        return []
