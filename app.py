import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import feedparser
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="Swarup Daily News Dashboard",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Configuration
# -----------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/151.0 Safari/537.36"
    )
}

GOODRETURNS_URL = "https://www.goodreturns.in/gold-rates/bhubaneswar.html"
TCS_URL = "https://www.tcs.com/who-we-are/newsroom"
WORLDOMETERS_URL = "https://www.worldometers.info/world-population/india-population/"

# Google News RSS is used for the general news sections. It does not require an API key.
RSS_FEEDS = {
    "International": "https://news.google.com/rss/search?q=world+international+news+when%3A1d&hl=en-IN&gl=IN&ceid=IN%3Aen",
    "India": "https://news.google.com/rss/search?q=India+news+when%3A1d&hl=en-IN&gl=IN&ceid=IN%3Aen",
    "Odisha": "https://news.google.com/rss/search?q=Odisha+news+when%3A1d&hl=en-IN&gl=IN&ceid=IN%3Aen",
}


# -----------------------------
# Helpers
# -----------------------------
@st.cache_data(ttl=600, show_spinner=False)
def get_rss_news(url, limit=10):
    feed = feedparser.parse(url)
    items = []
    seen = set()

    for entry in feed.entries:
        title = re.sub(r"\s+", " ", entry.get("title", "")).strip()
        link = entry.get("link", "")
        if not title or not link:
            continue

        # Google News titles commonly end with " - Publisher".
        publisher = ""
        if " - " in title:
            title, publisher = title.rsplit(" - ", 1)

        key = re.sub(r"[^a-z0-9]+", "", title.lower())
        if key in seen:
            continue
        seen.add(key)

        published = entry.get("published", "")
        try:
            dt = parsedate_to_datetime(published)
            published_display = dt.strftime("%d %b %Y, %I:%M %p")
        except Exception:
            published_display = published

        items.append(
            {
                "title": title,
                "publisher": publisher or "News source",
                "published": published_display,
                "link": link,
            }
        )
        if len(items) >= limit:
            break

    return items


