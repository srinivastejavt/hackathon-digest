#!/usr/bin/env python3
"""
Hackathon + Incubator + Accelerator + Cohort Daily Scraper  v3
Covers: hackathons, crypto accelerators, AI accelerators, incubators, cohorts, grants
Credentials injected via GitHub Secrets: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
Env vars: FOCUS=all|crypto,ai|web3 ... (comma-separated keywords)
"""

import os, json, html, requests
from datetime import datetime, date
from bs4 import BeautifulSoup

# ── CONFIG ──────────────────────────────────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
FOCUS            = os.environ.get("FOCUS", "all").lower().strip()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
# ────────────────────────────────────────────────────────────────────────────────────────────────────────


def get(url, timeout=10):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"  [warn] GET {url} -> {e}")
        return None


def fmt_date(raw):
    """Parse ISO or mixed date strings into short readable format."""
    if not raw:
        return ""
    raw = str(raw).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[:19], fmt).strftime("%b %d")
        except Exception:
            pass
    return raw[:30]


def fmt_prize(raw):
    """Format prize amounts: 10000 -> $10k, 1500000 -> $1.5M."""
    if not raw or str(raw).strip() in ("0", "None", ""):
        return ""
    s = str(raw).strip()
    if s.startswith("$"):
        return s[:20]
    try:
        v = int(float(s))
        if v <= 0:
            return ""
        if v >= 1_000_000:
            return f"${v / 1_000_000:.1f}M".replace(".0M", "M")
        if v >= 1_000:
            return f"${v // 1_000}k"
        return f"${v}"
    except Exception:
        return s[:20]


# ── LIVE SCRAPERS ───────────────────────────────────────────────────────────────────────────────────────

def scrape_devpost():
    """Devpost hackathons — with prize amounts and deadlines."""
    results = []
    url = "https://devpost.com/api/hackathons" + "?order_by=deadline&per_page=20"
    r = get(url)
    if not r:
        return results
    try:
        data = r.json()
        hackathons = data.get("hackathons", [])
    except Exception as e:
        print(f"  [warn] devpost json: {e}")
        return results
    for h in hackathons:
        title = h.get("title", "").strip()
        link  = h.get("url", "")
        if not link.startswith("http"):
            link = "https://devpost.com" + link
        prize  = fmt_prize(h.get("prize_amount", ""))
        raw_d  = h.get("submission_period_dates", "")
        if raw_d and " - " in raw_d:
            deadline = "Due " + raw_d.split(" - ")[-1].strip()
        elif raw_d:
            deadline = "Due " + raw_d.strip()
        else:
            deadline = ""
        if title and link:
            results.append({"title": title, "url": link, "deadline": deadline, "prize": prize, "source": "Devpost"})
    return results


def scrape_mlh():
    """MLH hackathons — scrape 2026 season HTML page."""
    import re
    results = []
    r = get("https://www.mlh.com/seasons/2026/events")
    if not r:
        return results
    soup = BeautifulSoup(r.text, "html.parser")
    # Find the Upcoming Events section and stop at Past Events
    in_upcoming = False
    for tag in soup.find_all(["h2", "h3", "a"]):
        if tag.name in ("h2", "h3"):
            text = tag.get_text(strip=True).lower()
            if "upcoming" in text:
                in_upcoming = True
            elif "past" in text:
                break
            continue
        if not in_upcoming:
            continue
        href = tag.get("href", "")
        if not href or ("events.mlh.io" not in href and "/events/" not in href):
            continue
        raw = tag.get_text(" ", strip=True)
        # Extract date range e.g. "JUN 12 - 18" or "JUL 10 - 16"
        dm = re.search(r"([A-Z]{3}\s+\d+\s*-\s*\d+)", raw)
        if dm:
            parts = dm.group(1).split("-")
            month = parts[0].strip().split()[0]
            end_day = parts[-1].strip()
            deadline = f"Due {month} {end_day}"
            title = raw[:raw.find(dm.group(0))].replace(" background", "").strip()
        else:
            deadline = ""
            title = raw.replace(" background", "").strip()
        if not href.startswith("http"):
            href = "https://www.mlh.com" + href
        # Clean duplicate title text (MLH repeats title 3x in tag)
        words = title.split()
        half = len(words) // 3
        if half > 0 and " ".join(words[:half]) == " ".join(words[half:half*2]):
            title = " ".join(words[:half])
        if title and len(title) > 2:
            results.append({"title": title[:80], "url": href, "deadline": deadline, "prize": "", "source": "MLH"})
    seen = set()
    deduped = []
    for item in results:
        if item["url"] not in seen:
            seen.add(item["url"])
            deduped.append(item)
    return deduped[:10]
