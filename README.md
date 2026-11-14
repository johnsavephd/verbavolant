# Verba Volant
Every morning at 9:00 (Rome): a random Latin saying with translation, pronunciation and context, on Telegram.

## Setup
1. Telegram: scrivi a @BotFather → /newbot → copia il token. Scrivi un messaggio al tuo bot, poi apri
   `https://api.telegram.org/bot<TOKEN>/getUpdates` e copia `chat.id`.
2. Repo → Settings → Secrets and variables → Actions: aggiungi `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
3. Actions → "Verba Volant daily" → Run workflow per il primo test.

## Landing page
`docs/index.html` is a single static file. Publish it with GitHub Pages (Settings → Pages → Branch: main, folder: /docs). The button points to https://t.me/verbavolant.
