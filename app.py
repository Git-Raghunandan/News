import re
import html
import requests
import feedparser
import streamlit as st
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor, as_completed


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Swarup Daily News",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# ROYAL CSS
# ============================================================

st.markdown("""
<style>

.stApp {
    background:
        radial-gradient(circle at top right, #2b2412 0%, #090909 35%),
        linear-gradient(135deg, #050505, #111111);
    color: #f5f5f5;
}

.main-title {
    text-align: center;
    padding: 10px 0 0 0;
}

.main-title h1 {
    font-size: 48px;
    font-weight: 800;
    letter-spacing: 3px;
    margin-bottom: 0;
    color: #d4af37;
    text-shadow: 0 0 20px rgba(212,175,55,0.25);
}

.main-title p {
    color: #c9c9c9;
    font-size: 18px;
    letter-spacing: 2px;
}

.sponsored {
    text-align: center;
    color: #d4af37;
    font-size: 15px;
    font-weight: 600;
    letter-spacing: 2px;
    margin-bottom: 20px;
}

.section-title {
    border-left: 5px solid #d4af37;
    padding-left: 12px;
    margin-top: 28px;
    margin-bottom: 15px;
    color: #d4af37;
    font-size: 25px;
    font-weight: 700;
}

.news-card {
    background: linear-gradient(
        145deg,
        rgba(32,32,32,0.95),
        rgba(14,14,14,0.98)
    );

    border: 1px solid rgba(212,175,55,0.28);
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 12px;

    box-shadow:
        0 5px 18px rgba(0,0,0,0.35),
        inset 0 1px 0 rgba(255,255,255,0.03);
}

.news-number {
    color: #d4af37;
    font-weight: bold;
    font-size: 18px;
}

.news-headline {
    color: #ffffff;
    font-size: 18px;
    font-weight: 700;
    line-height: 1.35;
}

.news-summary {
    color: #c7c7c7;
    font-size: 14px;
    line-height: 1.55;
    margin-top: 7px;
}

.source {
    color: #8f8f8f;
    font-size: 11px;
    margin-top: 8px;
}

.gold-card {
    background:
        linear-gradient(
            145deg,
            rgba(70,52,10,0.95),
            rgba(18,14,5,0.98)
        );

    border: 1px solid #d4af37;
    border-radius: 18px;
    padding: 24px;
    text-align: center;

    box-shadow:
        0 0 25px rgba(212,175,55,0.12);
}

.gold-label {
    color: #cfcfcf;
    font-size: 15px;
    letter-spacing: 1px;
}

.gold-price {
    color: #d4af37;
    font-size: 34px;
    font-weight: 800;
    margin-top: 5px;
}

.gold-unit {
    color: #aaaaaa;
    font-size: 12px;
}

.footer {
    text-align: center;
    color: #777777;
    font-size: 12px;
    margin-top: 40px;
    padding: 20px;
    border-top: 1px solid rgba(212,175,55,0.15);
}

div.stButton > button {
    background: linear-gradient(90deg, #8c6a16, #d4af37);
    color: #111111;
    font-weight: 700;
    border: none;
    border-radius: 10px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# CONSTANTS
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/151 Safari/537.36"
    )
}

MAX_NEWS = 10


# ============================================================
# GOOGLE NEWS RSS
# ============================================================

def google_news_url(query):
    encoded = quote_plus(query)

    return (
        f"https://news.google.com/rss/search?"
        f"q={encoded}&hl=en-IN&gl=IN&ceid=IN:en"
    )


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = html.unescape(text)

    soup = BeautifulSoup(text, "html.parser")

    text = soup.get_text(" ", strip=True)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# FETCH RSS
# ============================================================

@st.cache_data(ttl=300, show_spinner=False)
def fetch_feed(query, limit=10):

    url = google_news_url(query)

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15
        )

        response.raise_for_status()

        feed = feedparser.parse(response.content)

        results = []

        for entry in feed.entries[:limit]:

            title = clean_text(
                getattr(entry, "title", "")
            )

            summary = clean_text(
                getattr(entry, "summary", "")
            )

            source = ""

            if hasattr(entry, "source"):
                source = clean_text(
                    getattr(entry.source, "title", "")
                )

            if not title:
                continue

            results.append({
                "title": title,
                "summary": summary,
                "source": source
            })

        return results

    except Exception as e:

        return [{
            "title": "Unable to fetch news",
            "summary": str(e),
            "source": "News service"
        }]


# ============================================================
# NEWS CATEGORIES
# ============================================================

CATEGORIES = {

    "📰 Times of India — Top 10": (
        'site:timesofindia.indiatimes.com '
        '(India OR World OR Business OR Technology) '
        'when:1d'
    ),

    "🌎 International — Top 10": (
        '(world OR international OR geopolitics OR '
        'USA OR Europe OR China OR Russia OR Middle East) '
        'when:1d'
    ),

    "💻 IT Industry — Top 10": (
        '(Microsoft OR Google OR Amazon OR Apple OR '
        'OpenAI OR AI OR cybersecurity OR cloud OR '
        'software OR technology OR IT industry) '
        'when:1d'
    ),

    "🇮🇳 India — Top 10": (
        'India news when:1d'
    ),

    "🏝️ Odisha — Top 10": (
        'Odisha OR Bhubaneswar OR Cuttack OR Rourkela '
        'OR Puri when:1d'
    ),

    "🏆 TCS India — Top 10": (
        '"Tata Consultancy Services" OR TCS India '
        'when:7d'
    )
}


# ============================================================
# DISPLAY NEWS
# ============================================================

def display_news(title, articles):

    st.markdown(
        f'<div class="section-title">{title}</div>',
        unsafe_allow_html=True
    )

    if not articles:

        st.warning("No news available at the moment.")

        return

    for index, article in enumerate(
        articles[:MAX_NEWS],
        start=1
    ):

        headline = article["title"]

        summary = article["summary"]

        source = article["source"]

        # Remove common Google News source suffixes
        headline = re.sub(
            r"\s*-\s*[^-]+$",
            "",
            headline
        )

        # Keep summary short
        if len(summary) > 360:
            summary = summary[:357] + "..."

        if not summary:
            summary = (
                "This is one of the latest stories currently "
                "being reported across online news sources."
            )

        st.markdown(
            f"""
            <div class="news-card">

                <span class="news-number">
                    {index:02d}
                </span>

                <span class="news-headline">
                    &nbsp; {html.escape(headline)}
                </span>

                <div class="news-summary">
                    {html.escape(summary)}
                </div>

                <div class="source">
                    Source: {html.escape(source)}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


# ============================================================
# GOLD RATE
# ============================================================

GOODRETURNS_URL = (
    "https://www.goodreturns.in/gold-rates/bhubaneswar.html"
)


@st.cache_data(ttl=300, show_spinner=False)
def get_gold_rate():

    try:

        response = requests.get(
            GOODRETURNS_URL,
            headers=HEADERS,
            timeout=15
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        text = soup.get_text(
            " ",
            strip=True
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        # Look around the current gold rate section.
        match_24 = re.search(
            r"24K\s*Gold\s*/g\s*₹\s*([\d,]+)",
            text,
            re.IGNORECASE
        )

        match_22 = re.search(
            r"22K\s*Gold\s*/g\s*₹\s*([\d,]+)",
            text,
            re.IGNORECASE
        )

        # Fallback pattern
        if not match_24:

            match_24 = re.search(
                r"24 karat gold.*?₹([\d,]+)",
                text,
                re.IGNORECASE
            )

        if not match_22:

            match_22 = re.search(
                r"22 karat gold.*?₹([\d,]+)",
                text,
                re.IGNORECASE
            )

        rate_24 = (
            match_24.group(1)
            if match_24
            else "N/A"
        )

        rate_22 = (
            match_22.group(1)
            if match_22
            else "N/A"
        )

        return rate_24, rate_22

    except Exception:

        return "N/A", "N/A"


# ============================================================
# GOLD DISPLAY
# ============================================================

def display_gold():

    st.markdown(
        '<div class="section-title">🪙 Gold Rate Today — Bhubaneswar</div>',
        unsafe_allow_html=True
    )

    rate_24, rate_22 = get_gold_rate()

    col1, col2 = st.columns(2)

    with col1:

        st.markdown(
            f"""
            <div class="gold-card">

                <div class="gold-label">
                    24 CARAT GOLD
                </div>

                <div class="gold-price">
                    ₹{rate_24}
                </div>

                <div class="gold-unit">
                    per gram
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:

        st.markdown(
            f"""
            <div class="gold-card">

                <div class="gold-label">
                    22 CARAT GOLD
                </div>

                <div class="gold-price">
                    ₹{rate_22}
                </div>

                <div class="gold-unit">
                    per gram
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="main-title">

        <h1>👑 SWARUP DAILY NEWS</h1>

        <p>
            INDIA • WORLD • TECHNOLOGY • ODISHA • TCS • GOLD
        </p>

    </div>

    <div class="sponsored">
        ✦ SPONSORED BY SWARUP ✦
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# DATE / UPDATE TIME
# ============================================================

now = datetime.now()

col1, col2, col3 = st.columns([1, 2, 1])

with col2:

    st.markdown(
        f"""
        <div style="
            text-align:center;
            color:#999;
            margin-bottom:15px;
        ">
            Last refreshed:
            {now.strftime("%d %B %Y • %I:%M %p")}
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# REFRESH BUTTON
# ============================================================

col1, col2, col3 = st.columns([1, 2, 1])

with col2:

    if st.button(
        "🔄 REFRESH TODAY'S NEWS",
        use_container_width=True
    ):

        st.cache_data.clear()

        st.rerun()


# ============================================================
# GOLD
# ============================================================

display_gold()


# ============================================================
# FETCH ALL NEWS
# ============================================================

news_data = {}

with st.spinner("Collecting today's news..."):

    with ThreadPoolExecutor(
        max_workers=6
    ) as executor:

        jobs = {
            executor.submit(
                fetch_feed,
                query,
                MAX_NEWS
            ): category

            for category, query
            in CATEGORIES.items()
        }

        for job in as_completed(jobs):

            category = jobs[job]

            try:

                news_data[category] = job.result()

            except Exception:

                news_data[category] = []


# ============================================================
# DISPLAY NEWS
# ============================================================

for category in CATEGORIES:

    display_news(
        category,
        news_data.get(category, [])
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="footer">

        👑 <b>SWARUP DAILY NEWS</b><br><br>

        Sponsored by Swarup<br>

        News is automatically collected from online news sources.
        Headlines and summaries are presented for informational purposes.

        <br><br>

        © 2026 Swarup Daily News

    </div>
    """,
    unsafe_allow_html=True
)
