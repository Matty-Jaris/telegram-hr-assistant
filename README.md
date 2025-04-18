# Telegram HR Assistant 🤖

> Low‑/no‑code workflow (n8n + OpenAI GPT‑4o) that chats with recruiters on my behalf.

## ✨ Features
- **Friendly, concise answers** following `prompts/tone_of_voice.md`.
- Sends my latest **CV** and answers **FAQ** automatically.
- Inline buttons to schedule a call or request a PDF profile.
- Hosted on **n8n.cloud** – no server maintenance.

## 🗂 Repo structure


## 🚀 Quick start
1. Create a Telegram bot via [@BotFather](https://t.me/BotFather) and copy the API token.
2. Sign up at <https://n8n.cloud> and import `workflow/telegram_hr_assistant.json`.
3. In n8n **Credential Manager** add:
   - *Telegram API* token
   - *OpenAI* API key
4. Activate the workflow – done!  
   Send `/start` to `@YourBotUsername` to test the conversation.

> **No local install needed** – everything runs in the browser.

## 🔐 Security / GDPR
See `docs/privacy.md` for data‑retention policy and a list of fields the bot never discloses.

## 📜 License
MIT – use freely, but remove private CV/FAQ content before forking.


