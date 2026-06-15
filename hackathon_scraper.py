#!/usr/bin/env python3
"""
Hackathon + Incubator Daily Scraper
Credentials injected via GitHub Secrets: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
"""
import os, json, hashlib, html, requests
from datetime import datetime, date
from bs4 import BeautifulSoup

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
SEEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".seen_items.json")
HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/124.0.0.0"}

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f: return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f: json.dump(list(seen), f)

def item_id(title, url):
    return hashlib.md5((title + "|" + url).encode()).hexdigest()

def get(url, timeout=10):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception as e:
        print("  [warn]", url, "->", e)
        return None

def scrape_devpost():
    items = []
    r = get("https://devpost.com/api/hackathons?status[]=upcoming&status[]=open&order_by=deadline&per_page=20")
    if not r: return items
    try:
        for h in r.json().get("hackathons", []):
            items.append({"title": h.get("title",""), "url": h.get("url",""), "deadline": h.get("submission_period_dates",""), "prize": h.get("prize_amount",""), "source": "Devpost"})
    except Exception as e: print("  [devpost]", e)
    return items

def scrape_mlh():
    items = []
    r = get("https://mlh.io/seasons/2026/events")
    if not r: return items
    soup = BeautifulSoup(r.text, "lxml")
    for event in soup.select(".event"):
        t = event.select_one(".event-name")
        l = event.select_one("a.event-link")
        d = event.select_one(".event-date")
        if t and l:
            items.append({"title": t.get_text(strip=True), "url": l.get("href",""), "deadline": d.get_text(strip=True) if d else "", "prize": "", "source": "MLH"})
    return items

def scrape_devfolio():
    items = []
    r = get("https://devfolio.co/api/search/hackathons/?is_open=true&page=1&per_page=20")
    if not r: return items
    try:
        for h in r.json().get("results", []):
            slug = h.get("slug","")
            items.append({"title": h.get("name",""), "url": "https://devfolio.co/hackathons/" + slug, "deadline": h.get("ends_at","")[:10] if h.get("ends_at") else "", "prize": "", "source": "Devfolio"})
    except Exception as e: print("  [devfolio]", e)
    return items

def scrape_unstop():
    items = []
    r = get("https://unstop.com/api/public/opportunity/search-result?opportunity=hackathons&per_page=20&page=1&deadline=open")
    if not r: return items
    try:
        for h in r.json().get("data", {}).get("data", []):
            items.append({"title": h.get("title",""), "url": "https://unstop.com/hackathons/" + h.get("slug",""), "deadline": h.get("end_date",""), "prize": str(h.get("prize_money","")), "source": "Unstop"})
    except Exception as e: print("  [unstop]", e)
    return items

def scrape_yc():
    items = []
    r = get("https://www.ycombinator.com/apply")
    if not r: return items
    soup = BeautifulSoup(r.text, "lxml")
    deadline = ""
    for tag in soup.find_all(["h1","h2","h3","p","span"]):
        t = tag.get_text(strip=True)
        if "deadline" in t.lower() or "batch" in t.lower():
            deadline = t[:120]; break
    items.append({"title": "Y Combinator - " + (deadline or "Check for current batch"), "url": "https://www.ycombinator.com/apply", "deadline": deadline, "prize": "120k USD + network", "source": "YC"})
    return items

INCUBATORS = [
    {"title": "Y Combinator (YC) - Apply", "url": "https://www.ycombinator.com/apply", "source": "YC", "note": "Check site for current batch deadline"},
    {"title": "Antler - Apply", "url": "https://www.antler.co/apply", "source": "Antler", "note": "Rolling applications"},
    {"title": "Techstars - Apply", "url": "https://www.techstars.com/apply", "source": "Techstars", "note": "Check site for open programs"},
    {"title": "Pioneer - Apply", "url": "https://pioneer.app", "source": "Pioneer", "note": "Rolling tournament, apply anytime"},
    {"title": "a16z Speedrun - Apply", "url": "https://speedrun.a16z.com", "source": "a16z", "note": "Check for open cohorts"},
    {"title": "Entrepreneur First (EF) - Apply", "url": "https://www.joinef.com/apply", "source": "EF", "note": "Check site for open cohorts"},
    {"title": "500 Global - Apply", "url": "https://500.co/accelerators", "source": "500 Global", "note": "Multiple programs worldwide"},
]

def get_static_incubators():
    return [{"title": i["title"], "url": i["url"], "deadline": i.get("note",""), "prize": "", "source": i["source"]} for i in INCUBATORS]

def send_telegram(text):
    if not TELEGRAM_TOKEN:
        print("[telegram] Token not set"); return
    r = requests.post("https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": False}, timeout=10)
    print("[telegram] sent" if r.ok else "[telegram] error " + str(r.status_code))

def chunk_messages(text, limit=4096):
    lines = text.split("\n")
    chunks, cur = [], ""
    for line in lines:
        if len(cur) + len(line) + 1 > limit:
            chunks.append(cur.strip()); cur = line + "\n"
        else:
            cur += line + "\n"
    if cur.strip(): chunks.append(cur.strip())
    return chunks

def main():
    print("[" + datetime.now().strftime("%Y-%m-%d %H:%M") + "] Starting...")
    seen = load_seen()
    all_items = []
    for name, fn in [("Devpost",scrape_devpost),("MLH",scrape_mlh),("Devfolio",scrape_devfolio),("Unstop",scrape_unstop),("YC",scrape_yc),("Incubators",get_static_incubators)]:
        print("  " + name + "...")
        try:
            r = fn(); print("    ->", len(r)); all_items.extend(r)
        except Exception as e:
            print("    -> error:", e)

    new_items = []
    for item in all_items:
        if not item.get("title") or not item.get("url"): continue
        uid = item_id(item["title"], item["url"])
        if uid not in seen:
            new_items.append(item); seen.add(uid)
    save_seen(seen)
    print("New:", len(new_items), "/", len(all_items))

    EMOJI = {"Devpost":"💻","MLH":"🏫","Devfolio":"🛠","Unstop":"🏆","YC":"🚀","Antler":"🌍","Techstars":"⭐","Pioneer":"🧭","a16z":"💰","EF":"🤝","500 Global":"🌐","Incubators":"🏢"}

    if not new_items:
        send_telegram("🔍 <b>Hackathon & Incubator Digest</b> - " + str(date.today()) + "\n\nNo new opportunities today!"); return

    by_source = {}
    for item in new_items: by_source.setdefault(item["source"], []).append(item)

    lines = ["🎯 <b>Hackathon & Incubator Digest</b> - " + str(date.today()) + "\n"]
    for source, items in by_source.items():
        emoji = EMOJI.get(source, "📌")
        lines.append("\n" + emoji + " <b>" + source + "</b> (" + str(len(items)) + " new)")
        for item in items[:10]:
            url = item["url"]
            title = html.escape(item["title"][:80])
            url = item["url"]
            deadline = html.escape(item.get("deadline", ""))
            prize = html.escape(str(item.get("prize", "")))
            entry = '  • <a href="' + url + '">' + title + '</a>'
            if deadline: entry += "\n    📅 " + deadline[:60]
            if prize: entry += " | 💵 " + prize
            lines.append(entry)
    lines.append("\n\n<i>Total: " + str(len(new_items)) + " new | HackathonBot</i>")

    for chunk in chunk_messages("\n".join(lines)):
        send_telegram(chunk)

if __name__ == "__main__":
    main()
