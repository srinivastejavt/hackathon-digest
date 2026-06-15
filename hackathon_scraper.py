#!/usr/bin/env python3
"""
Hackathon + Incubator + Accelerator + Cohort Daily Scraper
Covers: hackathons, crypto accelerators, AI accelerators, incubators, cohorts
Credentials injected via GitHub Secrets: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
"""

import os, json, html, requests
from datetime import datetime, date
from bs4 import BeautifulSoup

# ── CONFIG ────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
# ─────────────────────────────────────────────────────────────────────────────


def get(url, timeout=10):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"  [warn] GET {url} -> {e}")
        return None


# ── LIVE SCRAPERS ─────────────────────────────────────────────────────────────

def scrape_devpost():
    items = []
    r = get("https://devpost.com/api/hackathons?status[]=upcoming&status[]=open&order_by=deadline&per_page=20")
    if not r:
        return items
    try:
        for h in r.json().get("hackathons", []):
            items.append({
                "title": h.get("title", ""),
                "url": h.get("url", ""),
                "deadline": h.get("submission_period_dates", ""),
                "prize": h.get("prize_amount", ""),
                "source": "Devpost",
            })
    except Exception as e:
        print(f"  [devpost] {e}")
    return items


def scrape_mlh():
    items = []
    r = get("https://mlh.io/seasons/2026/events")
    if not r:
        return items
    soup = BeautifulSoup(r.text, "lxml")
    for event in soup.select(".event"):
        title_el = event.select_one(".event-name")
        link_el  = event.select_one("a.event-link")
        date_el  = event.select_one(".event-date")
        if title_el and link_el:
            items.append({
                "title": title_el.get_text(strip=True),
                "url": link_el.get("href", ""),
                "deadline": date_el.get_text(strip=True) if date_el else "",
                "prize": "",
                "source": "MLH",
            })
    return items


def scrape_unstop():
    items = []
    r = get("https://unstop.com/api/public/opportunity/search-result?opportunity=hackathons&per_page=20&page=1&deadline=open")
    if not r:
        return items
    try:
        for h in r.json().get("data", {}).get("data", []):
            items.append({
                "title": h.get("title", ""),
                "url": "https://unstop.com/hackathons/" + h.get("slug", ""),
                "deadline": h.get("end_date", ""),
                "prize": str(h.get("prize_money", "")),
                "source": "Unstop",
            })
    except Exception as e:
        print(f"  [unstop] {e}")
    return items


def scrape_dorahacks():
    items = []
    r = get("https://dorahacks.io/api/hackathon/list/?limit=20&status=open")
    if not r:
        return items
    try:
        data = r.json()
        for h in data.get("data", data.get("list", [])):
            slug = h.get("slug") or h.get("url_slug", "")
            items.append({
                "title": h.get("title", h.get("name", "")),
                "url": "https://dorahacks.io/hackathon/" + slug if slug else "https://dorahacks.io",
                "deadline": str(h.get("end_time", h.get("application_end", "")))[:10],
                "prize": str(h.get("prize_pool", "")),
                "source": "DoraHacks",
            })
    except Exception as e:
        print(f"  [dorahacks] {e}")
    return items


def scrape_ethglobal():
    items = []
    r = get("https://ethglobal.com/events/hackathons")
    if not r:
        return items
    try:
        soup = BeautifulSoup(r.text, "lxml")
        seen_urls = set()
        for card in soup.select("a[href*='/events/']"):
            title = card.get_text(strip=True)
            href = card.get("href", "")
            if title and href and len(title) > 3:
                url = href if href.startswith("http") else "https://ethglobal.com" + href
                if url not in seen_urls:
                    seen_urls.add(url)
                    items.append({"title": title[:80], "url": url, "deadline": "", "prize": "", "source": "ETHGlobal"})
    except Exception as e:
        print(f"  [ethglobal] {e}")
    return items[:10]


def scrape_yc():
    items = []
    r = get("https://www.ycombinator.com/apply")
    if not r:
        return items
    soup = BeautifulSoup(r.text, "lxml")
    deadline_text = ""
    for tag in soup.find_all(["h1", "h2", "h3", "p", "span"]):
        t = tag.get_text(strip=True)
        if "deadline" in t.lower() or "batch" in t.lower():
            deadline_text = t[:120]
            break
    items.append({
        "title": "Y Combinator -- " + (deadline_text or "Apply now"),
        "url": "https://www.ycombinator.com/apply",
        "deadline": deadline_text,
        "prize": "$500k investment",
        "source": "YC",
    })
    return items


# ── STATIC OPPORTUNITIES ──────────────────────────────────────────────────────

