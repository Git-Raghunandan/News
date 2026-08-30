import re
from datetime import datetime
from urllib.parse import quote, urljoin

import feedparser
import requests
import streamlit as st
from bs4 import BeautifulSoup

# -----------------------------
# App configuration
# -----------------------------
st.set_page_config(
    page_title="Swarup Daily News Dashboard",
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

OTV_URL = "https://odishatv.in/"
GOLD_URL = "https://www.goodreturns.in/gold-rates/bhubaneswar.html"
TCS_URL = "https://www.tcs.com/who-we-are/newsroom"
POPULATION_URL = "https://www.worldometers.info/world-population/india-population/"

# Google News RSS is used for the three categories where the user did not
# specify a particular publisher. It provides current headlines with links
# to the originating story.
NEWS_QUERIES = {
    "International News": "world international news",
    "IT Industry News": "IT industry technology artificial intelligence cloud cybersecurity software",
    "India News": "India national news",
}

# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
    <style>
    .main {
        background: linear-gradient(135deg, #f7fbff 0%, #eef4ff 45%, #fff8ef 100%);
    }
    .hero {
        padding: 24px 28px;
        border-radius: 20px;
        background: linear-gradient(120deg, #172554, #2563eb, #7c3aed);
        color: white;
        margin-bottom: 18px;
        box-shadow: 0 10px 30px rgba(37,99,235,.18);
    }
    .hero h1 { margin: 0; font-size: 2.1rem; }
    .hero p { margin: 8px 0 0; opacity: .92; }
    .sponsor {
        font-size: .95rem;
        font-weight: 700;
        letter-spacing: .4px;
        margin-top: 12px;
    }
    .eco {
        padding: 12px 16px;
        border-radius: 12px;
        background: #ecfdf5;
        color: #065f46;
        border: 1px solid #a7f3d0;
        font-weight: 700;
        text-align: center;
        margin: 8px 0 18px;
    }
    .metric-card {
        padding: 18px;
        border-radius: 16px;
        background: white;
        border: 1px solid #e5e7eb;
        box-shadow: 0 6px 18px rgba(15,23,42,.06);
    }
    .news-card {
        padding: 15px 16px;
        border-radius: 14px;
        background: white;
        border: 1px solid #e5e7eb;
        margin: 8px 0;
        box-shadow: 0 3px 12px rgba(15,23,42,.04);
    }
    .news-card a {
        text-decoration: none;
        font-weight: 700;
        color: #1d4ed8;
        font-size: 1.02rem;
    }
    .source {
        color: #64748b;
        font-size: .82rem;
        margin-top: 6px;
    }
    footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Generic helpers
# -----------------------------
def get_html(url: str, timeout: int = 20) -> str:
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def unique_items(items, limit=10):
    out, seen = [], set()
    for item in items:
        title = clean_text(item.get("title", ""))
        link = item.get("link", "")
        key = (title.lower(), link)
        if not title or not link or key in seen:
            continue
        seen.add(key)
        item["title"] = title
        out.append(item)
        if len(out) >= limit:
            break
    return out


def source_name_from_url(url: str) -> str:
    try:
        host = url.split("/")[2].lower()
        return host.replace("www.", "")
    except Exception:
        return "Source"


# -----------------------------
# News feeds
# -----------------------------
@st.cache_data(ttl=600, show_spinner=False)
def fetch_google_news(query: str, limit: int = 10):
    rss_url = (
        "https://news.google.com/rss/search?q="
        + quote(query)
        + "&hl=en-IN&gl=IN&ceid=IN:en"
    )
    feed = feedparser.parse(rss_url)
    items = []
    for e in feed.entries[:25]:
        items.append({
            "title": e.get("title", ""),
            "link": e.get("link", ""),
            "published": e.get("published", ""),
            "source": (
                e.get("source", {}).get("title", "")
                if isinstance(e.get("source"), dict)
                else ""
            ) or source_name_from_url(e.get("link", "")),
        })
    return unique_items(items, limit)


# -----------------------------
# Odisha TV
# -----------------------------
@st.cache_data(ttl=600, show_spinner=False)
def fetch_otv_news(limit: int = 10):
    html = get_html(OTV_URL)
    soup = BeautifulSoup(html, "html.parser")
    items = []

    for a in soup.find_all("a", href=True):
        title = clean_text(a.get_text(" ", strip=True))
        href = a["href"]
        link = urljoin(OTV_URL, href)

        if (
            len(title) >= 20
            and "odishatv.in" in link
            and link.rstrip("/") != OTV_URL.rstrip("/")
            and not any(x in link.lower() for x in [
                "/videos", "/photos", "/search", "/tag/", "/author/",
                "/category/", "/live-tv", "/weather"
            ])
        ):
            items.append({
                "title": title,
                "link": link,
                "published": "",
                "source": "OdishaTV",
            })

    # Prefer URLs that look like article pages.
    items.sort(key=lambda x: ("/odisha/" not in x["link"], -len(x["title"])))
    return unique_items(items, limit)


# -----------------------------
# TCS Newsroom
# -----------------------------
@st.cache_data(ttl=600, show_spinner=False)
def fetch_tcs_news(limit: int = 10):
    html = get_html(TCS_URL)
    soup = BeautifulSoup(html, "html.parser")
    items = []

    for a in soup.find_all("a", href=True):
        title = clean_text(a.get_text(" ", strip=True))
        link = urljoin(TCS_URL, a["href"])

        if (
            len(title) >= 20
            and "tcs.com/who-we-are/newsroom" in link
            and link.rstrip("/") != TCS_URL.rstrip("/")
            and any(k in link.lower() for k in [
                "/press-release/", "/news/", "/article/"
            ])
        ):
            items.append({
                "title": title,
                "link": link,
                "published": "",
                "source": "TCS",
            })

    return unique_items(items, limit)


# -----------------------------
# Gold rate
# -----------------------------
@st.cache_data(ttl=600, show_spinner=False)
def fetch_gold_rates():
    html = get_html(GOLD_URL)
    soup = BeautifulSoup(html, "html.parser")
    text = clean_text(soup.get_text(" ", strip=True))

    def find_rate(carat):
        patterns = [
            rf"{carat}\s*(?:K|Karats?|Karat)?\D{{0,80}}(?:₹|Rs\.?|INR)?\s*([\d,]+)",
            rf"(?:₹|Rs\.?|INR)\s*([\d,]+)\D{{0,30}}{carat}\s*(?:K|Karats?|Karat)?",
        ]
        for p in patterns:
            m = re.search(p, text, re.I)
            if m:
                return int(m.group(1).replace(",", ""))
        return None

    k24 = find_rate(24)
    k22 = find_rate(22)

    # Fallback: look around the explicit page heading.
    if not k24 or not k22:
        m = re.search(
            r"today.*?₹\s*([\d,]+).*?for\s*22K.*?₹\s*([\d,]+).*?for\s*24K",
            text, re.I
        )
        if m:
            k22 = k22 or int(m.group(1).replace(",", ""))
            k24 = k24 or int(m.group(2).replace(",", ""))

    return {"24K": k24, "22K": k22, "url": GOLD_URL}


# -----------------------------
# India population
# -----------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_population():
    html = get_html(POPULATION_URL)
    soup = BeautifulSoup(html, "html.parser")
    text = clean_text(soup.get_text(" ", strip=True))

    # Worldometer's current page normally exposes "India Population" followed
    # by the live value. Try several patterns to survive layout changes.
    patterns = [
        r"India Population\s*([\d,]+)",
        r"current population.*?India.*?([\d,]{8,})",
        r"India\s+Population\s+([\d,]{8,})",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return {"population": m.group(1), "url": POPULATION_URL}

    return {"population": None, "url": POPULATION_URL}


# -----------------------------
# UI
# -----------------------------
def render_news(items, empty_message="No stories found."):
    if not items:
        st.warning(empty_message)
        return

    for i, item in enumerate(items, start=1):
        st.markdown(
            f"""
            <div class="news-card">
                <div style="color:#64748b;font-size:.78rem;font-weight:700;">
                    #{i} · {item.get("source","")}
                </div>
                <a href="{item["link"]}" target="_blank">{item["title"]}</a>
                <div class="source">{item.get("published","")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


st.markdown(
    """
    <div class="hero">
        <h1>📰 Swarup Daily News Dashboard</h1>
        <p>International • IT Industry • India • Odisha • TCS • Gold • Population</p>
        <div class="sponsor">Sponsored by Swarup</div>
    </div>
    <div class="eco">🌳 Save paper, save trees, save the Earth</div>
    """,
    unsafe_allow_html=True,
)

now = datetime.now().strftime("%d %b %Y, %I:%M %p")
st.caption(f"Dashboard generated: {now}")

with st.sidebar:
    st.header("⚙️ Controls")
    if st.button("🔄 Refresh all feeds", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown("### Data sources")
    st.markdown(
        f"- [OdishaTV]({OTV_URL})\n"
        f"- [Goodreturns – Bhubaneswar Gold]({GOLD_URL})\n"
        f"- [TCS Newsroom]({TCS_URL})\n"
        f"- [Worldometer – India Population]({POPULATION_URL})"
    )
    st.info(
        "International, IT and India headlines are collected through "
        "Google News RSS and link back to the original publisher."
    )

# Snapshot metrics
with st.spinner("Updating dashboard..."):
    gold = fetch_gold_rates()
    population = fetch_population()
    otv = fetch_otv_news()
    tcs = fetch_tcs_news()

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("🌍 International", "10")
with m2:
    st.metric("💻 IT Industry", "10")
with m3:
    st.metric("🇮🇳 India", "10")
with m4:
    st.metric("🟠 Odisha", "10")

st.markdown("### 💰 Today's Gold & 🇮🇳 Population")
c1, c2, c3 = st.columns(3)
with c1:
    val = f"₹{gold['24K']:,}" if gold["24K"] else "Unavailable"
    st.metric("24K Gold / gram", val)
    st.caption("Source: Goodreturns, Bhubaneswar")
with c2:
    val = f"₹{gold['22K']:,}" if gold["22K"] else "Unavailable"
    st.metric("22K Gold / gram", val)
    st.caption("Source: Goodreturns, Bhubaneswar")
with c3:
    val = population["population"] or "Unavailable"
    st.metric("India Current Population", val)
    st.caption("Source: Worldometer")

st.markdown("---")

tabs = st.tabs([
    "🌍 International",
    "💻 IT Industry",
    "🇮🇳 India",
    "🟠 Odisha",
    "🏢 TCS News",
])

with tabs[0]:
    render_news(fetch_google_news(NEWS_QUERIES["International News"]))

with tabs[1]:
    render_news(fetch_google_news(NEWS_QUERIES["IT Industry News"]))

with tabs[2]:
    render_news(fetch_google_news(NEWS_QUERIES["India News"]))

with tabs[3]:
    render_news(otv)

with tabs[4]:
    render_news(tcs)

st.markdown("---")
st.markdown(
    """
    <div style="text-align:center;padding:18px;color:#475569;">
        <b>Sponsored by Swarup</b><br>
        🌱 <b>Save paper, save trees, save the Earth</b><br>
        <small>News belongs to the respective publishers. Use the source links to read the full stories.</small>
    </div>
    """,
    unsafe_allow_html=True,
)
