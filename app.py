
import re
import html
from datetime import datetime, timezone, timedelta
from urllib.parse import quote_plus

import feedparser
import requests
import streamlit as st
from bs4 import BeautifulSoup

# ------------------------------------------------------------
# Swarup News Dashboard
# A colorful Streamlit dashboard for current news, gold rate,
# TCS news and India's population.
# ------------------------------------------------------------

st.set_page_config(
    page_title="Swarup News Dashboard",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

IST = timezone(timedelta(hours=5, minutes=30))
TIMEOUT = 15
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/151 Safari/537.36"
    )
}

# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at 10% 0%, rgba(99,102,241,.18), transparent 28%),
        radial-gradient(circle at 90% 0%, rgba(236,72,153,.16), transparent 25%),
        linear-gradient(135deg, #f8fafc 0%, #eef2ff 48%, #fff1f2 100%);
}

.block-container {
    max-width: 1450px;
    padding-top: 1.2rem;
    padding-bottom: 2rem;
}

.hero {
    border-radius: 24px;
    padding: 30px 34px;
    color: white;
    background: linear-gradient(120deg, #111827, #4338ca 48%, #be185d);
    box-shadow: 0 18px 45px rgba(31,41,55,.20);
    margin-bottom: 20px;
}

.hero h1 {
    font-size: 2.25rem;
    margin: 0;
    font-weight: 800;
    letter-spacing: -1px;
}

.hero p {
    margin: 7px 0 0;
    opacity: .9;
}

.sponsor {
    margin-top: 18px;
    font-size: .9rem;
    font-weight: 700;
    opacity: .95;
}

.metric-card {
    border-radius: 18px;
    padding: 18px 20px;
    background: rgba(255,255,255,.88);
    border: 1px solid rgba(148,163,184,.20);
    box-shadow: 0 8px 24px rgba(15,23,42,.07);
    min-height: 105px;
}

.metric-label {
    color: #64748b;
    font-size: .78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .8px;
}

.metric-value {
    margin-top: 5px;
    color: #111827;
    font-size: 1.65rem;
    font-weight: 800;
}

.metric-note {
    color: #64748b;
    font-size: .75rem;
    margin-top: 3px;
}

.section-title {
    margin-top: 28px;
    margin-bottom: 12px;
    font-size: 1.35rem;
    font-weight: 800;
    color: #111827;
}

.news-card {
    background: rgba(255,255,255,.94);
    border: 1px solid rgba(148,163,184,.18);
    border-radius: 16px;
    padding: 17px 18px;
    margin-bottom: 12px;
    box-shadow: 0 7px 20px rgba(15,23,42,.055);
}

.news-number {
    display: inline-block;
    min-width: 31px;
    height: 31px;
    line-height: 31px;
    text-align: center;
    border-radius: 50%;
    background: #eef2ff;
    color: #4338ca;
    font-weight: 800;
    margin-right: 8px;
}

.news-headline {
    color: #111827;
    font-size: 1rem;
    font-weight: 750;
    line-height: 1.38;
}

.news-summary {
    margin-top: 8px;
    color: #475569;
    font-size: .88rem;
    line-height: 1.55;
}

.news-source {
    margin-top: 9px;
    color: #94a3b8;
    font-size: .72rem;
    font-weight: 600;
}

.gold-box {
    border-radius: 18px;
    padding: 20px;
    background: linear-gradient(135deg, #fff7ed, #fef3c7);
    border: 1px solid #fde68a;
    box-shadow: 0 8px 24px rgba(120,53,15,.08);
}

.gold-price {
    font-size: 1.8rem;
    font-weight: 800;
    color: #92400e;
}

.gold-label {
    font-size: .76rem;
    color: #92400e;
    font-weight: 800;
    text-transform: uppercase;
}

.footer {
    text-align: center;
    margin-top: 30px;
    color: #64748b;
    font-size: .78rem;
}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# Helpers
# -----------------------------
def clean_text(value: str, max_chars: int = 300) -> str:
    if not value:
        return ""
    value = html.unescape(value)
    value = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) > max_chars:
        value = value[:max_chars].rsplit(" ", 1)[0] + "…"
    return value


def fetch(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return response.text


def google_news_rss(query: str, hl: str = "en-IN", gl: str = "IN", ceid: str = "IN:en"):
    url = (
        "https://news.google.com/rss/search?"
        f"q={quote_plus(query)}&hl={hl}&gl={gl}&ceid={ceid}"
    )
    feed = feedparser.parse(url)
    results = []

    for entry in feed.entries:
        title = clean_text(getattr(entry, "title", ""))
        summary = clean_text(getattr(entry, "summary", ""))
        source = ""
        if hasattr(entry, "source") and getattr(entry.source, "title", None):
            source = clean_text(entry.source.title)

        if not summary:
            summary = "Latest reporting and developments on this story."

        # Google News titles may contain " - Publication".
        if " - " in title and not source:
            title, source = title.rsplit(" - ", 1)

        results.append({
            "title": title,
            "summary": summary,
            "source": source or "News source",
        })

    # Remove obvious duplicates by normalized title.
    seen = set()
    unique = []
    for item in results:
        key = re.sub(r"[^a-z0-9]+", "", item["title"].lower())
        if key and key not in seen:
            seen.add(key)
            unique.append(item)

    return unique[:10]


def parse_money(text: str):
    if not text:
        return None
    m = re.search(r"₹\s*([\d,]+(?:\.\d+)?)", text)
    if not m:
        return None
    return float(m.group(1).replace(",", ""))


@st.cache_data(ttl=900, show_spinner=False)
def get_gold_rates():
    # Required user-specified source.
    url = "https://www.goodreturns.in/gold-rates/bhubaneswar.html"
    soup = BeautifulSoup(fetch(url), "html.parser")
    text = soup.get_text(" ", strip=True)

    rates = {}

    # First try the page's visible table/card values.
    patterns = {
        "24K": r"24K\s*Gold\s*/g\s*₹\s*([\d,]+(?:\.\d+)?)",
        "22K": r"22K\s*Gold\s*/g\s*₹\s*([\d,]+(?:\.\d+)?)",
    }

    for karat, pattern in patterns.items():
        match = re.search(pattern, text, flags=re.I)
        if match:
            rates[karat] = float(match.group(1).replace(",", ""))

    # Fallback: look for the "per gram" sentence.
    if len(rates) < 2:
        fallback = re.search(
            r"₹([\d,]+(?:\.\d+)?)\s+per gram for 24 karat.*?"
            r"₹([\d,]+(?:\.\d+)?)\s+per gram for 22 karat",
            text,
            flags=re.I,
        )
        if fallback:
            rates.setdefault("24K", float(fallback.group(1).replace(",", "")))
            rates.setdefault("22K", float(fallback.group(2).replace(",", "")))

    return {
        "24K": rates.get("24K"),
        "22K": rates.get("22K"),
        "updated": datetime.now(IST).strftime("%d %b %Y, %I:%M %p"),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def get_india_population():
    # Required user-specified source.
    url = "https://www.worldometers.info/world-population/india-population/"
    soup = BeautifulSoup(fetch(url), "html.parser")
    text = soup.get_text(" ", strip=True)

    # Worldometer commonly presents:
    # "The current population of India is 1,xxx,xxx,xxx ..."
    match = re.search(
        r"The current population of India is\s*([\d,]+)",
        text,
        flags=re.I,
    )

    if not match:
        # Fallback to a population heading/table value.
        match = re.search(
            r"India Population.*?([\d,]{8,})",
            text,
            flags=re.I,
        )

    if not match:
        raise ValueError("Could not find India's current population on Worldometer.")

    return {
        "population": int(match.group(1).replace(",", "")),
        "updated": datetime.now(IST).strftime("%d %b %Y, %I:%M %p"),
    }


# -----------------------------
# Data loading
# -----------------------------
@st.cache_data(ttl=900, show_spinner=False)
def load_all_news():
    return {
        "International News": google_news_rss(
            "top international world news OR global news"
        ),
        "IT Industry News": google_news_rss(
            "IT industry technology AI cybersecurity software cloud semiconductor"
        ),
        "India News": google_news_rss(
            "India national news government economy politics business"
        ),
        "Odisha News": google_news_rss(
            "Odisha news Bhubaneswar Cuttack Odisha government weather"
        ),
        "TCS News in India": google_news_rss(
            '"TCS" India Tata Consultancy Services latest news'
        ),
    }


# -----------------------------
# Header
# -----------------------------
now = datetime.now(IST)

st.markdown(
    f"""
<div class="hero">
    <h1>📰 Swarup News Dashboard</h1>
    <p>Today's concise briefing — India, Odisha, World, Technology, TCS, Gold & Population</p>
    <div class="sponsor">Sponsored by Swarup • Updated {now.strftime("%d %b %Y, %I:%M %p")} IST</div>
</div>
""",
    unsafe_allow_html=True,
)

# Manual refresh
col_a, col_b = st.columns([8, 1])
with col_b:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# -----------------------------
# Key metrics
# -----------------------------
try:
    gold = get_gold_rates()
except Exception:
    gold = {"24K": None, "22K": None, "updated": "Unavailable"}

try:
    population = get_india_population()
except Exception:
    population = {"population": None, "updated": "Unavailable"}

m1, m2, m3 = st.columns(3)

with m1:
    value = f"₹{gold['24K']:,.0f}/g" if gold["24K"] else "Unavailable"
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">Gold • 24K</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-note">Bhubaneswar • Goodreturns</div></div>',
        unsafe_allow_html=True,
    )

with m2:
    value = f"₹{gold['22K']:,.0f}/g" if gold["22K"] else "Unavailable"
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">Gold • 22K</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-note">Bhubaneswar • Goodreturns</div></div>',
        unsafe_allow_html=True,
    )

with m3:
    value = f"{population['population']:,}" if population["population"] else "Unavailable"
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">India Current Population</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-note">Worldometer live population figure</div></div>',
        unsafe_allow_html=True,
    )

