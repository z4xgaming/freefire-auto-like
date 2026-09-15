# api/index.py
# Vercel Python Serverless Function for Free Fire IND Auto-Like Panel

import json
import urllib.request
import urllib.error
import urllib.parse
from http.server import BaseHTTPRequestHandler

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
INFO_API_BASE = "https://info-api-quick.vercel.app/player-info"
LIKE_ENDPOINT = "https://client.ind.freefiremobile.com/LikeProfile"

# Default access key — used if the user leaves the session field empty
DEFAULT_SESSION_KEY = "FREE20"

# Set to True to skip the real like request (useful for UI testing)
MOCK_MODE = False


# ------------------------------------------------------------------
# Helper: Fetch player info (name + current likes)
# ------------------------------------------------------------------
def fetch_player_info(uid: str):
    """
    Calls the info-api-quick service and returns (player_name, likes).
    Raises an exception on failure.
    """
    url = f"{INFO_API_BASE}?uid={urllib.parse.quote(uid)}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (FF-Auto-Liker/1.0)",
            "Accept": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("utf-8")
        data = json.loads(raw)

    player_name = (
        data.get("nickname")
        or data.get("name")
        or data.get("player_name")
        or "Unknown"
    )
    likes = (
        data.get("likes")
        or data.get("Like")
        or data.get("like_count")
        or 0
    )
    return str(player_name), int(likes)


# ------------------------------------------------------------------
# Helper: Send a like to the IND LikeProfile endpoint (best effort)
# ------------------------------------------------------------------
def send_like(uid: str, session_key: str):
    """
    Attempts to POST a like request to the Free Fire IND server.
    Returns True on HTTP 2xx, False otherwise.
    """
    if MOCK_MODE:
        return True  # Simulate success for UI testing

    payload = json.dumps({
        "target_uid": uid,
        "region": "IND",
        "session_key": session_key,
    }).encode("utf-8")

    req = urllib.request.Request(
        LIKE_ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12; Pixel 6)",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB49",
            "Authorization": f"Bearer {session_key}",
            "X-Access-Key": session_key,   # 👈 FREE20 travels here too
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError:
        return False
    except Exception:
        return False


# ------------------------------------------------------------------
# Vercel Handler
# ------------------------------------------------------------------
class handler(BaseHTTPRequestHandler):

    def _send_json(self, status: int, body: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        """POST /api  →  body: {uid, session_key}"""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            body = json.loads(raw_body) if raw_body else {}
        except Exception:
            self._send_json(400, {"error": "Invalid JSON body"})
            return

        uid = str(body.get("uid", "")).strip()
        session_key = str(body.get("session_key", "")).strip()

        # 👇 FREE20 fallback — अगर user ने key खाली छोड़ी तो FREE20 use होगी
        if not session_key:
            session_key = DEFAULT_SESSION_KEY

        if not uid:
            self._send_json(400, {"error": "uid is required"})
            return

        # ----- 1. Fetch old likes & player name -----
        try:
            player_name, old_likes = fetch_player_info(uid)
        except Exception as e:
            self._send_json(502, {
                "error": f"Failed to fetch player info: {str(e)}"
            })
            return

        # ----- 2. Attempt to send the like -----
        like_sent = False
        like_error = None
        try:
            like_sent = send_like(uid, session_key)
        except Exception as e:
            like_error = str(e)

        # ----- 3. Re-fetch likes (or simulate +1) -----
        if like_sent:
            try:
                _, new_likes = fetch_player_info(uid)
            except Exception:
                new_likes = old_likes + 1
        else:
            new_likes = old_likes

        # ----- 4. Build response -----
        response = {
            "success": like_sent,
            "player_name": player_name,
            "uid": uid,
            "old_likes": old_likes,
            "new_likes": new_likes,
            "likes_gained": max(0, new_likes - old_likes),
            "key_used": session_key,   # 👈 debug के लिए frontend को भेज दो
            "error": like_error,
        }

        self._send_json(200, response)
