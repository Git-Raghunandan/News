import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import feedparser
import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="Swarup News & India Dashboard",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Configuration
# -----------------------------
SOURCES = {
    "International News — Reuters": {
        "url": "https://www.reuters.com/",
        "rss": [
            "https://feeds.reuters.com/reuters/topNews",
            "https://feeds.reuters.com/reuters/worldNews",
        ],
        "color": "#2563eb",
    },
    "IT Industry News — Reuters Technology": {
        "url": "https://www.reuters.com/technology/",
        "rss": [
            "https://feeds.reuters.com/reuters/technologyNews",
        ],
        "color": "#7c3aed",
    },
    "India News — News On AIR": {
        "url": "https://newsonair.gov.in/",
        "rss": [
            "https://www.newsonair.gov.in/feed/",
            "https://newsonair.gov.in/feed/",
        ],
        "color": "#ea580c",
    },
    "Odisha News — OdishaTV": {
        "url": "https://odishatv.in/",
        "rss": [
            "https://odishatv.in/rss",
            "https://odishatv.in/feed",
        ],
        "color": "#059669",
    },
    "TCS Newsroom": {
        "url": "https://www.tcs.com/who-we-are/newsroom",
        "rss": [],
        "color": "#dc2626",
    },
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_TIMEOUT = 15


# -----------------------------
# Helpers
# -----------------------------
def clean_text(value: str) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", BeautifulSoup(value, "html.parser").get_text(" ", strip=True)).strip()


def absolute_url(base: str, link: str) -> str:
    return urljoin(base, link)


def unique_items(items):
    seen = set()
    result = []
    for item in items:
        link = item.get("link", "").strip()
        title = item.get("title", "").strip()
        key = link or title
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def make_item(title, link, summary="", published=""):
    return {
        "title": clean_text(title),
        "link": link,
        "summary": clean_text(summary),
        "published": clean_text(published),
    }


# -----------------------------
# Generic RSS reader
# -----------------------------
def read_rss(url, limit=10):
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        parsed = feedparser.parse(response.content)

        items = []
        for entry in parsed.entries[:limit]:
            link = entry.get("link", "")
            title = entry.get("title", "")
            summary = entry.get("summary", entry.get("description", ""))
            published = entry.get("published", entry.get("updated", ""))
            if title and link:
                items.append(make_item(title, link, summary, published))

        return items
    except Exception:
        return []


def discover_feed_urls(page_url):
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        feeds = []

        for tag in soup.find_all("link"):
            rel = [str(x).lower() for x in tag.get("rel", [])]
            typ = str(tag.get("type", "")).lower()
            href = tag.get("href")
            if href and ("alternate" in rel) and (
                "rss" in typ or "atom" in typ or "xml" in typ
            ):
                feeds.append(absolute_url(page_url, href))

        return list(dict.fromkeys(feeds))
    except Exception:
        return []


# -----------------------------
# HTML article extraction
# -----------------------------
ARTICLE_SELECTORS = [
    "article",
    "[data-testid*='story']",
    "[data-testid*='article']",
    ".story",
    ".story-card",
    ".article",
    ".news-card",
    ".post",
    ".listing",
]


def extract_html_articles(page_url, limit=10):
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        candidates = []
        for selector in ARTICLE_SELECTORS:
            candidates.extend(soup.select(selector))

        # Fallback: inspect links with meaningful headline-like text.
        if not candidates:
            candidates = soup.find_all("a")

        items = []
        for node in candidates:
            if node.name == "a":
                a = node
            else:
                a = node.find("a", href=True)

            if not a:
                continue

            title = clean_text(a.get_text(" ", strip=True))
            href = a.get("href", "")
            if not title or not href:
                continue

            # Avoid navigation / tiny labels.
            if len(title) < 25 or len(title) > 300:
                continue

            link = absolute_url(page_url, href)
            if urlparse(link).netloc == "":
                continue

            summary = ""
            if node.name != "a":
                p = node.find(["p", "div"])
                if p:
                    summary = clean_text(p.get_text(" ", strip=True))

            items.append(make_item(title, link, summary))

        return unique_items(items)[:limit]
    except Exception:
        return []


def get_news(source_name, page_url, rss_urls, limit=10):
    # 1. Configured feeds
    for rss in rss_urls:
        items = read_rss(rss, limit)
        if items:
            return unique_items(items)[:limit], f"RSS: {rss}"

    # 2. Feed discovery
    for rss in discover_feed_urls(page_url):
        items = read_rss(rss, limit)
        if items:
            return unique_items(items)[:limit], f"RSS: {rss}"

    # 3. HTML fallback
    items = extract_html_articles(page_url, limit)
    if items:
        return items, "HTML fallback"

    return [], "Unavailable"


# -----------------------------
# Special sources
# -----------------------------
def get_tcs_news(limit=10):
    url = SOURCES["TCS Newsroom"]["url"]
    items = extract_html_articles(url, limit)

    # TCS pages can change structure. Use links that look like newsroom stories.
    if not items:
        try:
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            raw = []
            for a in soup.find_all("a", href=True):
                title = clean_text(a.get_text(" ", strip=True))
                href = a["href"]
                if len(title) >= 25 and any(
                    word in title.lower()
                    for word in ["tcs", "launch", "appoint", "award", "partner", "report", "ai", "technology"]
                ):
                    raw.append(make_item(title, absolute_url(url, href)))
            items = unique_items(raw)[:limit]
        except Exception:
            items = []

    return items[:limit]


def parse_money(text):
    if not text:
        return None
    m = re.search(r"(?:₹|Rs\.?\s*)\s*([\d,]+(?:\.\d+)?)", text)
    return m.group(1).replace(",", "") if m else None


def get_gold_rates():
    url = "https://www.goodreturns.in/gold-rates/bhubaneswar.html"
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        text = soup.get_text(" ", strip=True)

        # First try tables.
        rates = {}
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            for row in rows:
                cells = [clean_text(c.get_text(" ", strip=True)) for c in row.find_all(["th", "td"])]
                if not cells:
                    continue
                joined = " | ".join(cells).lower()
                if "24k" in joined or "22k" in joined:
                    for c in cells:
                        if "24k" in c.lower():
                            val = parse_money(c)
                            if val:
                                rates["24K"] = val
                        if "22k" in c.lower():
                            val = parse_money(c)
                            if val:
                                rates["22K"] = val

        # Common page-layout fallback: look for nearby purity labels.
        for purity in ["24K", "22K"]:
            if purity not in rates:
                pattern = rf"{purity}\s*(?:Gold)?\s*(?:/g|per gram)?\s*(?:₹|Rs\.?)?\s*([\d,]+)"
                m = re.search(pattern, text, re.I)
                if m:
                    rates[purity] = m.group(1).replace(",", "")

        return {
            "24K": rates.get("24K", "—"),
            "22K": rates.get("22K", "—"),
            "url": url,
        }
    except Exception:
        return {"24K": "—", "22K": "—", "url": url}


def get_india_population():
    url = "https://www.worldometers.info/world-population/india-population/"
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(" ", strip=True)

        # Prefer the "India Population" value.
        patterns = [
            r"India Population\s*([\d,]+)",
            r"current population of India.*?([\d,]{8,})",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.I)
            if m:
                return {"population": m.group(1), "url": url}

        # Search for a large comma-separated integer near "Population".
        m = re.search(r"Population of India.*?([\d,]{9,})", text, re.I)
        if m:
            return {"population": m.group(1), "url": url}

        return {"population": "—", "url": url}
    except Exception:
        return {"population": "—", "url": url}


# -----------------------------
# Cached data functions
# -----------------------------
@st.cache_data(ttl=900, show_spinner=False)
def load_news(source_name, limit=10):
    cfg = SOURCES[source_name]
    return get_news(source_name, cfg["url"], cfg["rss"], limit)


@st.cache_data(ttl=900, show_spinner=False)
def load_tcs(limit=10):
    return get_tcs_news(limit)


@st.cache_data(ttl=900, show_spinner=False)
def load_gold():
    return get_gold_rates()


@st.cache_data(ttl=900, show_spinner=False)
def load_population():
    return get_india_population()


# -----------------------------
# UI
# -----------------------------
st.markdown(
    """
    <style>
    .main {background: linear-gradient(180deg,#f8fafc 0%,#eef2ff 100%);}
    .hero {
        padding: 28px 32px;
        border-radius: 20px;
        background: linear-gradient(135deg,#111827,#1e3a8a,#7c3aed);
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 12px 30px rgba(30,41,59,.18);
    }
    .hero h1 {font-size: 38px; margin: 0 0 8px 0;}
    .hero p {font-size: 17px; margin: 0; opacity:.92;}
    .sponsor {
        margin-top: 18px;
        display:inline-block;
        padding:7px 13px;
        border:1px solid rgba(255,255,255,.3);
        border-radius:999px;
        font-weight:600;
        background:rgba(255,255,255,.10);
    }
    .card {
        background:white;
        border-radius:16px;
        padding:16px 18px;
        margin:10px 0;
        box-shadow:0 4px 16px rgba(15,23,42,.08);
        border:1px solid #e5e7eb;
    }
    .card a {text-decoration:none; color:#111827; font-weight:700; font-size:16px;}
    .meta {color:#64748b; font-size:12px; margin-top:7px;}
    .metric {
        background:white; padding:18px; border-radius:16px;
        border:1px solid #e5e7eb; box-shadow:0 4px 16px rgba(15,23,42,.07);
    }
    .footer {
        text-align:center; padding:24px; color:#475569;
        font-weight:600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <h1>📰 Swarup News & India Intelligence Dashboard</h1>
        <p>International • Technology • India • Odisha • TCS • Gold • Population</p>
        <div class="sponsor">Sponsored by Swarup</div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Dashboard Controls")
    st.caption("Data is refreshed automatically every 15 minutes.")
    if st.button("🔄 Refresh now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.markdown("### Sources")
    st.markdown("- Reuters")
    st.markdown("- News On AIR")
    st.markdown("- OdishaTV")
    st.markdown("- Goodreturns")
    st.markdown("- TCS")
    st.markdown("- Worldometer")

    st.divider()
    st.caption("For personal/informational use. Original publishers retain all rights.")

# Top metrics
gold = load_gold()
population = load_population()

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown('<div class="metric">🥇 <b>24K Gold</b><br><span style="font-size:26px">₹'
                + str(gold["24K"]) + '</span> / gram</div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="metric">🪙 <b>22K Gold</b><br><span style="font-size:26px">₹'
                + str(gold["22K"]) + '</span> / gram</div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="metric">🇮🇳 <b>India Population</b><br><span style="font-size:26px">'
                + str(population["population"]) + '</span></div>', unsafe_allow_html=True)

st.write("")

sections = [
    ("🌍 International News", "International News — Reuters"),
    ("💻 IT Industry News", "IT Industry News — Reuters Technology"),
    ("🇮🇳 India News", "India News — News On AIR"),
    ("🌴 Odisha News", "Odisha News — OdishaTV"),
]

for heading, source_name in sections:
    st.subheader(heading)
    items, method = load_news(source_name, 10)
    if not items:
        st.warning(f"Could not load this feed right now. Open the source directly: {SOURCES[source_name]['url']}")
    for idx, item in enumerate(items, 1):
        st.markdown(
            f"""
            <div class="card">
                <div style="color:#64748b;font-size:12px;font-weight:700;">#{idx}</div>
                <a href="{item['link']}" target="_blank">{item['title']}</a>
                {('<div class="meta">'+item['summary'][:220]+'…</div>') if item['summary'] else ''}
                {('<div class="meta">Published: '+item['published']+'</div>') if item['published'] else ''}
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.caption(f"Source: {SOURCES[source_name]['url']} • Collection method: {method}")

st.subheader("🏢 TCS Newsroom")
tcs_items = load_tcs(10)
if not tcs_items:
    st.warning("TCS newsroom could not be parsed right now. Use the source link below.")
for idx, item in enumerate(tcs_items, 1):
    st.markdown(
        f"""
        <div class="card">
            <div style="color:#64748b;font-size:12px;font-weight:700;">#{idx}</div>
            <a href="{item['link']}" target="_blank">{item['title']}</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
st.caption(f"Source: {SOURCES['TCS Newsroom']['url']}")

st.subheader("📊 Reference Links")
r1, r2 = st.columns(2)
with r1:
    st.link_button("🥇 Open Goodreturns — Bhubaneswar Gold Rates", gold["url"], use_container_width=True)
with r2:
    st.link_button("🇮🇳 Open Worldometer — India Population", population["url"], use_container_width=True)

st.markdown(
    """
    <div class="footer">
        🌱 Save paper, save trees, save the Earth<br>
        <span style="font-size:12px;font-weight:400;">
        Dashboard sponsored by Swarup • Last refresh: """
    + datetime.now().strftime("%d %b %Y, %I:%M %p")
    + """</span>
    </div>
    """,
    unsafe_allow_html=True,
)