# -----------------------------
# News
# -----------------------------
try:
    news = load_all_news()
except Exception as exc:
    st.error(f"News feed could not be loaded: {exc}")
    news = {}

def render_news_section(title, items, emoji):
    st.markdown(f'<div class="section-title">{emoji} {title}</div>', unsafe_allow_html=True)

    if not items:
        st.warning("No stories were returned right now. Press Refresh to try again.")
        return

    for idx, item in enumerate(items[:10], 1):
        title_text = clean_text(item["title"], 180)
        summary = clean_text(item["summary"], 360)
        source = clean_text(item["source"], 80)

        st.markdown(
            f"""
<div class="news-card">
    <div class="news-headline">
        <span class="news-number">{idx}</span>{html.escape(title_text)}
    </div>
    <div class="news-summary">{html.escape(summary)}</div>
    <div class="news-source">{html.escape(source)}</div>
</div>
""",
            unsafe_allow_html=True,
        )

# Use two columns for a professional newspaper-style layout.
left, right = st.columns(2)

with left:
    render_news_section(
        "Top 10 International News",
        news.get("International News", []),
        "🌍",
    )
    render_news_section(
        "Top 10 India News",
        news.get("India News", []),
        "🇮🇳",
    )
    render_news_section(
        "Top 10 Odisha News",
        news.get("Odisha News", []),
        "🌾",
    )

with right:
    render_news_section(
        "Top 10 IT Industry News",
        news.get("IT Industry News", []),
        "💻",
    )
    render_news_section(
        "Top 10 TCS News in India",
        news.get("TCS News in India", []),
        "🏢",
    )

# -----------------------------
# Footer
# -----------------------------
st.markdown(
    """
<div class="footer">
    <b>Sponsored by Swarup</b><br>
    News is presented as headlines with short summaries. Gold and population figures
    are fetched from the specified online sources. Rates and population can change
    during the day. News availability depends on the public RSS/news feeds.
</div>
""",
    unsafe_allow_html=True,
)
