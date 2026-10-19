#!/usr/bin/env python3
"""
Telegram Gateway for Gemini Studio AI
Provides bidirectional bridge between Telegram Bot and Google AI Studio (Gemini 3.8 / 2.5 Flash).
Can run locally or on a VPS/Server with 0 external dependencies (uses standard library urllib).
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
import urllib.parse

# Default Configuration
DEFAULT_GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
CONFIG_FILE = "gateway_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "tg_bot_token": os.environ.get("TG_BOT_TOKEN", ""),
        "gemini_api_key": DEFAULT_GEMINI_KEY,
        "model": DEFAULT_MODEL,
        "allowed_chat_ids": []
    }

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def call_gemini(api_key: str, model: str, prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "РњРѕРґРµР»СЊ РІРµСЂРЅСѓР»Р° РїСѓСЃС‚РѕР№ РѕС‚РІРµС‚.")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        return f"вљ пёЏ РћС€РёР±РєР° Gemini API ({e.code}): {err_body}"
    except Exception as e:
        return f"вљ пёЏ РћС€РёР±РєР° РІС‹Р·РѕРІР° Gemini: {str(e)}"

def tg_api(token: str, method: str, params: dict = None) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    headers = {"Content-Type": "application/json"}
    data = json.dumps(params).encode("utf-8") if params else None
    req = urllib.request.Request(url, data=data, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "description": str(e)}

def send_tg_message(token: str, chat_id: int, text: str):
    # Try sending with HTML formatting first
    res = tg_api(token, "sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    })
    # If formatting fails, fallback to plain text
    if not res.get("ok"):
        tg_api(token, "sendMessage", {
            "chat_id": chat_id,
            "text": text
        })

def main():
    print("=" * 60)
    print("вљЎ Gemini Studio AI вЂ” Telegram Gateway Daemon")
    print("=" * 60)
    
    config = load_config()
    token = config.get("tg_bot_token")
    
    if not token:
        print("\n[!] РўРѕРєРµРЅ Telegram-Р±РѕС‚Р° РЅРµ РЅР°Р№РґРµРЅ РІ РєРѕРЅС„РёРіСѓСЂР°С†РёРё.")
        token = input("Р’РІРµРґРёС‚Рµ Bot Token РѕС‚ @BotFather: ").strip()
        if not token:
            print("[x] РўРѕРєРµРЅ РЅРµ СѓРєР°Р·Р°РЅ. Р—Р°РІРµСЂС€РµРЅРёРµ СЂР°Р±РѕС‚С‹.")
            sys.exit(1)
        config["tg_bot_token"] = token
        save_config(config)

    # Test bot token
    me = tg_api(token, "getMe")
    if not me.get("ok"):
        print(f"[x] РќРµРґРµР№СЃС‚РІРёС‚РµР»СЊРЅС‹Р№ С‚РѕРєРµРЅ Telegram API: {me.get('description')}")
        sys.exit(1)

    bot_user = me["result"]["username"]
    print(f"\n[+] Telegram Gateway СѓСЃРїРµС€РЅРѕ Р·Р°РїСѓС‰РµРЅ!")
    print(f"[+] Р‘РѕС‚: @{bot_user} ({me['result'].get('first_name')})")
    print(f"[+] РњРѕРґРµР»СЊ Gemini: {config.get('model', DEFAULT_MODEL)}")
    print("[+] РћР¶РёРґР°РЅРёРµ СЃРѕРѕР±С‰РµРЅРёР№ РѕС‚ РїРѕР»СЊР·РѕРІР°С‚РµР»РµР№...\n")

    offset = 0
    while True:
        try:
            updates = tg_api(token, "getUpdates", {
                "offset": offset,
                "timeout": 30,
                "limit": 50
            })
            
            if not updates.get("ok"):
                time.sleep(3)
                continue

            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message")
                if not msg or "text" not in msg:
                    continue

                chat_id = msg["chat"]["id"]
                user = msg.get("from", {}).get("username", str(chat_id))
                text = msg["text"].strip()

                print(f"[{time.strftime('%H:%M:%S')}] [@{user}]: {text}")

                if text == "/start":
                    welcome = (
                        "рџ‘‹ <b>Р”РѕР±СЂРѕ РїРѕР¶Р°Р»РѕРІР°С‚СЊ РІ Gemini Studio AI Gateway!</b>\n\n"
                        f"РЇ РїРѕРґРєР»СЋС‡РµРЅ Рє РјРѕРґРµР»Рё <b>{config.get('model', DEFAULT_MODEL)}</b>.\n"
                        "РћС‚РїСЂР°РІСЊС‚Рµ РјРЅРµ Р»СЋР±РѕР№ РІРѕРїСЂРѕСЃ РёР»Рё Р·Р°РґР°С‡Сѓ, Рё СЏ РјРіРЅРѕРІРµРЅРЅРѕ СЃС„РѕСЂРјРёСЂСѓСЋ РѕС‚РІРµС‚!\n\n"
                        "РљРѕРјР°РЅРґС‹:\n"
                        "/model вЂ” С‚РµРєСѓС‰Р°СЏ РјРѕРґРµР»СЊ\n"
                        "/help вЂ” СЃРїСЂР°РІРєР°"
                    )
                    send_tg_message(token, chat_id, welcome)
                    continue

                if text == "/help":
                    help_text = (
                        "рџ’Ў <b>РЎРїСЂР°РІРєР° РїРѕ С€Р»СЋР·Сѓ:</b>\n\n"
                        "вЂў Р’С‹ РјРѕР¶РµС‚Рµ РѕР±С‰Р°С‚СЊСЃСЏ СЃ РјРѕРґРµР»СЊСЋ РїСЂСЏРјРѕ Р·РґРµСЃСЊ.\n"
                        "вЂў РћС‚РІРµС‚С‹ РіРµРЅРµСЂРёСЂСѓСЋС‚СЃСЏ С‡РµСЂРµР· РѕС„РёС†РёР°Р»СЊРЅС‹Р№ Google AI Studio API.\n"
                        "вЂў Р’Р°С€ Chat ID: <code>" + str(chat_id) + "</code>"
                    )
                    send_tg_message(token, chat_id, help_text)
                    continue

                if text == "/model":
                    send_tg_message(token, chat_id, f"РўРµРєСѓС‰Р°СЏ РјРѕРґРµР»СЊ: <code>{config.get('model', DEFAULT_MODEL)}</code>")
                    continue

                # Notify user that model is thinking
                tg_api(token, "sendChatAction", {"chat_id": chat_id, "action": "typing"})

                # Call Gemini
                reply = call_gemini(config["gemini_api_key"], config.get("model", DEFAULT_MODEL), text)
                send_tg_message(token, chat_id, reply)

        except KeyboardInterrupt:
            print("\n[+] Р—Р°РІРµСЂС€РµРЅРёРµ СЂР°Р±РѕС‚С‹ С€Р»СЋР·Р°.")
            break
        except Exception as e:
            print(f"[!] РћС€РёР±РєР° С†РёРєР»Р° polling: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
