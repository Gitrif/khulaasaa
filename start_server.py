"""
Khulaasaa Server & Tunnel Launcher.

This script:
1. Launches `cloudflared.exe` to expose port 8300.
2. Extracts the live `https://<subdomain>.trycloudflare.com` URL.
3. Automatically updates `APP_URL` in `.env`.
4. Updates Telegram's "Open Khulaasaa" Mini App menu button via Bot API.
5. Launches `uvicorn main:app --reload --port 8300`.
"""
import os
import re
import sys
import time
import subprocess
import requests

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(ROOT_DIR, ".env")
CLOUDFLARED = os.path.join(ROOT_DIR, "cloudflared.exe")

def update_env_file(key: str, value: str):
    if not os.path.exists(ENV_FILE):
        return
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    updated = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(f"{key}={value}\n")
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    os.environ[key] = value

def set_telegram_menu_button(bot_token: str, app_url: str):
    try:
        url = f"https://api.telegram.org/bot{bot_token}/setChatMenuButton"
        payload = {
            "menu_button": {
                "type": "web_app",
                "text": "Open Khulaasaa",
                "web_app": {"url": app_url}
            }
        }
        res = requests.post(url, json=payload, timeout=10)
        data = res.json()
        if data.get("ok"):
            print(f"[OK] Telegram Mini App URL updated to: {app_url}")
        else:
            print(f"[WARN] Failed to update Telegram menu button: {data}")
    except Exception as exc:
        print(f"[ERROR] Could not update Telegram menu button: {exc}")

def main():
    if not os.path.exists(CLOUDFLARED):
        print(f"[ERROR] {CLOUDFLARED} not found! Starting uvicorn only...")
        subprocess.run([sys.executable, "-m", "uvicorn", "main:app", "--reload", "--port", "8300"])
        return

    print("=" * 65)
    print("Starting Cloudflare Tunnel...")
    cf_proc = subprocess.Popen(
        [CLOUDFLARED, "tunnel", "--url", "http://localhost:8300"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )

    tunnel_url = None
    start_time = time.time()
    print("Waiting for Cloudflare Tunnel URL...")

    # Read output until the URL appears
    while time.time() - start_time < 30:
        line = cf_proc.stdout.readline()
        if not line:
            break
        match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
        if match:
            tunnel_url = match.group(0)
            break

    if not tunnel_url:
        print("[WARN] Could not retrieve trycloudflare URL within 30s.")
    else:
        print(f"[OK] Tunnel active: {tunnel_url}")
        update_env_file("APP_URL", tunnel_url)

        # Update Telegram Menu Button immediately
        from dotenv import dotenv_values
        env_vars = dotenv_values(ENV_FILE)
        token = env_vars.get("TELEGRAM_BOT_TOKEN")
        if token:
            set_telegram_menu_button(token, tunnel_url)

    print("=" * 65)
    print("Starting Uvicorn Server on http://localhost:8300 ...")
    print("Press Ctrl+C to stop both server and tunnel.")
    print("=" * 65)

    try:
        subprocess.run([sys.executable, "-m", "uvicorn", "main:app", "--reload", "--port", "8300"])
    finally:
        cf_proc.terminate()
        print("\nCloudflare tunnel terminated.")

if __name__ == "__main__":
    main()