def fetch_html(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.text


@st.cache_data(ttl=600, show_spinner=False)
def get_gold_rates():
    html = fetch_html(GOODRETURNS_URL)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    # First preference: the wording used in the GoodReturns page itself.
    patterns = [
        r"gold price in Bhubaneswar stands at ₹\s*([\d,]+)\s*per gram for 24 karat.*?"
        r"₹\s*([\d,]+)\s*per gram for 22 karat",
        r"Bhubaneswar.*?24K\s*Gold\s*/g.*?₹\s*([\d,]+).*?"
        r"22K\s*Gold\s*/g.*?₹\s*([\d,]+)",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, flags=re.I | re.S)
        if m:
            return {
                "24K": int(m.group(1).replace(",", "")),
                "22K": int(m.group(2).replace(",", "")),
                "source": GOODRETURNS_URL,
                "updated": datetime.now().strftime("%d %b %Y, %I:%M %p"),
            }

    raise ValueError("Could not locate 24K/22K gold rates on GoodReturns.")


@st.cache_data(ttl=1800, show_spinner=False)
def get_tcs_news(limit=10):
    html = fetch_html(TCS_URL)
    soup = BeautifulSoup(html, "html.parser")

    results = []
    seen = set()

    # TCS newsroom pages contain article links under /who-we-are/newsroom/.
    for a in soup.select("a[href]"):
        title = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        href = a.get("href", "")

        if not title or len(title) < 12:
            continue
        if "/who-we-are/newsroom/" not in href:
            continue

        if href.startswith("/"):
            href = "https://www.tcs.com" + href
        elif href.startswith("./"):
            href = "https://www.tcs.com/who-we-are/newsroom/" + href[2:]

        # Skip navigation/filter links and keep likely article titles.
        low = title.lower()
        if low in {"view all", "discover more", "press releases", "news alerts", "media kit"}:
            continue

        key = re.sub(r"[^a-z0-9]+", "", title.lower())
        if key in seen:
            continue
        seen.add(key)

        results.append({"title": title, "link": href})

        if len(results) >= limit:
            break

    return results


@st.cache_data(ttl=1800, show_spinner=False)
def get_population():
    html = fetch_html(WORLDOMETERS_URL)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    # Worldometer publishes a live counter and a 2026 mid-year estimate.
    live_match = re.search(
        r"The current population of India is\s*([\d,]+)",
        text,
        flags=re.I,
    )
    estimate_match = re.search(
        r"India 2026 population is estimated at\s*([\d,]+)",
        text,
        flags=re.I,
    )

    if not live_match and not estimate_match:
        # Fallback to a table row containing 2026.
        for row in soup.select("tr"):
            cells = [c.get_text(" ", strip=True) for c in row.select("td")]
            if cells and cells[0] == "2026" and len(cells) > 1:
                estimate_match = re.match(r"([\d,]+)", cells[1])
                break

    return {
        "live": live_match.group(1) if live_match else "Unavailable",
        "mid_year_2026": estimate_match.group(1) if estimate_match else "Unavailable",
        "source": WORLDOMETERS_URL,
    }


def money(value):
    return f"₹{value:,.0f}"


def render_news_card(item, index):
    publisher = item.get("publisher", "")
    published = item.get("published", "")
    title = item["title"]
    link = item["link"]

    st.markdown(
        f"""
        <div class="news-card">
            <div class="news-number">{index:02d}</div>
            <div class="news-content">
                <a href="{link}" target="_blank">{title}</a>
                <div class="meta">{publisher} &nbsp;•&nbsp; {published}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_tcs_card(item, index):
    st.markdown(
        f"""
        <div class="tcs-card">
            <div class="news-number">{index:02d}</div>
            <div class="news-content">
                <a href="{item['link']}" target="_blank">{item['title']}</a>
                <div class="meta">Tata Consultancy Services • TCS Newsroom</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at 10% 0%, rgba(59,130,246,.13), transparent 30%),
            radial-gradient(circle at 95% 5%, rgba(168,85,247,.14), transparent 28%),
            #f6f8fc;
    }

    .hero {
        padding: 28px 30px;
        border-radius: 24px;
        background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 48%, #7c3aed 100%);
        color: white;
        box-shadow: 0 15px 35px rgba(15,23,42,.20);
        margin-bottom: 22px;
    }

    .hero h1 {
        font-size: 2.4rem;
        margin: 0 0 6px 0;
        font-weight: 800;
    }

    .hero p {
        margin: 4px 0;
        opacity: .92;
    }

    .sponsor {
        display: inline-block;
        margin-top: 14px;
        padding: 7px 13px;
        border-radius: 999px;
        background: rgba(255,255,255,.14);
        border: 1px solid rgba(255,255,255,.25);
        font-size: .88rem;
    }

    .section-title {
        font-size: 1.35rem;
        font-weight: 800;
        margin: 12px 0 10px 0;
        color: #0f172a;
    }

    .news-card, .tcs-card {
        display: flex;
        gap: 12px;
        align-items: flex-start;
        background: rgba(255,255,255,.94);
        border: 1px solid #e5e7eb;
        border-left: 5px solid #2563eb;
        border-radius: 14px;
        padding: 12px 14px;
        margin: 8px 0;
        box-shadow: 0 5px 16px rgba(15,23,42,.05);
    }

    .tcs-card {
        border-left-color: #7c3aed;
    }

    .news-number {
        font-weight: 900;
        color: #2563eb;
        min-width: 28px;
    }

    .news-content a {
        color: #111827 !important;
        text-decoration: none;
        font-weight: 700;
        line-height: 1.35;
    }

    .news-content a:hover {
        color: #2563eb !important;
    }

    .meta {
        color: #64748b;
        font-size: .76rem;
        margin-top: 5px;
    }

    .metric-card {
        padding: 17px;
        border-radius: 18px;
        background: white;
        border: 1px solid #e5e7eb;
        box-shadow: 0 7px 22px rgba(15,23,42,.06);
        text-align: center;
    }

    .metric-label {
        color: #64748b;
        font-size: .82rem;
        font-weight: 700;
    }

    .metric-value {
        font-size: 1.65rem;
        font-weight: 900;
        color: #0f172a;
        margin-top: 4px;
    }

    .source-note {
        color: #64748b;
        font-size: .75rem;
        margin-top: 5px;
    }

    .footer {
        margin-top: 35px;
        padding: 18px;
        border-radius: 18px;
        background: #0f172a;
        color: white;
        text-align: center;
    }

    .footer .eco {
        font-size: 1.05rem;
        font-weight: 800;
        color: #86efac;
    }

    @media (max-width: 700px) {
        .hero h1 { font-size: 1.8rem; }
        .hero { padding: 22px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Header
# -----------------------------
st.markdown(
    """
    <div class="hero">
        <h1>📰 Swarup Daily News Dashboard</h1>
        <p>News • India • Odisha • Gold • TCS • Population — all in one place</p>
        <div class="sponsor">Sponsored by Swarup</div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### ⚙️ Dashboard")
    st.caption("Live online sources are fetched when the page refreshes.")
    if st.button("🔄 Refresh all data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown("### 🔗 Source pages")
    st.markdown(f"[GoodReturns – Bhubaneswar Gold]({GOODRETURNS_URL})")
    st.markdown(f"[TCS Newsroom]({TCS_URL})")
    st.markdown(f"[Worldometer – India Population]({WORLDOMETERS_URL})")
    st.caption("General news is collected through Google News RSS searches.")

# -----------------------------
# Live indicators
# -----------------------------
st.markdown('<div class="section-title">📊 Today at a glance</div>', unsafe_allow_html=True)

gold = None
population = None
errors = []

try:
    gold = get_gold_rates()
except Exception as e:
    errors.append(f"Gold: {e}")

try:
    population = get_population()
except Exception as e:
    errors.append(f"Population: {e}")

m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">🥇 24K Gold / gram</div>'
        f'<div class="metric-value">{money(gold["24K"]) if gold else "—"}</div>'
        f'<div class="source-note">Bhubaneswar • GoodReturns</div></div>',
        unsafe_allow_html=True,
    )

with m2:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">🪙 22K Gold / gram</div>'
        f'<div class="metric-value">{money(gold["22K"]) if gold else "—"}</div>'
        f'<div class="source-note">Bhubaneswar • GoodReturns</div></div>',
        unsafe_allow_html=True,
    )

with m3:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">🇮🇳 India Live Population</div>'
        f'<div class="metric-value">{population["live"] if population else "—"}</div>'
        f'<div class="source-note">Worldometer live estimate</div></div>',
        unsafe_allow_html=True,
    )

with m4:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">📅 2026 Mid-year Population</div>'
        f'<div class="metric-value">{population["mid_year_2026"] if population else "—"}</div>'
        f'<div class="source-note">Worldometer estimate</div></div>',
        unsafe_allow_html=True,
    )

if errors:
    st.warning("Some live data could not be loaded: " + " | ".join(errors))

st.markdown("---")

# -----------------------------
# News sections
# -----------------------------
try:
    international = get_rss_news(RSS_FEEDS["International"], 10)
except Exception:
    international = []

try:
    india = get_rss_news(RSS_FEEDS["India"], 10)
except Exception:
    india = []

try:
    odisha = get_rss_news(RSS_FEEDS["Odisha"], 10)
except Exception:
    odisha = []

left, right = st.columns(2, gap="large")

with left:
    st.markdown('<div class="section-title">🌍 Top 10 International News</div>', unsafe_allow_html=True)
    if international:
        for i, item in enumerate(international, 1):
            render_news_card(item, i)
    else:
        st.info("International news is temporarily unavailable.")

with right:
    st.markdown('<div class="section-title">🇮🇳 Top 10 India News</div>', unsafe_allow_html=True)
    if india:
        for i, item in enumerate(india, 1):
            render_news_card(item, i)
    else:
        st.info("India news is temporarily unavailable.")

st.markdown('<div class="section-title">🌊 Top 10 Odisha News</div>', unsafe_allow_html=True)
if odisha:
    for i, item in enumerate(odisha, 1):
        render_news_card(item, i)
else:
    st.info("Odisha news is temporarily unavailable.")

st.markdown('<div class="section-title">💻 Top TCS News</div>', unsafe_allow_html=True)
try:
    tcs = get_tcs_news(10)
except Exception as e:
    tcs = []
    st.warning(f"TCS Newsroom could not be read right now: {e}")

if tcs:
    for i, item in enumerate(tcs, 1):
        render_tcs_card(item, i)
else:
    st.info("TCS newsroom items are temporarily unavailable.")

# -----------------------------
# Footer
# -----------------------------
today = datetime.now().strftime("%d %B %Y")
st.markdown(
    f"""
    <div class="footer">
        <div><strong>Sponsored by Swarup</strong> • Updated on {today}</div>
        <div class="eco">🌳 Save paper, save trees, save the Earth</div>
    </div>
    """,
    unsafe_allow_html=True,
)
