/**
 * Telegram Gateway for Gemini Studio AI (Node.js version)
 * Standalone bidirectional bridge between Telegram Bot and Google AI Studio.
 */

const fs = require('fs');
const path = require('path');

const CONFIG_FILE = path.join(__dirname, 'gateway_config.json');
const DEFAULT_KEY = process.env.GEMINI_API_KEY || "YOUR_GEMINI_API_KEY";
const DEFAULT_MODEL = process.env.GEMINI_MODEL || "gemini-3.8-flash";

function loadConfig() {
  if (fs.existsSync(CONFIG_FILE)) {
    try {
      return JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));
    } catch (e) {}
  }
  return {
    tg_bot_token: process.env.TG_BOT_TOKEN || "",
    gemini_api_key: DEFAULT_KEY,
    model: DEFAULT_MODEL
  };
}

async function callGemini(apiKey, model, prompt) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || res.statusText);
  }
  const data = await res.json();
  return data.candidates?.[0]?.content?.parts?.[0]?.text || "РџСѓСЃС‚РѕР№ РѕС‚РІРµС‚.";
}

async function tgApi(token, method, params = {}) {
  const url = `https://api.telegram.org/bot${token}/${method}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  return await res.json();
}

async function start() {
  const config = loadConfig();
  const token = config.tg_bot_token;
  if (!token) {
    console.error("[!] РЈРєР°Р¶РёС‚Рµ tg_bot_token РІ gateway_config.json РёР»Рё РїРµСЂРµРјРµРЅРЅРѕР№ РѕРєСЂСѓР¶РµРЅРёСЏ TG_BOT_TOKEN");
    process.exit(1);
  }

  const me = await tgApi(token, 'getMe');
  if (!me.ok) {
    console.error("[x] РћС€РёР±РєР° С‚РѕРєРµРЅР°:", me.description);
    process.exit(1);
  }

  console.log(`[+] Telegram Gateway Р·Р°РїСѓС‰РµРЅ! Р‘РѕС‚: @${me.result.username}`);

  let offset = 0;
  while (true) {
    try {
      const updates = await tgApi(token, 'getUpdates', { offset, timeout: 25 });
      if (updates.ok && updates.result) {
        for (const u of updates.result) {
          offset = u.update_id + 1;
          const msg = u.message;
          if (!msg || !msg.text) continue;

          const chatId = msg.chat.id;
          const text = msg.text.trim();
          console.log(`[Message from ${msg.chat.id}]: ${text}`);

          if (text === '/start') {
            await tgApi(token, 'sendMessage', {
              chat_id: chatId,
              text: `рџ‘‹ РџСЂРёРІРµС‚! РЇ С€Р»СЋР· Gemini Studio AI (${config.model}). РћС‚РїСЂР°РІСЊС‚Рµ РјРЅРµ РІРѕРїСЂРѕСЃ!`
            });
            continue;
          }

          await tgApi(token, 'sendChatAction', { chat_id: chatId, action: 'typing' });
          const reply = await callGemini(config.gemini_api_key, config.model, text);
          await tgApi(token, 'sendMessage', {
            chat_id: chatId,
            text: reply
          });
        }
      }
    } catch (e) {
      console.error("[Polling error]:", e.message);
      await new Promise(r => setTimeout(r, 2000));
    }
  }
}

if (require.main === module) {
  start();
}
