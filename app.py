import re
import html
from datetime import datetime
from urllib.parse import quote

import requests
import feedparser
import streamlit as st
from bs4 import BeautifulSoup

# ------------------------------------------------------------
# Swarup News Dashboard
# Streamlit dashboard: international, IT, India, Odisha,
# TCS India, Bhubaneswar gold rates and India population.
# ------------------------------------------------------------

st.set_page_config(
    page_title="Swarup News Dashboard",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0 Safari/537.36"
    )
}

GOODRETURNS_URL = "https://www.goodreturns.in/gold-rates/bhubaneswar.html"
WORLDMETERS_URL = "https://www.worldometers.info/world-population/india-population/"

# Google News RSS is used only as a news aggregation endpoint.
# The dashboard intentionally does not display clickable article URLs.
NEWS_QUERIES = {
    "🌍 International News": "world international latest news",
    "💻 IT Industry News": "technology IT industry AI cloud cybersecurity software",
    "🇮🇳 India News": "India latest national news",
    "🌊 Odisha News": "Odisha latest news Bhubaneswar Odisha",
    "🏢 TCS News in India": '"TCS" India Tata Consultancy Services',
}

CATEGORY_COLORS = {
    "🌍 International News": "#4F46E5",
    "💻 IT Industry News": "#0891B2",
    "🇮🇳 India News": "#EA580C",
    "🌊 Odisha News": "#059669",
    "🏢 TCS News in India": "#7C3AED",
}


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    soup = BeautifulSoup(value, "html.parser")
    text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def shorten(text: str, limit: int = 300) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut + "…"


def google_news_rss(query: str, limit: int = 10):
    url = (
        "https://news.google.com/rss/search?"
        f"q={quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
    )
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        feed = feedparser.parse(response.content)

        items = []
        seen = set()

        for entry in feed.entries:
            title = clean_text(entry.get("title", ""))
            # Google News often formats title as "Headline - Publisher".
            publisher = ""
            if " - " in title:
                title, publisher = title.rsplit(" - ", 1)

            summary = clean_text(entry.get("summary", ""))
            key = re.sub(r"[^a-z0-9]+", "", title.lower())

            if not title or key in seen:
                continue

            seen.add(key)
            items.append(
                {
                    "title": title,
                    "summary": shorten(summary, 320)
                    or "A developing story covered by the news feed.",
                    "publisher": publisher or "News feed",
                    "published": entry.get("published", ""),
                }
            )

            if len(items) >= limit:
                break

        return items
    except Exception as exc:
        return [
            {
                "title": "News feed temporarily unavailable",
                "summary": f"Could not refresh this section right now: {exc}",
                "publisher": "System",
                "published": "",
            }
        ]


@st.cache_data(ttl=900, show_spinner=False)
def get_all_news():
    return {name: google_news_rss(query, 10) for name, query in NEWS_QUERIES.items()}


@st.cache_data(ttl=900, show_spinner=False)
def get_gold_rates():
    response = requests.get(GOODRETURNS_URL, headers=HEADERS, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    text = clean_text(soup.get_text(" ", strip=True))

    # Page wording currently contains:
    # "₹15,824 per gram for 24 karat ... ₹14,505 per gram for 22 karat ..."
    m24 = re.search(
        r"today'?s gold price in bhubaneswar stands at\s*₹?\s*([\d,]+)\s*per gram for 24",
        text,
        flags=re.I,
    )
    m22 = re.search(
        r"₹?\s*([\d,]+)\s*per gram for 22 karat",
        text,
        flags=re.I,
    )

    if not (m24 and m22):
        # Fallback: use the table values around "Today Gold Price Per Gram".
        m24 = re.search(r"1\s+₹([\d,]+)\s+₹([\d,]+)", text)
        if m24:
            return {"24K": m24.group(1), "22K": m24.group(2)}

    if not (m24 and m22):
        raise ValueError("Could not locate 24K/22K values on GoodReturns.")

    return {
        "24K": m24.group(1),
        "22K": m22.group(1),
    }


@st.cache_data(ttl=900, show_spinner=False)
def get_population():
    response = requests.get(WORLDMETERS_URL, headers=HEADERS, timeout=20)
    response.raise_for_status()
    text = clean_text(BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True))

    # Worldometer's current page contains a sentence such as:
    # "The current population of India is 1,477,527,450 as of ..."
    current = re.search(
        r"The current population of India is\s*([\d,]+)",
        text,
        flags=re.I,
    )
    midyear = re.search(
        r"India 2026 population is estimated at\s*([\d,]+)",
        text,
        flags=re.I,
    )

    return {
        "current": current.group(1) if current else "Unavailable",
        "midyear_2026": midyear.group(1) if midyear else "Unavailable",
    }


