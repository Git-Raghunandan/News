import re
import html
import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import feedparser
import requests
import streamlit as st
from bs4 import BeautifulSoup

# -----------------------------
# Configuration
# -----------------------------
APP_TITLE = "Swarup Daily News"
SPONSOR = "Sponsored by Swarup"

GOODRETURNS_URL = "https://www.goodreturns.in/gold-rates/bhubaneswar.html"
WORLDMETERS_URL = "https://www.worldometers.info/world-population/india-population/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151 Safari/537.36"
    )
}

CATEGORIES = {
    "🌍 International News": [
        "international world news today",
        "global breaking news today",
        "world politics economy conflict today",
    ],
    "💻 IT Industry News": [
        "IT industry technology business AI cloud cybersecurity today",
        "information technology industry news today",
        "software technology companies industry news today",
    ],
    "🇮🇳 India News": [
        "India national news today",
        "India politics economy business news today",
        "India government policy news today",
    ],
    "🟢 Odisha News": [
        "Odisha news today",
        "Odisha Bhubaneswar Cuttack news today",
        "Odisha government weather crime development today",
    ],
    "🏢 TCS News in India": [
        "TCS Tata Consultancy Services India news today",
        "TCS India employees business technology news today",
        "Tata Consultancy Services India latest news today",
    ],
}

# Google News RSS is used as an aggregator. The dashboard does not expose
# clickable article links to viewers, as requested.
GOOGLE_NEWS_RSS = (
    "https://news.google.com/rss/search?q={query}"
    "&hl=en-IN&gl=IN&ceid=IN:en"
)


# -----------------------------
# Helpers
# -----------------------------
def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def parse_date(entry):
    try:
        if getattr(entry, "published_parsed", None):
            return datetime.fromtimestamp(
                time.mktime(entry.published_parsed)
            )
        if getattr(entry, "published", None):
            return parsedate_to_datetime(entry.published).replace(tzinfo=None)
    except Exception:
        pass
    return datetime.now()


