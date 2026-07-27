import os
import httpx

def send_telegram_alert(token: str, chat_id: str, message: str, image_path: str = None):
    """
    Dispatches alert text and optional camera snapshot directly to a Telegram Channel or Chat.
    Uses httpx for non-blocking HTTP requests.
    """
    if not token or not chat_id:
        print("[Telegram Notification] Skipped (Token or Chat ID not configured)")
        return False
        
    try:
        base_url = f"https://api.telegram.org/bot{token}"
        
        # If there is a snapshot, send Photo. Otherwise, send Message.
        if image_path and os.path.exists(image_path):
            url = f"{base_url}/sendPhoto"
            files = {"photo": (os.path.basename(image_path), open(image_path, "rb"), "image/jpeg")}
            data = {"chat_id": chat_id, "caption": message, "parse_mode": "HTML"}
            response = httpx.post(url, data=data, files=files, timeout=10.0)
        else:
            url = f"{base_url}/sendMessage"
            data = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
            response = httpx.post(url, data=data, timeout=10.0)
            
        if response.status_code == 200:
            print("[Telegram Notification] Alert dispatched successfully.")
            return True
        else:
            print(f"[Telegram Notification] Failed (Status {response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"[Telegram Notification] Connection error: {e}")
        return False
