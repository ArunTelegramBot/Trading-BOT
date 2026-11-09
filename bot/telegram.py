import json
import urllib.parse
import urllib.request

def send_message(token: str, chat_id: str, text: str):
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read()).get("ok", False)