def split_sentences(text):
    text = clean_text(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def make_five_lines(title, summary):
    """
    Creates five short, understandable lines from RSS title/description.
    It deliberately does not invent facts that are absent from the feed.
    """
    title = clean_text(title)
    summary = clean_text(summary)

    sentences = split_sentences(summary)

    # Remove an RSS description that simply repeats the title.
    sentences = [s for s in sentences if s.lower() != title.lower()]

    lines = [title]

    for s in sentences:
        if s.lower() not in {x.lower() for x in lines}:
            lines.append(s)

    # If the feed description is short, use title/summary chunks rather than
    # inventing details.
    if len(lines) < 5 and summary:
        words = summary.split()
        remaining = 5 - len(lines)
        chunk_size = max(8, len(words) // max(1, remaining))
        chunks = [
            " ".join(words[i:i + chunk_size])
            for i in range(0, len(words), chunk_size)
        ]
        for c in chunks:
            if c and c.lower() not in {x.lower() for x in lines}:
                lines.append(c)
            if len(lines) >= 5:
                break

    fallback = [
        "The report is part of the latest news cycle.",
        "The available report provides the main context for the story.",
        "The development may be relevant to people following this topic.",
        "Further details can change as the story develops.",
    ]

    for f in fallback:
        if len(lines) >= 5:
            break
        lines.append(f)

    return lines[:5]


def fetch_rss(query, limit=10):
    url = GOOGLE_NEWS_RSS.format(query=quote_plus(query))
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()

    feed = feedparser.parse(response.content)
    items = []

    for entry in feed.entries:
        title = clean_text(getattr(entry, "title", ""))
        summary = clean_text(
            getattr(entry, "summary", "")
            or getattr(entry, "description", "")
        )

        if not title:
            continue

        items.append(
            {
                "title": title,
                "summary": summary,
                "published": parse_date(entry),
                "lines": make_five_lines(title, summary),
            }
        )

    return items


@st.cache_data(ttl=900, show_spinner=False)
def get_category_news(queries, limit=10):
    combined = []
    seen = set()

    for query in queries:
        try:
            items = fetch_rss(query, limit=limit)
        except Exception:
            continue

        for item in items:
            key = re.sub(r"[^a-z0-9]+", "", item["title"].lower())
            if key in seen:
                continue
            seen.add(key)
            combined.append(item)

    combined.sort(key=lambda x: x["published"], reverse=True)
    return combined[:limit]


@st.cache_data(ttl=900, show_spinner=False)
def get_gold_rates():
    response = requests.get(GOODRETURNS_URL, headers=HEADERS, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    text = clean_text(soup.get_text(" ", strip=True))

    result = {"24k": None, "22k": None, "date": None}

    # Prefer the page's structured/current text.
    patterns = {
        "24k": [
            r"₹\s*([\d,]+)\s*per gram for 24 karat",
            r"24K\s+Gold\s*/g\s*₹\s*([\d,]+)",
            r"24K\s+Gold\s*₹\s*([\d,]+)",
        ],
        "22k": [
            r"₹\s*([\d,]+)\s*per gram for 22 karat",
            r"22K\s+Gold\s*/g\s*₹\s*([\d,]+)",
            r"22K\s+Gold\s*₹\s*([\d,]+)",
        ],
    }

    for key, pats in patterns.items():
        for pat in pats:
            m = re.search(pat, text, flags=re.I)
            if m:
                result[key] = int(m.group(1).replace(",", ""))
                break

    date_match = re.search(
        r"(\d{1,2}\s+[A-Za-z]+\s+20\d{2})", text
    )
    if date_match:
        result["date"] = date_match.group(1)

    return result


@st.cache_data(ttl=900, show_spinner=False)
def get_population():
    response = requests.get(WORLDMETERS_URL, headers=HEADERS, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    text = clean_text(soup.get_text(" ", strip=True))

    result = {"live": None, "midyear": None, "rank": None}

    m = re.search(
        r"The current population of India is\s*([\d,]+)",
        text,
        flags=re.I,
    )
    if m:
        result["live"] = int(m.group(1).replace(",", ""))

    m = re.search(
        r"India 2026 population is estimated at\s*([\d,]+)",
        text,
        flags=re.I,
    )
    if m:
        result["midyear"] = int(m.group(1).replace(",", ""))

    m = re.search(
        r"India ranks number\s*(\d+)",
        text,
        flags=re.I,
    )
    if m:
        result["rank"] = int(m.group(1))

    return result


def render_news_card(item, number):
    lines = item["lines"]
    st.markdown(
        f"""
        <div class="news-card">
            <div class="news-number">{number:02d}</div>
            <div class="news-body">
                <div class="news-title">{html.escape(lines[0])}</div>
                <div class="news-meta">
                    {item["published"].strftime("%d %b %Y, %I:%M %p")}
                </div>
                <div class="news-lines">
                    <div>{html.escape(lines[0])}</div>
                    <div>{html.escape(lines[1])}</div>
                    <div>{html.escape(lines[2])}</div>
                    <div>{html.escape(lines[3])}</div>
                    <div>{html.escape(lines[4])}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------
# Page
# -----------------------------
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #07111f 0%, #0b1f36 45%, #112b46 100%);
        color: #f4f7fb;
    }

    .main-title {
        font-size: 3rem;
        font-weight: 800;
        letter-spacing: -1px;
        margin-bottom: 0;
    }

    .subtitle {
        font-size: 1rem;
        opacity: .82;
        margin-top: 4px;
    }

    .sponsor {
        display: inline-block;
        padding: 7px 14px;
        border-radius: 999px;
        background: linear-gradient(90deg, #f59e0b, #ef4444);
        color: white;
        font-weight: 700;
        margin: 12px 0 18px 0;
    }

    .metric-card {
        padding: 20px;
        border-radius: 18px;
        background: rgba(255,255,255,.08);
        border: 1px solid rgba(255,255,255,.12);
        box-shadow: 0 8px 30px rgba(0,0,0,.18);
        min-height: 130px;
    }

    .metric-label {
        font-size: .85rem;
        opacity: .72;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 800;
        margin-top: 6px;
    }

    .metric-small {
        font-size: .78rem;
        opacity: .65;
        margin-top: 4px;
    }

    .section-header {
        font-size: 1.65rem;
        font-weight: 800;
        margin-top: 30px;
        margin-bottom: 14px;
    }

    .news-card {
        display: flex;
        gap: 16px;
        margin: 12px 0;
        padding: 18px;
        border-radius: 18px;
        background: rgba(255,255,255,.065);
        border: 1px solid rgba(255,255,255,.11);
        box-shadow: 0 8px 24px rgba(0,0,0,.14);
    }

    .news-number {
        font-size: 1.35rem;
        font-weight: 900;
        opacity: .42;
        min-width: 38px;
    }

    .news-body {
        flex: 1;
    }

    .news-title {
        font-size: 1.15rem;
        font-weight: 800;
        line-height: 1.35;
    }

    .news-meta {
        font-size: .76rem;
        opacity: .58;
        margin: 6px 0 10px;
    }

    .news-lines div {
        margin: 5px 0;
        line-height: 1.45;
        opacity: .92;
    }

    .news-lines div:first-child {
        font-weight: 700;
        opacity: 1;
    }

    .footer {
        text-align: center;
        opacity: .55;
        padding: 30px 0 10px;
        font-size: .8rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="main-title">📰 Swarup Daily News</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">A clean daily briefing: World • IT • India • Odisha • TCS</div>',
    unsafe_allow_html=True,
)
st.markdown(f'<div class="sponsor">{SPONSOR}</div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

try:
    gold = get_gold_rates()
except Exception:
    gold = {"24k": None, "22k": None, "date": None}

try:
    population = get_population()
except Exception:
    population = {"live": None, "midyear": None, "rank": None}

with col1:
    value = f"₹{gold['24k']:,}/g" if gold["24k"] else "Unavailable"
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">24K Gold</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-small">Bhubaneswar • GoodReturns</div></div>',
        unsafe_allow_html=True,
    )

with col2:
    value = f"₹{gold['22k']:,}/g" if gold["22k"] else "Unavailable"
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">22K Gold</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-small">Bhubaneswar • GoodReturns</div></div>',
        unsafe_allow_html=True,
    )

with col3:
    value = f"{population['live']:,}" if population["live"] else "Unavailable"
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">India Population</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-small">Worldometer live figure</div></div>',
        unsafe_allow_html=True,
    )

with col4:
    now = datetime.now().strftime("%d %b %Y")
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">Dashboard Date</div>'
        f'<div class="metric-value">{now}</div>'
        f'<div class="metric-small">Refresh for latest feeds</div></div>',
        unsafe_allow_html=True,
    )

st.divider()

if st.button("🔄 Refresh all news & rates", type="primary"):
    st.cache_data.clear()
    st.rerun()

st.caption(
    "News is summarized from current RSS results. Article links are intentionally "
    "not displayed. Gold and population figures are fetched from the requested pages."
)

for category, queries in CATEGORIES.items():
    st.markdown(f'<div class="section-header">{category}</div>', unsafe_allow_html=True)

    with st.spinner(f"Loading {category}..."):
        news = get_category_news(tuple(queries), limit=10)

    if not news:
        st.warning("No current items were returned. Please refresh.")
        continue

    for idx, item in enumerate(news, start=1):
        render_news_card(item, idx)

st.markdown(
    '<div class="footer">Swarup Daily News • Sponsored by Swarup • '
    'Automatically refreshed when the dashboard is opened/refreshed</div>',
    unsafe_allow_html=True,
)