def scrape_unstop():
    """Unstop hackathons — HTML scrape (API returns empty)."""
    import re
    results = []
    r = get("https://unstop.com/hackathons")
    if not r:
        return results
    soup = BeautifulSoup(r.text, "html.parser")
    for a in soup.select("a[href*='/hackathons/']")[:20]:
        href = a.get("href", "")
        if not href.startswith("http"):
            href = "https://unstop.com" + href
        raw = a.get_text(" ", strip=True)
        if not raw or len(raw) < 5 or raw.lower() in ("hackathons", "competitions"):
            continue
        # Look for prize in text like "INR 1,00,000" or "USD 10,000"
        prize = ""
        pm = re.search(r"(INR|USD|\$)[\s,\d\.]+", raw)
        if pm:
            prize = pm.group(0).strip()[:20]
        # Look for date like "30 Jun 2026" or "Jun 30, 2026"
        deadline = ""
        dm = re.search(r"(\d{1,2}\s+[A-Za-z]{3}\s+202\d|[A-Za-z]{3}\s+\d{1,2},?\s+202\d)", raw)
        if dm:
            deadline = "Due " + dm.group(0).strip()
        title = raw[:80]
        results.append({"title": title, "url": href, "deadline": deadline, "prize": fmt_prize(prize), "source": "Unstop"})
    seen = set()
    deduped = []
    for item in results:
        if item["url"] not in seen:
            seen.add(item["url"])
            deduped.append(item)
    return deduped[:10]
def scrape_dorahacks():
    """DoraHacks — try JSON API endpoints, fall back to HTML."""
    results = []
    apis = [
        "https://dorahacks.io/api/hackathon" + "?tab=open&limit=20",
        "https://dorahacks.io/api/hackathon/list" + "?limit=20&status=open",
    ]
    for api_url in apis:
        r = get(api_url)
        if not r:
            continue
        try:
            payload = r.json()
            items = (payload.get("data") or payload.get("hackathons") or
                     payload.get("list") or payload.get("results") or [])
            if isinstance(payload, list):
                items = payload
        except Exception:
            continue
        for h in items[:15]:
            title = (h.get("title") or h.get("name") or "").strip()
            hid   = h.get("id") or h.get("buidl_id") or ""
            link  = f"https://dorahacks.io/hackathon/{hid}/detail" if hid else "https://dorahacks.io/hackathon"
            prize = fmt_prize(h.get("prize_pool") or h.get("total_prize") or "")
            end   = h.get("voting_end") or h.get("end_time") or h.get("deadline") or ""
            deadline = ("Due " + fmt_date(end)) if end else ""
            if title:
                results.append({"title": title, "url": link, "deadline": deadline, "prize": prize, "source": "DoraHacks"})
        if results:
            return results
    # HTML fallback
    r = get("https://dorahacks.io/hackathon")
    if r:
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select("a[href*='/hackathon/']")[:15]:
            title = card.get_text(strip=True)
            href  = card.get("href", "")
            if not href.startswith("http"):
                href = "https://dorahacks.io" + href
            if title and len(title) > 5:
                results.append({"title": title[:80], "url": href, "deadline": "", "prize": "", "source": "DoraHacks"})
    return results


def scrape_ethglobal():
    """ETHGlobal hackathons — scrape the events page."""
    results = []
    r = get("https://ethglobal.com/events")
    if not r:
        return results
    soup = BeautifulSoup(r.text, "html.parser")
    for a in soup.select("a[href*='/events/']")[:20]:
        title = a.get_text(strip=True)
        href  = a.get("href", "")
        if not href.startswith("http"):
            href = "https://ethglobal.com" + href
        if title and len(title) > 3 and "/events/" in href:
            results.append({"title": title[:80], "url": href, "deadline": "", "prize": "", "source": "ETHGlobal"})
    seen = set()
    deduped = []
    for item in results:
        if item["url"] not in seen:
            seen.add(item["url"])
            deduped.append(item)
    return deduped[:10]


def scrape_yc():
    """Y Combinator current batch — scrape the apply page."""
    results = []
    r = get("https://www.ycombinator.com/apply/")
    if not r:
        return results
    soup = BeautifulSoup(r.text, "html.parser")
    deadline = ""
    for tag in soup.find_all(["p", "span", "div", "h2", "h3"]):
        t = tag.get_text(" ", strip=True)
        if "deadline" in t.lower() or "application" in t.lower():
            deadline = t[:60]
            break
    results.append({
        "title": "Y Combinator — Apply to YC",
        "url": "https://www.ycombinator.com/apply/",
        "deadline": deadline,
        "prize": "",
        "source": "YC"
    })
    return results
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
    return STATIC_OPPORTUNITIES


