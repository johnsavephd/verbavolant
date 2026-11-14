"""Daily Latin saying -> Telegram. Picks a random saying not sent yet and records it in history.json."""
import html, json, os, random, sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

ROME = ZoneInfo("Europe/Rome")
DRY_RUN = os.environ.get("DRY_RUN") == "1"

# GitHub cron runs in UTC: it fires at 7 and 8 UTC and only sends when it is 9:00 in Rome.
if os.environ.get("GITHUB_EVENT_NAME") == "schedule" and datetime.now(ROME).hour != 9:
    print("Not 9:00 in Rome, exiting.")
    sys.exit(0)

sayings = json.load(open("sayings.json"))
history = json.load(open("history.json")) if os.path.exists("history.json") else []
used = {h["latin"] for h in history}
left = [s for s in sayings if s["latin"] not in used]
if not left:  # list exhausted: start a new cycle
    history, left = [], sayings
s = random.choice(left)

e = lambda k: html.escape(s[k], quote=False)
text = f"<b>{e('latin')}</b>\n<i>{e('pronunciation')}</i>\n\n“{e('translation')}”\n\n{e('explanation')}"

if DRY_RUN:
    print(text)
    sys.exit(0)

r = requests.post(
    f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
    json={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text, "parse_mode": "HTML",
          "disable_web_page_preview": True},
    timeout=30,
)
r.raise_for_status()

history.append({"date": datetime.now(ROME).date().isoformat(), "latin": s["latin"]})
json.dump(history, open("history.json", "w"), ensure_ascii=False, indent=1)
print("Sent:", s["latin"], f"({len(left) - 1} left in this cycle)")