def render_news_card(item, accent):
    st.markdown(
        f"""
        <div class="news-card" style="border-left: 5px solid {accent};">
            <div class="headline">{html.escape(item["title"])}</div>
            <div class="summary">{html.escape(item["summary"])}</div>
            <div class="meta">{html.escape(item["publisher"])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------- CSS -----------------------------
st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at 5% 0%, rgba(79,70,229,.10), transparent 25%),
            radial-gradient(circle at 95% 5%, rgba(14,165,233,.10), transparent 25%),
            #f7f8fc;
    }
    .hero {
        padding: 28px 30px;
        border-radius: 22px;
        background: linear-gradient(120deg, #111827, #312e81 55%, #0f766e);
        color: white;
        box-shadow: 0 12px 30px rgba(15,23,42,.15);
        margin-bottom: 22px;
    }
    .hero h1 {
        margin: 0;
        font-size: 2.35rem;
        letter-spacing: -.8px;
    }
    .hero p {
        margin: 7px 0 0;
        color: #e5e7eb;
        font-size: 1rem;
    }
    .sponsor {
        display: inline-block;
        margin-top: 14px;
        padding: 7px 13px;
        border-radius: 999px;
        background: rgba(255,255,255,.14);
        font-size: .88rem;
        font-weight: 700;
    }
    .metric {
        background: white;
        border-radius: 18px;
        padding: 18px 20px;
        box-shadow: 0 7px 22px rgba(15,23,42,.08);
        border: 1px solid #e5e7eb;
        min-height: 115px;
    }
    .metric-label {
        color: #64748b;
        font-size: .86rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .7px;
    }
    .metric-value {
        margin-top: 6px;
        font-size: 1.75rem;
        font-weight: 800;
        color: #111827;
    }
    .metric-sub {
        margin-top: 4px;
        color: #64748b;
        font-size: .78rem;
    }
    .section-title {
        margin: 28px 0 12px;
        font-size: 1.45rem;
        font-weight: 800;
        color: #111827;
    }
    .news-card {
        background: white;
        border-radius: 14px;
        padding: 15px 17px;
        margin: 9px 0;
        box-shadow: 0 5px 18px rgba(15,23,42,.06);
        border-top: 1px solid #eef2f7;
        border-right: 1px solid #eef2f7;
        border-bottom: 1px solid #eef2f7;
    }
    .headline {
        font-size: 1.02rem;
        line-height: 1.35;
        font-weight: 800;
        color: #172033;
    }
    .summary {
        color: #475569;
        line-height: 1.48;
        margin-top: 7px;
        font-size: .91rem;
    }
    .meta {
        color: #94a3b8;
        font-size: .75rem;
        margin-top: 9px;
        font-weight: 600;
    }
    .footer {
        text-align: center;
        color: #94a3b8;
        padding: 28px 0 10px;
        font-size: .82rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------- Header -----------------------------
now = datetime.now().strftime("%d %B %Y, %I:%M %p")

st.markdown(
    f"""
    <div class="hero">
        <h1>📰 Swarup Daily News & Market Dashboard</h1>
        <p>Fresh headlines, IT industry updates, India & Odisha news, TCS coverage, gold rates and India population.</p>
        <span class="sponsor">Sponsored by Swarup</span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.title("⚙️ Dashboard")
st.sidebar.caption("Refresh the page whenever you want the latest feed.")
if st.sidebar.button("🔄 Refresh Now", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("### Sections")
st.sidebar.markdown(
    "- 🌍 International — 10\n"
    "- 💻 IT Industry — 10\n"
    "- 🇮🇳 India — 10\n"
    "- 🌊 Odisha — 10\n"
    "- 🏢 TCS India — 10\n"
    "- 🪙 Bhubaneswar Gold — 24K & 22K\n"
    "- 👥 India Population"
)

# ----------------------------- Live metrics -----------------------------
with st.spinner("Refreshing live market and population data…"):
    try:
        gold = get_gold_rates()
    except Exception:
        gold = {"24K": "Unavailable", "22K": "Unavailable"}

    try:
        population = get_population()
    except Exception:
        population = {"current": "Unavailable", "midyear_2026": "Unavailable"}

m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown(
        f'<div class="metric"><div class="metric-label">24K Gold</div>'
        f'<div class="metric-value">₹{gold["24K"]}</div>'
        f'<div class="metric-sub">per gram · Bhubaneswar</div></div>',
        unsafe_allow_html=True,
    )

with m2:
    st.markdown(
        f'<div class="metric"><div class="metric-label">22K Gold</div>'
        f'<div class="metric-value">₹{gold["22K"]}</div>'
        f'<div class="metric-sub">per gram · Bhubaneswar</div></div>',
        unsafe_allow_html=True,
    )

with m3:
    st.markdown(
        f'<div class="metric"><div class="metric-label">India Population</div>'
        f'<div class="metric-value">{population["current"]}</div>'
        f'<div class="metric-sub">current figure from Worldometer</div></div>',
        unsafe_allow_html=True,
    )

with m4:
    st.markdown(
        f'<div class="metric"><div class="metric-label">Updated</div>'
        f'<div class="metric-value">{datetime.now().strftime("%H:%M")}</div>'
        f'<div class="metric-sub">{datetime.now().strftime("%d %b %Y")}</div></div>',
        unsafe_allow_html=True,
    )

st.caption(
    f"Dashboard refresh time: {now}. Gold rates are indicative and may exclude GST, TCS and other levies."
)

# ----------------------------- News -----------------------------
with st.spinner("Collecting the latest headlines…"):
    news = get_all_news()

# Render the four main sections as two-column grids.
main_sections = [
    "🌍 International News",
    "💻 IT Industry News",
    "🇮🇳 India News",
    "🌊 Odisha News",
]

for left_name, right_name in zip(main_sections[::2], main_sections[1::2]):
    left, right = st.columns(2)
    with left:
        st.markdown(f'<div class="section-title">{left_name}</div>', unsafe_allow_html=True)
        for item in news.get(left_name, [])[:10]:
            render_news_card(item, CATEGORY_COLORS[left_name])
    with right:
        st.markdown(f'<div class="section-title">{right_name}</div>', unsafe_allow_html=True)
        for item in news.get(right_name, [])[:10]:
            render_news_card(item, CATEGORY_COLORS[right_name])

# TCS gets its own full-width area because the user requested an explanation.
st.markdown('<div class="section-title">🏢 TCS News in India — Headlines & What It Means</div>',
            unsafe_allow_html=True)
st.info(
    "The TCS section searches current coverage specifically for Tata Consultancy Services in India. "
    "Each item includes a headline and a short plain-language explanation based on the feed summary."
)
for item in news.get("🏢 TCS News in India", [])[:10]:
    render_news_card(item, CATEGORY_COLORS["🏢 TCS News in India"])

st.markdown(
    """
    <div class="footer">
        📰 Swarup Daily News & Market Dashboard · Sponsored by Swarup<br>
        News summaries are generated from current online news feeds. Verify important information independently.
    </div>
    """,
    unsafe_allow_html=True,
)