def send_telegram(text):
    """Send a Telegram message with HTML parse mode."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[dry-run] Would send:", text[:120])
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        data = r.json()
        if not data.get("ok"):
            print(f"  [warn] Telegram error: {data}")
        else:
            print("  [ok] Telegram message sent")
    except Exception as e:
        print(f"  [warn] Telegram send failed: {e}")


def chunk_messages(text, max_len=4000):
    """Split text into Telegram-safe chunks at newline boundaries."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    lines  = text.split("\n")
    cur    = ""
    for line in lines:
        if len(cur) + len(line) + 1 > max_len:
            chunks.append(cur.rstrip())
            cur = ""
        cur += line + "\n"
    if cur.strip():
        chunks.append(cur.rstrip())
    return chunks


def main():
    today      = date.today()
    is_monday  = today.weekday() == 0
    today_str  = today.strftime("%b %d, %Y")
    dow        = today.strftime("%A")
    NL         = "\n"

    # ── Apply FOCUS filter to static programs ──────────────────────────────────────
    static_all   = get_static_opportunities()
    if FOCUS == "all":
        static_items = static_all
    else:
        kws = [k.strip() for k in FOCUS.split(",") if k.strip()]
        static_items = [
            i for i in static_all
            if any(k in i.get("source", "").lower() or k in i.get("title", "").lower() for k in kws)
        ]
    print(f"[focus={FOCUS}] {len(static_items)}/{len(static_all)} static programs")

    # ── Run live scrapers ────────────────────────────────────────────────────────────
    scrapers = [
        ("Devpost",   scrape_devpost),
        ("MLH",       scrape_mlh),
        ("Unstop",    scrape_unstop),
        ("DoraHacks", scrape_dorahacks),
        ("ETHGlobal", scrape_ethglobal),
        ("YC",        scrape_yc),
    ]
    live_sections = []
    for name, fn in scrapers:
        print(f"Scraping {name}...")
        try:
            items = fn()
        except Exception as e:
            print(f"  [error] {name}: {e}")
            items = []
        if not items:
            print(f"  [skip] {name}: no results")
            continue
        sec = []
        for it in items[:4]:
            title = html.escape(it.get("title", "")[:70])
            url   = it.get("url", "")
            d     = it.get("deadline", "").strip()
            p     = it.get("prize", "").strip()
            row   = f'  • <a href="{url}">{title}</a>'
            tags  = []
            if d:
                tags.append(html.escape(d[:40]))
            if p:
                tags.append("\U0001f4b0 " + html.escape(p))
            if tags:
                row += "  <i>" + "  \u00b7  ".join(tags) + "</i>"
            sec.append(row)
        if sec:
            live_sections.append(f"<b>{name}</b>" + NL + NL.join(sec))
        print(f"  [ok] {name}: {len(items)} results, showing {min(len(items),4)}")

    # ── Message 1 : Live listings (sent every day) ──────────────────────────────────
    lines = [f"U0001f680 <b>Hackathon + Opportunity Digest</b>"]
    lines.append(f"{dow}, {today_str}")
    lines.append("")
    if live_sections:
        lines.append("<b>U0001f4e1 Live Listings</b>")
        lines.append("")
        lines += live_sections
    else:
        lines.append("No live listings found today.")
    msg1 = NL.join(lines)
    for chunk in chunk_messages(msg1):
        send_telegram(chunk)

    # ── Message 2+ : Static programs (Mondays only) ─────────────────────────────────
    if not is_monday:
        print(f"[skip] Programs digest not sent (runs Mondays only — today is {dow})")
        return

    print("Monday — sending programs digest...")
    by_cat = {}
    for item in static_items:
        cat = item.get("source", "Other")
        by_cat.setdefault(cat, []).append(item)

    CAT_EMOJI = {
        "Crypto Accelerator": "U0001f525",
        "AI Accelerator":     "U0001f916",
        "General Accelerator":"U0001f3c6",
        "Incubator":          "U0001f331",
        "Cohort":             "U0001f91d",
        "Grant":              "U0001f4b8",
        "Fellowship":         "U0001f393",
        "Competition":        "U0001f3af",
    }

    prog_lines = [f"U0001f4c5 <b>Programs Digest</b> (weekly — {today_str})"]
    prog_lines.append(f"FOCUS: {FOCUS}")
    prog_lines.append("")
    for cat, items in by_cat.items():
        emoji = CAT_EMOJI.get(cat, "⭐")
        prog_lines.append(f"{emoji} <b>{html.escape(cat)}</b>")
        for it in items:
            title  = html.escape(it.get("title", "")[:70])
            url    = it.get("url", "")
            status = it.get("status", "")
            badge  = f" <i>({html.escape(status)})</i>" if status else ""
            prog_lines.append(f"  • <a href=\"{url}\">{title}</a>{badge}")
        prog_lines.append("")
    for chunk in chunk_messages(NL.join(prog_lines)):
        send_telegram(chunk)


if __name__ == "__main__":
    main()
