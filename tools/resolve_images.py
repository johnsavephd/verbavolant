"""Find a public-domain file on Wikimedia Commons for each saying in tools/image_plan.py.

Run by the "Resolve images" GitHub workflow (Wikimedia is reachable from GitHub runners).
- Sayings that already have an image are left alone.
- For each planned saying, tries the queries in order and keeps the first result that is
  public domain (or CC0) and at least 700 px wide.
- Writes the file name and credit into sayings.json and builds REVIEW.md with thumbnails,
  so the choices can be checked by eye on GitHub.
"""
import html, json, re, sys, time

import requests

sys.path.insert(0, "tools")
from image_plan import PLAN  # noqa: E402

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "VerbaVolantBot/1.0 (https://github.com/johnsavephd/verbavolant)"}


def clean(v):
    return html.unescape(re.sub(r"<[^>]+>", "", v or "")).strip()


def is_free(meta):
    lic = (meta.get("LicenseShortName", {}).get("value", "") + " " + meta.get("License", {}).get("value", "")).lower()
    return "public domain" in lic or lic.strip().startswith("pd") or " pd" in lic or "cc0" in lic


def search(q):
    params = {
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
        "gsrsearch": f"{q} filetype:bitmap", "gsrlimit": 8,
        "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 400,
    }
    r = requests.get(API, params=params, headers=UA, timeout=60)
    r.raise_for_status()
    pages = r.json().get("query", {}).get("pages", {})
    return sorted(pages.values(), key=lambda p: p.get("index", 99))


sayings = json.load(open("sayings.json"))
by_latin = {s["latin"]: s for s in sayings}
missing_in_list = [k for k in PLAN if k not in by_latin]
if missing_in_list:
    sys.exit(f"Plan entries not in sayings.json: {missing_in_list}")

rows, failed = [], []
for s in sayings:
    if s["latin"] not in PLAN:
        continue
    queries, credit = PLAN[s["latin"]]
    if s.get("image") and s.get("thumb"):
        rows.append((s, s["image"], s["thumb"], s.get("commons_info", "")))
        continue
    found = None
    for q in queries:
        try:
            for p in search(q):
                ii = (p.get("imageinfo") or [{}])[0]
                meta = ii.get("extmetadata", {})
                if ii.get("width", 0) >= 700 and is_free(meta):
                    found = (p["title"].removeprefix("File:"), ii.get("thumburl", ""),
                             f"{clean(meta.get('Artist', {}).get('value'))} | {clean(meta.get('DateTimeOriginal', {}).get('value'))} | {clean(meta.get('LicenseShortName', {}).get('value'))}")
                    break
        except Exception as err:
            print("Search error", s["latin"], q, err)
        time.sleep(0.3)
        if found:
            break
    if found:
        s["image"], s["thumb"], s["commons_info"] = found
        s["credit"] = credit
        rows.append((s, *found))
        print("OK  ", s["latin"], "->", found[0])
    else:
        failed.append((s["latin"], queries))
        print("FAIL", s["latin"])

json.dump(sayings, open("sayings.json", "w"), ensure_ascii=False, indent=1)

with open("REVIEW.md", "w") as f:
    f.write("# Paintings to review\n\nCheck that each picture is the painting named in the credit and fits the saying.\n\n")
    f.write(f"Found: {len(rows)}. Not found: {len(failed)}.\n\n")
    f.write("| Saying | Painting | Credit | Commons (artist, date, licence) |\n|---|---|---|---|\n")
    for s, name, thumb, info in rows:
        link = "https://commons.wikimedia.org/wiki/File:" + name.replace(" ", "_")
        f.write(f"| **{s['latin']}** | <a href=\"{link}\"><img src=\"{thumb}\" width=\"220\"></a> | {s.get('credit', '')} | {info} |\n")
    if failed:
        f.write("\n## Not found\n\n")
        for latin, qs in failed:
            f.write(f"- **{latin}**: tried {qs}\n")
print(f"Done: {len(rows)} found, {len(failed)} not found")
