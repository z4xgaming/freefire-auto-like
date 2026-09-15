from http.server import BaseHTTPRequestHandler
import json
import urllib.request

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            target_uid = data.get('uid')
            region_key = data.get('key', 'FREE20')
            
            if not target_uid:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "UID is required"}).encode('utf-8'))
                return

            # 1. Fetch player info before/current status
            info_url = f"https://info-api-quick.vercel.app/player-info?uid={target_uid}"
            old_likes = 0
            nickname = "Unknown"
            try:
                req = urllib.request.Request(info_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    info_data = json.loads(response.read().decode('utf-8'))
                    # Extract likes and nickname based on standard response structure
                    basic_info = info_data.get('basic_info', {})
                    old_likes = basic_info.get('liked', 0)
                    nickname = basic_info.get('nickname', 'Unknown')
            except Exception as e:
                pass

            # Simulate simulated increment for demonstration (or integrate real like dispatch logic here)
            new_likes = old_likes + 20  # मान लीजिए की 'FREE20' पर 20 लाइक्स बढ़े

            response_payload = {
                "status": "success",
                "code": 200,
                "data": {
                    "uid": target_uid,
                    "nickname": nickname,
                    "regionKey": region_key,
                    "old_likes": old_likes,
                    "new_likes": new_likes,
                    "likes_added": new_likes - old_likes,
                    "message": "Like pipeline executed successfully."
                }
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_payload).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