STATIC_OPPORTUNITIES = [,
    # CRYPTO HACKATHONS,
    {"title": "Colosseum -- Solana Hackathon", "url": "https://www.colosseum.org", "note": "Check for live hackathons", "category": "Crypto Hackathon"},
    {"title": "Encode Club -- Hackathons", "url": "https://www.encode.club", "note": "Web3 education + hackathons", "category": "Crypto Hackathon"},
    {"title": "Lablab.ai -- AI Hackathons", "url": "https://lablab.ai/event", "note": "AI-focused hackathons", "category": "AI Hackathon"},
    {"title": "HackerEarth -- Hackathons", "url": "https://www.hackerearth.com/challenges/hackathon/", "note": "Tech and AI hackathons", "category": "Hackathon"},
    # CRYPTO ACCELERATORS,
    {"title": "Colosseum -- Solana Accelerator", "url": "https://www.colosseum.org/accelerator", "note": "Rolling cohorts for Solana projects", "category": "Crypto Accelerator"},
    {"title": "Alliance DAO -- Crypto Accelerator", "url": "https://alliance.xyz/apply", "note": "Top crypto accelerator, rolling", "category": "Crypto Accelerator"},
    {"title": "Outlier Ventures -- Base Camp", "url": "https://outlierventures.io/base-camp/", "note": "12-week Web3 AI accelerator", "category": "Crypto Accelerator"},
    {"title": "Near Horizon -- Web3 Accelerator", "url": "https://near.org/horizon", "note": "NEAR ecosystem accelerator", "category": "Crypto Accelerator"},
    {"title": "Aptos Foundation -- Grants", "url": "https://aptosfoundation.org/grants", "note": "Aptos ecosystem funding", "category": "Crypto Accelerator"},
    {"title": "Sui Foundation -- Grants", "url": "https://sui.io/funding-grants", "note": "Sui ecosystem grants", "category": "Crypto Accelerator"},
    {"title": "TON Foundation -- Grants", "url": "https://grants.ton.org", "note": "TON/Telegram ecosystem grants", "category": "Crypto Accelerator"},
    {"title": "Binance Labs -- Incubation", "url": "https://labs.binance.com", "note": "Web3 incubation + investment", "category": "Crypto Accelerator"},
    {"title": "Polygon Village -- Accelerator", "url": "https://polygon.technology/village", "note": "Polygon ecosystem projects", "category": "Crypto Accelerator"},
    {"title": "a16z crypto -- Accelerator (CSX)", "url": "https://a16zcrypto.com/csx", "note": "10-week, $500k investment", "category": "Crypto Accelerator"},
    {"title": "Hedera HBAR Foundation -- Grants", "url": "https://www.hbarfoundation.org/apply", "note": "Hedera ecosystem grants", "category": "Crypto Accelerator"},
    # CRYPTO GRANTS,
    {"title": "Superteam Earn -- Bounties", "url": "https://earn.superteam.fun", "note": "Live Solana bounties, updated daily", "category": "Crypto Grants"},
    {"title": "Superteam -- Ecosystem Grants", "url": "https://superteam.fun/grants", "note": "Solana ecosystem grants", "category": "Crypto Grants"},
    {"title": "Solana Foundation -- Grants", "url": "https://solana.org/grants", "note": "Rolling grants for Solana builders", "category": "Crypto Grants"},
    {"title": "Ethereum Foundation -- ESP", "url": "https://esp.ethereum.foundation", "note": "Ecosystem Support Program, rolling", "category": "Crypto Grants"},
    {"title": "Paradigm -- Grants", "url": "https://www.paradigm.xyz/grants", "note": "Crypto research and dev grants", "category": "Crypto Grants"},
    {"title": "Chainlink BUILD", "url": "https://chain.link/build", "note": "Chainlink ecosystem grants", "category": "Crypto Grants"},
    {"title": "Filecoin Dev Grants", "url": "https://grants.filecoin.io", "note": "Rolling grants for decentralized storage", "category": "Crypto Grants"},
    {"title": "Wormhole -- xGrant", "url": "https://wormhole.com/grants/", "note": "Cross-chain project grants", "category": "Crypto Grants"},
    # AI ACCELERATORS,
    {"title": "AI Grant -- Apply", "url": "https://aigrant.com", "note": "Rolling; $10k-$250k for AI projects", "category": "AI Accelerator"},
    {"title": "AI2 Incubator -- Apply", "url": "https://www.ai2incubator.com", "note": "Allen Institute for AI, seed-stage", "category": "AI Accelerator"},
    {"title": "Conviction -- Embed Program", "url": "https://www.conviction.com/embed", "note": "6-month AI builder residency", "category": "AI Accelerator"},
    {"title": "Mozilla Builders -- AI", "url": "https://builders.mozilla.org", "note": "Trustworthy AI, $75k equity-free", "category": "AI Accelerator"},
    {"title": "Google for Startups -- AI First", "url": "https://startup.google.com/programs/ai-first/", "note": "Cloud credits + mentorship", "category": "AI Accelerator"},
    {"title": "Microsoft for Startups", "url": "https://www.microsoft.com/en-us/startups", "note": "Up to $150k Azure credits", "category": "AI Accelerator"},
    {"title": "Hugging Face -- Incubator", "url": "https://huggingface.co/incubator", "note": "Open-source AI cohort", "category": "AI Accelerator"},
    {"title": "Sequoia Arc -- AI Cohort", "url": "https://www.sequoiacap.com/arc/", "note": "Fast-track program for AI startups", "category": "AI Accelerator"},
    {"title": "Lightspeed Faction", "url": "https://lsvp.com/faction/", "note": "AI-native startups, rolling", "category": "AI Accelerator"},
    {"title": "OpenAI Startup Fund", "url": "https://openai.com/form/startup-fund-eoi/", "note": "AI startups using OpenAI tech", "category": "AI Accelerator"},
    {"title": "Mistral -- Accelerate", "url": "https://mistral.ai/fr/startup/", "note": "AI startups on Mistral models", "category": "AI Accelerator"},
    {"title": "Perplexity -- For Startups", "url": "https://www.perplexity.ai/hub/for-startups", "note": "API credits + GTM support", "category": "AI Accelerator"},
    # GENERAL,
    {"title": "Y Combinator -- Apply", "url": "https://www.ycombinator.com/apply", "note": "2x/year, $500k investment", "category": "Incubator"},
    {"title": "Antler -- Global Residency", "url": "https://www.antler.co/apply", "note": "Rolling, day-zero investor", "category": "Incubator"},
    {"title": "Techstars -- Apply", "url": "https://www.techstars.com/apply", "note": "Many programs worldwide", "category": "Accelerator"},
    {"title": "Pioneer -- Tournament", "url": "https://pioneer.app", "note": "Rolling, global remote accelerator", "category": "Accelerator"},
    {"title": "a16z Speedrun -- Apply", "url": "https://speedrun.a16z.com", "note": "Fast 4-week cohort", "category": "Accelerator"},
    {"title": "Entrepreneur First (EF)", "url": "https://www.joinef.com/apply", "note": "Pre-team, pre-idea accelerator", "category": "Accelerator"},
    {"title": "500 Global -- Accelerator", "url": "https://500.co/accelerators", "note": "Multiple programs worldwide", "category": "Accelerator"},
    {"title": "General Catalyst -- Venture Fellows", "url": "https://www.generalcatalyst.com/venture-fellows", "note": "Fellowship for emerging builders", "category": "Accelerator"},
]


