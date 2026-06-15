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

STATIC_OPPORTUNITIES = [
    {"title": "Colosseum -- Solana Hackathon", "url": "https://www.colosseum.org", "note": "Check for live hackathons", "category": "Crypto Hackathon"},
    {"title": "Encode Club -- Hackathons", "url": "https://www.encode.club", "note": "Web3 education + hackathons", "category": "Crypto Hackathon"},
    {"title": "ETHGlobal -- Hackathons", "url": "https://ethglobal.com/events", "note": "Major Ethereum hackathons worldwide", "category": "Crypto Hackathon"},
    {"title": "DoraHacks -- Hackathons", "url": "https://dorahacks.io/hackathon", "note": "Global Web3 hackathon platform", "category": "Crypto Hackathon"},
    {"title": "Gitcoin Hackathons", "url": "https://gitcoin.co/hackathon-list", "note": "Open source and web3 hackathons", "category": "Crypto Hackathon"},
    {"title": "Solana Breakpoint -- Hackathon", "url": "https://solana.com/breakpoint", "note": "Annual Solana conference + hackathon", "category": "Crypto Hackathon"},
    {"title": "Polkadot Hackathon", "url": "https://polkadot.network/ecosystem/hackathons", "note": "Substrate and Polkadot hackathons", "category": "Crypto Hackathon"},
    {"title": "HackFS by ETHGlobal", "url": "https://ethglobal.com/events/hackfs2025", "note": "Decentralized storage + web3 hackathon", "category": "Crypto Hackathon"},
    {"title": "Celo Camp Hackathon", "url": "https://www.celocamp.com", "note": "Mobile-first web3, rolling cohorts", "category": "Crypto Hackathon"},
    {"title": "ICP Hackathons", "url": "https://dfinity.org/developers/events", "note": "Internet Computer hackathons", "category": "Crypto Hackathon"},
    {"title": "Devfolio Hackathons", "url": "https://devfolio.co/hackathons", "note": "India + global web3 hackathons", "category": "Crypto Hackathon"},
    {"title": "Lablab.ai -- AI Hackathons", "url": "https://lablab.ai/event", "note": "AI-focused hackathons, frequent", "category": "AI Hackathon"},
    {"title": "HackerEarth -- Hackathons", "url": "https://www.hackerearth.com/challenges/hackathon", "note": "Tech and AI hackathons", "category": "Hackathon"},
    {"title": "Devpost -- Hackathons", "url": "https://devpost.com/hackathons", "note": "Largest hackathon aggregator", "category": "Hackathon"},
    {"title": "MLH -- Season Hackathons", "url": "https://mlh.io/seasons/2025/events", "note": "Major League Hacking, student-focused", "category": "Hackathon"},
    {"title": "Colosseum -- Solana Accelerator", "url": "https://www.colosseum.org/accelerator", "note": "Rolling cohorts for Solana projects", "category": "Crypto Accelerator"},
    {"title": "Alliance DAO -- Crypto Accelerator", "url": "https://alliance.xyz/apply", "note": "Top crypto accelerator, rolling", "category": "Crypto Accelerator"},
    {"title": "Aptos Foundation -- Accelerator", "url": "https://aptosfoundation.org/grants", "note": "Move ecosystem projects", "category": "Crypto Accelerator"},
    {"title": "Sui Foundation -- Builder Program", "url": "https://sui.io/grants", "note": "Sui ecosystem accelerator", "category": "Crypto Accelerator"},
    {"title": "TON Foundation -- Accelerator", "url": "https://ton.foundation/grants", "note": "TON / Telegram ecosystem", "category": "Crypto Accelerator"},
    {"title": "Hedera HBAR Foundation -- Grants", "url": "https://hbarfoundation.org/apply", "note": "HBAR ecosystem projects", "category": "Crypto Accelerator"},
    {"title": "zkSync Accelerator", "url": "https://zksync.io/ecosystem", "note": "ZK-rollup ecosystem grants", "category": "Crypto Accelerator"},
    {"title": "Near Foundation -- Horizon", "url": "https://near.org/horizon", "note": "NEAR ecosystem accelerator + grants", "category": "Crypto Accelerator"},
    {"title": "Polygon Labs -- Accelerator", "url": "https://polygon.technology/village", "note": "Polygon ecosystem builder program", "category": "Crypto Accelerator"},
    {"title": "Avalanche -- Blizzard Fund", "url": "https://www.avax.network/grants", "note": "AVAX ecosystem grants + accelerator", "category": "Crypto Accelerator"},
    {"title": "Stacks Foundation -- Grants", "url": "https://stacks.org/grants", "note": "Bitcoin L2 ecosystem grants", "category": "Crypto Accelerator"},
    {"title": "Algorand Foundation -- Grants", "url": "https://algorand.foundation/grants", "note": "Algorand blockchain grants", "category": "Crypto Accelerator"},
    {"title": "LayerZero -- Builder Grants", "url": "https://layerzero.network/builders", "note": "Cross-chain omnichain grants", "category": "Crypto Accelerator"},
    {"title": "Arbitrum Foundation -- Grants", "url": "https://arbitrum.foundation/grants", "note": "Arbitrum ecosystem grants", "category": "Crypto Accelerator"},
    {"title": "Optimism -- RetroActive PGF", "url": "https://optimism.io/retropgf", "note": "Retroactive public goods funding", "category": "Crypto Accelerator"},
    {"title": "Base Ecosystem Fund", "url": "https://base.mirror.xyz", "note": "Coinbase Base L2 ecosystem", "category": "Crypto Accelerator"},
    {"title": "Scroll Foundation -- Grants", "url": "https://scroll.io/grants", "note": "ZK-EVM rollup ecosystem", "category": "Crypto Accelerator"},
    {"title": "Fuel Network -- Grants", "url": "https://fuel.network/grants", "note": "Parallel execution blockchain", "category": "Crypto Accelerator"},
    {"title": "Uniswap Foundation -- Grants", "url": "https://uniswapfoundation.org/grants", "note": "DeFi protocol grants", "category": "Crypto Accelerator"},
    {"title": "Web3 Foundation -- Grants", "url": "https://web3.foundation/grants", "note": "Polkadot and Kusama ecosystem", "category": "Crypto Accelerator"},
    {"title": "Protocol Labs -- Grants", "url": "https://protocol.ai/work", "note": "IPFS, Filecoin, libp2p ecosystem", "category": "Crypto Accelerator"},
    {"title": "dYdX Grants Program", "url": "https://dydxgrants.com", "note": "Decentralized exchange ecosystem", "category": "Crypto Accelerator"},
    {"title": "Aave Grants DAO", "url": "https://aavegrants.org", "note": "DeFi lending protocol grants", "category": "Crypto Accelerator"},
    {"title": "Compound Grants", "url": "https://compoundgrants.org", "note": "DeFi money market grants", "category": "Crypto Accelerator"},
    {"title": "1inch Foundation -- Grants", "url": "https://1inch.io/grants", "note": "DEX aggregator ecosystem", "category": "Crypto Accelerator"},
    {"title": "Superteam Earn", "url": "https://earn.superteam.fun", "note": "Solana bounties and grants, rolling", "category": "Crypto Grants"},
    {"title": "Superteam -- Grants", "url": "https://superteam.fun/grants", "note": "Superteam grants for Solana builders", "category": "Crypto Grants"},
    {"title": "Solana Foundation -- Grants", "url": "https://solana.org/grants", "note": "Rolling grants for Solana ecosystem", "category": "Crypto Grants"},
    {"title": "Ethereum Foundation -- ESP", "url": "https://esp.ethereum.foundation", "note": "Ecosystem Support Program, rolling", "category": "Crypto Grants"},
    {"title": "Ethereum Foundation -- Academic Grants", "url": "https://esp.ethereum.foundation/academic-grants", "note": "Research grants for academics", "category": "Crypto Grants"},
    {"title": "Paradigm -- Research Grants", "url": "https://www.paradigm.xyz/grants", "note": "Crypto research grants", "category": "Crypto Grants"},
    {"title": "Chainlink -- BUILD Program", "url": "https://chain.link/build", "note": "Chainlink ecosystem grants + support", "category": "Crypto Grants"},
    {"title": "Filecoin Foundation -- Dev Grants", "url": "https://grants.filecoin.io", "note": "Rolling grants for decentralized storage", "category": "Crypto Grants"},
    {"title": "Wormhole -- xGrant", "url": "https://wormhole.com/grants", "note": "Cross-chain project grants", "category": "Crypto Grants"},
    {"title": "Gitcoin -- Grants Rounds", "url": "https://grants.gitcoin.co", "note": "Quadratic funding rounds", "category": "Crypto Grants"},
    {"title": "Cardano -- Project Catalyst", "url": "https://projectcatalyst.io", "note": "Community-voted funding on Cardano", "category": "Crypto Grants"},
    {"title": "Cosmos -- Interchain Foundation", "url": "https://interchain.io/funding", "note": "Cosmos/IBC ecosystem grants", "category": "Crypto Grants"},
    {"title": "Zcash Foundation -- Grants", "url": "https://zcashcommunitygrants.org", "note": "Privacy tech and Zcash grants", "category": "Crypto Grants"},
    {"title": "Celestia -- Modular Fellows", "url": "https://celestia.org/grants", "note": "Modular blockchain grants + fellowship", "category": "Crypto Grants"},
    {"title": "EigenLayer -- Grants", "url": "https://www.eigenlayer.xyz/ecosystem", "note": "Restaking protocol grants", "category": "Crypto Grants"},
    {"title": "a16z -- Crypto Grants", "url": "https://a16zcrypto.com/grants", "note": "Research and open source grants", "category": "Crypto Grants"},
    {"title": "AI Grant -- Apply", "url": "https://aigrant.com", "note": "Rolling; up to $250k for AI projects", "category": "AI Accelerator"},
    {"title": "AI2 Incubator -- Apply", "url": "https://www.ai2incubator.com", "note": "Allen Institute for AI, seed-stage", "category": "AI Accelerator"},
    {"title": "YC -- Apply", "url": "https://www.ycombinator.com/apply", "note": "Top accelerator, Jan and Jun batches", "category": "AI Accelerator"},
    {"title": "Sequoia Arc -- Apply", "url": "https://www.sequoiacap.com/arc", "note": "Sequoia pre-seed program, rolling", "category": "AI Accelerator"},
    {"title": "Lightspeed Faction -- Fellowship", "url": "https://lsvp.com/faction", "note": "Pre-seed for technical founders", "category": "AI Accelerator"},
    {"title": "OpenAI Startup Fund", "url": "https://openai.com/fund", "note": "OpenAI-backed startups", "category": "AI Accelerator"},
    {"title": "Mistral -- Accelerate Program", "url": "https://mistral.ai/en/accelerate", "note": "EU AI startups, credits + support", "category": "AI Accelerator"},
    {"title": "Perplexity -- For Startups", "url": "https://www.perplexity.ai/for-startups", "note": "AI search API credits for startups", "category": "AI Accelerator"},
    {"title": "a16z -- Speedrun", "url": "https://speedrun.a16z.com", "note": "2-week AI startup sprint, rolling", "category": "AI Accelerator"},
    {"title": "Google for Startups -- AI First", "url": "https://startup.google.com/programs/ai-first", "note": "Google AI accelerator, 3 months", "category": "AI Accelerator"},
    {"title": "Microsoft for Startups -- Founders Hub", "url": "https://foundershub.startups.microsoft.com", "note": "Azure credits + enterprise support", "category": "AI Accelerator"},
    {"title": "NVIDIA Inception -- Program", "url": "https://www.nvidia.com/startups", "note": "GPU credits + go-to-market for AI", "category": "AI Accelerator"},
    {"title": "Cohere for AI -- Research Grants", "url": "https://cohere.com/cohere-for-ai", "note": "AI research grants from Cohere", "category": "AI Accelerator"},
    {"title": "AWS Activate -- Founders", "url": "https://aws.amazon.com/activate", "note": "AWS credits up to $100k", "category": "AI Accelerator"},
    {"title": "Scale AI -- Startup Program", "url": "https://scale.com/startups", "note": "Data labeling credits for AI startups", "category": "AI Accelerator"},
    {"title": "Together AI -- Compute Grants", "url": "https://www.together.ai/startups", "note": "LLM inference credits", "category": "AI Accelerator"},
    {"title": "Hugging Face -- Expert Acceleration", "url": "https://huggingface.co/support", "note": "ML support + compute for AI teams", "category": "AI Accelerator"},
    {"title": "Nat Friedman -- AI Grants", "url": "https://aigrant.com", "note": "Rolling AI project grants", "category": "AI Accelerator"},
    {"title": "Pear VC -- Garage Program", "url": "https://pear.vc/garage", "note": "Pre-seed cohort, AI + dev tools focus", "category": "AI Accelerator"},
    {"title": "Khosla Ventures -- KV Lab", "url": "https://www.khoslaventures.com/kv-lab", "note": "AI research + startup support", "category": "AI Accelerator"},
    {"title": "Pioneer -- Tournament", "url": "https://pioneer.app", "note": "Online accelerator, rolling cohorts", "category": "Cohort"},
    {"title": "On Deck -- Founders Fellowship", "url": "https://www.beondeck.com/founders", "note": "Founder community + peer support", "category": "Cohort"},
    {"title": "South Park Commons -- Membership", "url": "https://www.southparkcommons.com/apply", "note": "Tech community for pre-company founders", "category": "Cohort"},
    {"title": "Interact Fellowship", "url": "https://www.joininteract.com", "note": "Fellowship for ambitious young builders", "category": "Cohort"},
    {"title": "Neo -- Fellowship", "url": "https://neo.com/fellowship", "note": "Fellowship for top early-stage builders", "category": "Cohort"},
    {"title": "Contrary -- Talent Collective", "url": "https://contrary.com/talent", "note": "Student + early career program", "category": "Cohort"},
    {"title": "Kleiner Perkins -- Fellows", "url": "https://kpcb.com/fellows", "note": "Engineering + design fellows program", "category": "Cohort"},
    {"title": "Entrepreneur First -- Cohort", "url": "https://www.joinef.com/apply", "note": "Pre-team, global cities, rolling", "category": "Cohort"},
    {"title": "Antler -- Residency", "url": "https://www.antler.co/apply", "note": "Global day-0 accelerator, many cities", "category": "Cohort"},
    {"title": "Founders Forum -- Ones to Watch", "url": "https://foundersforum.com", "note": "European startup cohort + community", "category": "Cohort"},
    {"title": "Buildspace -- Nights and Weekends", "url": "https://buildspace.so", "note": "6-week cohort for builders + founders", "category": "Cohort"},
    {"title": "Replit -- Ventures", "url": "https://replit.com/ventures", "note": "Vibe coding era startup cohort", "category": "Cohort"},
    {"title": "Techstars -- Apply", "url": "https://www.techstars.com/accelerators", "note": "Global network, many tracks and cities", "category": "Incubator"},
    {"title": "500 Global -- Flagship", "url": "https://500.co/accelerator", "note": "Global accelerator, formerly 500 Startups", "category": "Incubator"},
    {"title": "Alchemist Accelerator", "url": "https://www.alchemistaccelerator.com/apply", "note": "Enterprise SaaS, SF-based", "category": "Incubator"},
    {"title": "LAUNCH Accelerator", "url": "https://launch.co/accelerator", "note": "Jason Calacanis, rolling, remote", "category": "Incubator"},
    {"title": "MassChallenge -- Apply", "url": "https://masschallenge.org/programs", "note": "Global zero-equity incubator", "category": "Incubator"},
    {"title": "Plug and Play -- Tech Center", "url": "https://www.plugandplaytechcenter.com/ventures", "note": "Corporate accelerator, many verticals", "category": "Incubator"},
    {"title": "IndieBio -- SOSV", "url": "https://indiebio.co/apply", "note": "Biotech and health startups", "category": "Incubator"},
    {"title": "HAX -- SOSV Hardware", "url": "https://hax.co/apply", "note": "Hardware and deep tech startups", "category": "Incubator"},
    {"title": "Founders Factory", "url": "https://foundersfactory.com/studios", "note": "Studio + accelerator, UK and global", "category": "Incubator"},
    {"title": "Creative Destruction Lab", "url": "https://creativedestructionlab.com/apply", "note": "Science-based startups, CDL-Toronto", "category": "Incubator"},
    {"title": "Berkeley SkyDeck -- Pad-13", "url": "https://skydeck.berkeley.edu/apply", "note": "UC Berkeley accelerator", "category": "Incubator"},
    {"title": "Stanford -- StartX", "url": "https://startx.com/apply", "note": "Stanford-affiliated non-profit accelerator", "category": "Incubator"},
    {"title": "General Catalyst -- Venture Fellows", "url": "https://www.generalcatalyst.com/venture-fellows", "note": "Annual fellowship at top VC", "category": "Incubator"},
    {"title": "Betaworks -- Camp", "url": "https://betaworks.com/camp", "note": "NYC-based themed cohorts", "category": "Incubator"},
    {"title": "Dreamit Ventures -- Apply", "url": "https://www.dreamit.com/apply", "note": "SecureTech and HealthTech tracks", "category": "Incubator"},
    {"title": "Station F -- Programs", "url": "https://stationf.co/programs", "note": "World's largest startup campus, Paris", "category": "Incubator"},
    {"title": "Wayra -- Apply", "url": "https://wayra.com/apply", "note": "Telefonica corporate accelerator", "category": "Incubator"},
    {"title": "Capital Factory -- Apply", "url": "https://capitalfactory.com/accelerate", "note": "Texas-based, defense + tech", "category": "Incubator"},
    {"title": "Founder Institute -- Apply", "url": "https://fi.co/apply", "note": "Pre-seed, global, part-time cohorts", "category": "Incubator"},
    {"title": "NSF SBIR -- Phase I", "url": "https://seedfund.nsf.gov", "note": "US gov R&D grants up to $275k", "category": "Grant"},
    {"title": "Mozilla Foundation -- Technology Fund", "url": "https://foundation.mozilla.org/fellowships", "note": "Open source and privacy grants", "category": "Grant"},
    {"title": "Open Technology Fund", "url": "https://www.opentech.fund/funds", "note": "Internet freedom and privacy grants", "category": "Grant"},
    {"title": "Knight Foundation -- Grants", "url": "https://knightfoundation.org/apply", "note": "Journalism, democracy, arts grants", "category": "Grant"},
    {"title": "Shuttleworth Foundation -- Fellowship", "url": "https://shuttleworthfoundation.org/apply", "note": "Open source fellowship, rolling", "category": "Grant"},
    {"title": "Fast Forward -- Accelerator", "url": "https://www.ffwd.org/apply", "note": "Tech nonprofits accelerator", "category": "Grant"},
    {"title": "Blue Ridge Labs -- Fellowship", "url": "https://blueridgelabs.org", "note": "Social impact tech fellowship", "category": "Grant"}
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



# ── MAIN ─────────────────────────────────────────────────────────────────────────────

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Starting scrape...")

    live_scrapers = [
        ("Devpost",   scrape_devpost),
        ("MLH",       scrape_mlh),
        ("Unstop",    scrape_unstop),
        ("DoraHacks", scrape_dorahacks),
        ("ETHGlobal", scrape_ethglobal),
        ("YC",        scrape_yc),
    ]

    live_items = []
    for name, fn in live_scrapers:
        print(f"  Scraping {name}...")
        try:
            results = fn()
            print(f"    → {len(results)} items")
            live_items.extend(results)
        except Exception as e:
            print(f"    → error: {e}")

    static_items = get_static_opportunities()
    live_items = [i for i in live_items if i.get("title") and i.get("url")]
    today = date.today().strftime("%b %d, %Y")
    print(f"Total: {len(live_items)} live + {len(static_items)} static")

    SOURCE_EMOJI = {
        "Devpost": "U0001f4bb", "MLH": "U0001f3eb", "Unstop": "U0001f3c6",
        "DoraHacks": "U0001f310", "ETHGlobal": "⧠", "YC": "U0001f680",
    }

    CAT_EMOJI = {
        "Crypto Hackathon":   "⛓",
        "Crypto Accelerator": "U0001f52e",
        "Crypto Grants":      "U0001f48e",
        "AI Hackathon":       "U0001f916",
        "AI Accelerator":     "U0001f9e0",
        "Cohort":             "U0001f465",
        "Incubator":          "U0001f331",
        "Hackathon":          "U0001f4bb",
        "Grant":              "U0001f4b0",
    }

    # ── MESSAGE 1: Live listings (change daily) ─────────────────────────────
    by_source = {}
    for item in live_items:
        by_source.setdefault(item["source"], []).append(item)

    lines = [
        f"U0001f3af <b>Daily Digest</b> — {today}",
        f"<i>U0001f7e2 {len(live_items)} live listings  |  U0001f4da {len(static_items)} ongoing programs</i>",
    ]

    if by_source:
        lines.append("")
        lines.append("――― LIVE THIS WEEK ―――")
        for source, items in by_source.items():
            emoji = SOURCE_EMOJI.get(source, "U0001f4cc")
            lines.append(f"
{emoji} <b>{source}</b>  ({len(items)} open)")
            for item in items[:4]:
                t = html.escape(item["title"][:65])
                u = item["url"]
                d = item.get("deadline", "")
                row = '  · <a href="' + u + '">' + t + '</a>'
                if d:
                    row += '  <i>— ' + html.escape(d[:35]) + '</i>'
                lines.append(row)
            if len(items) > 4:
                lines.append(f'  <i>+{len(items)-4} more on site →</i>')
    else:
        lines.append("")
        lines.append("⚠️ No live listings scraped today — see ongoing programs below.")

    send_telegram("\n".join(lines))

    # ── MESSAGE 2+: Ongoing programs (static, grouped by category) ─────────
    by_cat = {}
    for item in static_items:
        cat = item.get("category", "Other")
        by_cat.setdefault(cat, []).append(item)

    prog_lines = [
        f"U0001f4da <b>Ongoing Programs</b>  ({len(static_items)} open to apply)",
        "<i>Sorted by category — tap any link to apply</i>",
    ]

    for cat, items in by_cat.items():
        emoji = CAT_EMOJI.get(cat, "U0001f4cc")
        prog_lines.append(f"
{emoji} <b>{cat}</b>  ({len(items)})")
        for item in items:
            t = html.escape(item["title"])
            u = item["url"]
            note = item.get("note", "")
            line = '  · <a href="' + u + '">' + t + '</a>'
            if note:
                line += '  <i>— ' + html.escape(note[:40]) + '</i>'
            prog_lines.append(line)

    prog_lines.append(f"\n<i>HackathonBot · runs daily at 8am</i>")

    for chunk in chunk_messages("\n".join(prog_lines)):
        send_telegram(chunk)


if __name__ == "__main__":
    main()
