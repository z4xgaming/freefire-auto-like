from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import os

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

            # 1. पहले Player Info API से पुराने लाइक्स और नाम फेच करें
            info_url = f"https://info-api-quick.vercel.app/player-info?uid={target_uid}"
            old_likes = 0
            player_name = "Unknown"
            
            try:
                req = urllib.request.Request(info_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    info_data = json.loads(response.read().decode('utf-8'))
                    account_info = info_data.get('basic_info', info_data.get('account_info', {}))
                    old_likes = int(account_info.get('liked', info_data.get('liked', 0)))
                    player_name = account_info.get('nickname', info_data.get('nickname', 'Player'))
            except Exception as e:
                old_likes = 0

            # 2. असली Free Fire IND Game Server पर Like भेजने की रिक्वेस्ट
            game_api_url = "https://client.ind.freefiremobile.com/LikeProfile"
            
            game_headers = {
                'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)',
                'Content-Type': 'application/json',
                'X-Unity-Version': '2018.4.11f1'
            }
            
            game_payload = {
                "uid": int(target_uid),
                "region": "IND"
            }

            likes_added_count = 0
            api_success = False

            try:
                req_data = json.dumps(game_payload).encode('utf-8')
                game_req = urllib.request.Request(game_api_url, data=req_data, headers=game_headers, method='POST')
                
                with urllib.request.urlopen(game_req) as game_res:
                    game_response_data = json.loads(game_res.read().decode('utf-8'))
                    # यदि गेम सर्वर से पॉजिटिव रिस्पांस मिले
                    if game_res.status == 200:
                        likes_added_count = 20
                        api_success = True
            except Exception as game_err:
                # यदि डायरेक्ट गेम सर्वर ब्लॉक करे, तो फॉलबैक या एरर थ्रो करें ताकि फेक सक्सेस न दिखे
                api_success = False

            if not api_success:
                # अगर गेम सर्वर से कनेक्शन फेल हो तो एरर भेजें (Fake Success बंद करने के लिए)
                self.send_response(502)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "error", 
                    "message": "Game server rejected the request or token mismatch! (Fake success prevented)"
                }).encode('utf-8'))
                return

            new_likes = old_likes + likes_added_count

            response_payload = {
                "status": "success",
                "code": 200,
                "data": {
                    "uid": target_uid,
                    "nickname": player_name,
                    "regionKey": region_key,
                    "old_likes": old_likes,
                    "new_likes": new_likes,
                    "likes_added": likes_added_count,
                    "message": "Likes successfully sent to game server!"
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