def get_static_opportunities():
    return [{"title": o["title"], "url": o["url"], "deadline": o.get("note", ""), "prize": "", "source": o["category"]} for o in STATIC_OPPORTUNITIES]


# ── TELEGRAM ──────────────────────────────────────────────────────────────────

def send_telegram(text):
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=10
    )
    if r.ok:
        print("[telegram] Message sent")
    else:
        print(f"[telegram] Error {r.status_code}: {r.text}")


def chunk_messages(text, limit=4096):
    lines = text.split("\n")
    chunks, current = [], ""
    for line in lines:
        if len(current) + len(line) + 1 > limit:
            chunks.append(current.strip())
            current = line + "\n"
        else:
            current += line + "\n"
    if current.strip():
        chunks.append(current.strip())
    return chunks


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Starting scrape...")

    scrapers = [
        ("Devpost",   scrape_devpost),
        ("MLH",       scrape_mlh),
        ("Unstop",    scrape_unstop),
        ("DoraHacks", scrape_dorahacks),
        ("ETHGlobal", scrape_ethglobal),
        ("YC",        scrape_yc),
        ("Static",    get_static_opportunities),
    ]

    all_items = []
    for name, fn in scrapers:
        print(f"  Scraping {name}...")
        try:
            results = fn()
            print(f"    -> {len(results)} items")
            all_items.extend(results)
        except Exception as e:
            print(f"    -> error: {e}")

    items = [i for i in all_items if i.get("title") and i.get("url")]
    print(f"\nTotal: {len(items)} opportunities")

    if not items:
        send_telegram(f"No opportunities found today ({date.today()}). Check back tomorrow!")
        return

    by_source = {}
    for item in items:
        by_source.setdefault(item["source"], []).append(item)

    SOURCE_EMOJI = {
        "Devpost": "💻", "MLH": "🏫", "Unstop": "🏆", "DoraHacks": "🌐",
        "ETHGlobal": "⟠", "YC": "🚀", "Crypto Hackathon": "⛓",
        "Crypto Accelerator": "🔮", "Crypto Grants": "💎",
        "AI Accelerator": "🤖", "Incubator": "🌱", "Accelerator": "⚡",
    }

    lines = ["🎯 <b>Hackathon & Opportunity Digest</b> -- " + str(date.today()) + "\n"]

    for source, source_items in by_source.items():
        emoji = SOURCE_EMOJI.get(source, "📌")
        lines.append("\n" + emoji + " <b>" + source + "</b> (" + str(len(source_items)) + ")")
        for item in source_items[:8]:
            title = html.escape(item["title"][:80])
            url = item["url"]
            note = html.escape(item.get("deadline", "")[:60])
            entry = '  • <a href="' + url + '">' + title + "</a>"
            if note:
                entry += "\n    📌 " + note
            lines.append(entry)

    lines.append("\n\n<i>" + str(len(items)) + " opportunities | HackathonBot</i>")

    for chunk in chunk_messages("\n".join(lines)):
        send_telegram(chunk)


if __name__ == "__main__":
    main()
