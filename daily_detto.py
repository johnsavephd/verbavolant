"""Daily Latin saying -> Telegram. Picks a random saying not sent yet and records it in history.json.

If the saying has a public-domain painting from Wikimedia Commons, it is sent as a photo with the
text as caption; if the image cannot be fetched or sent, the text goes out alone.
"""
import html, json, os, random, re, sys
from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests

ROME = ZoneInfo("Europe/Rome")
DRY_RUN = os.environ.get("DRY_RUN") == "1"
FORCE = os.environ.get("FORCE_SAYING", "").strip()  # manual preview of one saying, not recorded
UA = {"User-Agent": "VerbaVolantBot/1.0 (https://github.com/johnsavephd/verbavolant)"}

sayings = json.load(open("sayings.json"))
history = json.load(open("history.json")) if os.path.exists("history.json") else []
now = datetime.now(ROME)

if FORCE:
    match = [x for x in sayings if x["latin"].lower() == FORCE.lower()]
    if not match:
        sys.exit(f"No saying called {FORCE!r} in sayings.json")
    s = match[0]
else:
    # Scheduled runs: GitHub may start them late, so several runs are scheduled.
    # Send on the first one from 7:30 Rome time onwards, and only if nothing was sent today.
    if os.environ.get("GITHUB_EVENT_NAME") == "schedule":
        if (now.hour, now.minute) < (7, 30):
            print("Too early in Rome, exiting.")
            sys.exit(0)
        if any(h["date"] == now.date().isoformat() for h in history):
            print("Already sent today, exiting.")
            sys.exit(0)
    used = {h["latin"] for h in history}
    left = [x for x in sayings if x["latin"] not in used]
    if not left:  # list exhausted: start a new cycle
        history, left = [], sayings
    s = random.choice(left)

e = lambda k: html.escape(s[k], quote=False)
text = (
    f"{s['icon']} <b>{e('latin')}</b>\n<i>{e('pronunciation')}</i>\n\n"
    f"“{e('translation')}”\n\n"
    f"<b>Origin.</b> {e('origin')}\n\n"
    f"<b>Today.</b> {e('today')}"
)
credit = f"🖼️ <i>{e('credit')}</i>" if s.get("credit") else ""

if DRY_RUN:
    print(text + ("\n\n" + credit if credit else ""))
    if s.get("image"):
        print("IMAGE:", s["image"])
    sys.exit(0)

API = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}"
CHAT = os.environ["TELEGRAM_CHAT_ID"]


def visible_len(markup):
    return len(html.unescape(re.sub(r"<[^>]+>", "", markup)))


def tg(method, **kw):
    r = requests.post(f"{API}/{method}", timeout=60, **kw)
    if not r.ok:
        raise RuntimeError(f"Telegram {method} error {r.status_code}: {r.json().get('description', r.text)}")


def send_text(body):
    tg("sendMessage", json={"chat_id": CHAT, "text": body, "parse_mode": "HTML",
                            "disable_web_page_preview": True})


def fetch_image(name):
    url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(name)}?width=1280"
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    if not r.headers.get("content-type", "").startswith("image/"):
        raise RuntimeError(f"Not an image: {r.headers.get('content-type')}")
    return r.content


sent_with_image = False
if s.get("image"):
    try:
        img = fetch_image(s["image"])
        full = text + "\n\n" + credit
        if visible_len(full) <= 1024:  # Telegram caption limit
            tg("sendPhoto", data={"chat_id": CHAT, "caption": full, "parse_mode": "HTML"},
               files={"photo": ("painting.jpg", img)})
        else:
            tg("sendPhoto", data={"chat_id": CHAT, "caption": credit, "parse_mode": "HTML"},
               files={"photo": ("painting.jpg", img)})
            send_text(text)
        sent_with_image = True
    except Exception as err:  # never lose a day because of an image
        print("Image failed, sending text only:", err)

try:
    if not sent_with_image:
        send_text(text + ("\n\n" + credit if credit else ""))
except RuntimeError as err:
    sys.exit(str(err))

if FORCE:
    print("Preview sent (not recorded in history):", s["latin"])
    sys.exit(0)

history.append({"date": now.date().isoformat(), "latin": s["latin"]})
json.dump(history, open("history.json", "w"), ensure_ascii=False, indent=1)
print("Sent:", s["latin"], "with image" if sent_with_image else "", f"({len(left) - 1} left in this cycle)")
