import streamlit as st
import feedparser
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote
import html

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Swarup News Dashboard",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>

    .stApp {
        background:
            linear-gradient(
                135deg,
                #f5f7ff 0%,
                #eef3ff 45%,
                #f8fbff 100%
            );
    }

    .main-title {
        text-align: center;
        font-size: 42px;
        font-weight: 800;
        margin-bottom: 0;
        background: linear-gradient(
            90deg,
            #1d4ed8,
            #7c3aed,
            #db2777
        );
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .subtitle {
        text-align: center;
        color: #64748b;
        font-size: 17px;
        margin-bottom: 20px;
    }

    .sponsor {
        text-align: center;
        font-size: 15px;
        font-weight: 600;
        color: #475569;
        margin-bottom: 20px;
    }

    .section-header {
        padding: 12px 18px;
        border-radius: 14px;
        color: white;
        font-size: 24px;
        font-weight: 750;
        margin-top: 22px;
        margin-bottom: 15px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.08);
    }

    .international {
        background: linear-gradient(90deg, #2563eb, #4f46e5);
    }

    .technology {
        background: linear-gradient(90deg, #7c3aed, #9333ea);
    }

    .india {
        background: linear-gradient(90deg, #ea580c, #f97316);
    }

    .odisha {
        background: linear-gradient(90deg, #059669, #10b981);
    }

    .tcs {
        background: linear-gradient(90deg, #0f766e, #0891b2);
    }

    .news-card {
        background: rgba(255,255,255,0.92);
        padding: 16px 18px;
        border-radius: 14px;
        margin-bottom: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 3px 12px rgba(15,23,42,0.06);
    }

    .news-number {
        color: #2563eb;
        font-weight: 800;
        font-size: 17px;
    }

    .news-title {
        font-size: 17px;
        font-weight: 700;
        color: #172033;
        line-height: 1.35;
    }

    .news-description {
        color: #64748b;
        font-size: 14px;
        line-height: 1.55;
        margin-top: 7px;
    }

    .source {
        color: #7c3aed;
        font-size: 12px;
        font-weight: 600;
        margin-top: 8px;
    }

    .metric-card {
        background: white;
        padding: 22px;
        border-radius: 18px;
        text-align: center;
        border: 1px solid #e2e8f0;
        box-shadow: 0 5px 20px rgba(15,23,42,0.07);
    }

    .metric-label {
        color: #64748b;
        font-size: 14px;
        font-weight: 600;
    }

    .metric-value {
        font-size: 30px;
        font-weight: 800;
        color: #111827;
        margin-top: 5px;
    }

    .gold-24 {
        border-top: 5px solid #eab308;
    }

    .gold-22 {
        border-top: 5px solid #f59e0b;
    }

    .population {
        border-top: 5px solid #2563eb;
    }

    .footer {
        text-align: center;
        margin-top: 35px;
        padding: 20px;
        color: #64748b;
        font-size: 14px;
        border-top: 1px solid #e2e8f0;
    }

    .eco {
        font-size: 18px;
        font-weight: 700;
        color: #15803d;
        margin-top: 8px;
    }

</style>
""", unsafe_allow_html=True)


# ============================================================
# CONSTANTS
# ============================================================

GOLD_URL = "https://www.goodreturns.in/gold-rates/bhubaneswar.html"

POPULATION_URL = (
    "https://www.worldometers.info/world-population/"
    "india-population/"
)

USER_AGENT = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/151 Safari/537.36"
    )
}


# ============================================================
# RSS NEWS FUNCTION
# ============================================================

def get_google_news_rss(query, limit=10):
    """
    Get Google News RSS results for a topic.
    """

    url = (
        "https://news.google.com/rss/search?"
        f"q={quote(query)}"
        "&hl=en-IN"
        "&gl=IN"
        "&ceid=IN:en"
    )

    try:
        response = requests.get(
            url,
            headers=USER_AGENT,
            timeout=15
        )

        feed = feedparser.parse(response.content)

        news = []

        for entry in feed.entries[:limit]:

            title = entry.get("title", "").strip()

            # Remove HTML from summary
            summary = entry.get(
                "summary",
                entry.get("description", "")
            )

            soup = BeautifulSoup(summary, "html.parser")
            description = soup.get_text(" ", strip=True)

            source = ""

            if hasattr(entry, "source"):
                source = entry.source.get("title", "")

            news.append({
                "title": title,
                "description": description,
                "link": entry.get("link", "#"),
                "source": source,
                "published": entry.get("published", "")
            })

        return news

    except Exception as e:
        return [{
            "title": "Unable to load news",
            "description": str(e),
            "link": "#",
            "source": "System",
            "published": ""
        }]


# ============================================================
# GOLD RATE
# ============================================================

@st.cache_data(ttl=1800)
def get_gold_rates():

    try:

        response = requests.get(
            GOLD_URL,
            headers=USER_AGENT,
            timeout=15
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        text = soup.get_text(
            " ",
            strip=True
        )

        # Try to find the 24K and 22K values
        pattern_24 = r"24K\s*Gold\s*/g\s*₹?\s*([\d,]+)"
        pattern_22 = r"22K\s*Gold\s*/g\s*₹?\s*([\d,]+)"

        match_24 = re.search(
            pattern_24,
            text,
            re.IGNORECASE
        )

        match_22 = re.search(
            pattern_22,
            text,
            re.IGNORECASE
        )

        rate24 = (
            match_24.group(1)
            if match_24
            else "N/A"
        )

        rate22 = (
            match_22.group(1)
            if match_22
            else "N/A"
        )

        return {
            "24K": rate24,
            "22K": rate22
        }

    except Exception:
        return {
            "24K": "N/A",
            "22K": "N/A"
        }


# ============================================================
# INDIA POPULATION
# ============================================================

@st.cache_data(ttl=3600)
def get_population():

    try:

        response = requests.get(
            POPULATION_URL,
            headers=USER_AGENT,
            timeout=15
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        text = soup.get_text(
            " ",
            strip=True
        )

        # Current population
        current_pattern = (
            r"The current population of India is "
            r"([\d,]+)"
        )

        current_match = re.search(
            current_pattern,
            text,
            re.IGNORECASE
        )

        current_population = (
            current_match.group(1)
            if current_match
            else "N/A"
        )

        # 2026 mid-year population
        year_pattern = (
            r"India 2026 population is estimated at "
            r"([\d,]+)"
        )

        year_match = re.search(
            year_pattern,
            text,
            re.IGNORECASE
        )

        population_2026 = (
            year_match.group(1)
            if year_match
            else "N/A"
        )

        return {
            "current": current_population,
            "2026": population_2026
        }

    except Exception:
        return {
            "current": "N/A",
            "2026": "N/A"
        }


# ============================================================
# NEWS CARD
# ============================================================

def display_news(news):

    for index, item in enumerate(news, start=1):

        title = html.escape(
            item.get("title", "")
        )

        description = html.escape(
            item.get("description", "")
        )

        source = html.escape(
            item.get("source", "News source")
        )

        link = item.get("link", "#")

        st.markdown(
            f"""
            <div class="news-card">

                <span class="news-number">
                    {index}.
                </span>

                <span class="news-title">
                    {title}
                </span>

                <div class="news-description">
                    {description}
                </div>

                <div class="source">
                    📰 {source}
                    &nbsp; | &nbsp;
                    <a href="{link}" target="_blank">
                        Read Full Story →
                    </a>
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">📰 Swarup Daily News Dashboard</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'News • Technology • India • Odisha • TCS • Gold • Population'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="sponsor">✨ Sponsored by Swarup ✨</div>',
    unsafe_allow_html=True
)


# ============================================================
# REFRESH
# ============================================================

col1, col2, col3 = st.columns([1, 2, 1])

with col2:

    if st.button(
        "🔄 Refresh Latest News",
        use_container_width=True
    ):

        st.cache_data.clear()
        st.rerun()


updated_time = datetime.now().strftime(
    "%d %B %Y | %I:%M %p"
)

st.caption(
    f"Last dashboard update: {updated_time}"
)


# ============================================================
# GOLD + POPULATION
# ============================================================

gold = get_gold_rates()
population = get_population()

st.markdown(
    '<div class="section-header india">'
    '📊 Today’s Important Numbers'
    '</div>',
    unsafe_allow_html=True
)

c1, c2, c3 = st.columns(3)

with c1:

    st.markdown(
        f"""
        <div class="metric-card gold-24">
            <div class="metric-label">
                🥇 Gold 24K / gram
            </div>
            <div class="metric-value">
                ₹{gold["24K"]}
            </div>
            <small>
                Source: Goodreturns
            </small>
        </div>
        """,
        unsafe_allow_html=True
    )


with c2:

    st.markdown(
        f"""
        <div class="metric-card gold-22">
            <div class="metric-label">
                🥇 Gold 22K / gram
            </div>
            <div class="metric-value">
                ₹{gold["22K"]}
            </div>
            <small>
                Source: Goodreturns
            </small>
        </div>
        """,
        unsafe_allow_html=True
    )


with c3:

    st.markdown(
        f"""
        <div class="metric-card population">
            <div class="metric-label">
                🇮🇳 India Population
            </div>
            <div class="metric-value">
                {population["current"]}
            </div>
            <small>
                Worldometer live figure
            </small>
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# INTERNATIONAL NEWS
# ============================================================

st.markdown(
    '<div class="section-header international">'
    '🌍 Top 10 International News'
    '</div>',
    unsafe_allow_html=True
)

international_news = get_google_news_rss(
    "international world news when:1d",
    10
)

display_news(international_news)


# ============================================================
# IT NEWS
# ============================================================

st.markdown(
    '<div class="section-header technology">'
    '💻 Top 10 IT Industry News'
    '</div>',
    unsafe_allow_html=True
)

it_news = get_google_news_rss(
    "IT technology AI software cloud cybersecurity "
    "industry when:7d",
    10
)

display_news(it_news)


# ============================================================
# INDIA NEWS
# ============================================================

st.markdown(
    '<div class="section-header india">'
    '🇮🇳 Top 10 India News'
    '</div>',
    unsafe_allow_html=True
)

india_news = get_google_news_rss(
    "India national news when:1d",
    10
)

display_news(india_news)


# ============================================================
# ODISHA NEWS
# ============================================================

st.markdown(
    '<div class="section-header odisha">'
    '🌴 Top 10 Odisha News'
    '</div>',
    unsafe_allow_html=True
)

odisha_news = get_google_news_rss(
    "Odisha Bhubaneswar Cuttack Odisha news when:1d",
    10
)

display_news(odisha_news)


# ============================================================
# TCS NEWS
# ============================================================

st.markdown(
    '<div class="section-header tcs">'
    '🏢 TCS News in India'
    '</div>',
    unsafe_allow_html=True
)

tcs_news = get_google_news_rss(
    '"Tata Consultancy Services" TCS India when:7d',
    10
)

display_news(tcs_news)


# ============================================================
# SOURCES
# ============================================================

st.markdown(
    '<div class="section-header technology">'
    '🔗 Official Data Sources'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    f"""
    - 🥇 [Goodreturns – Bhubaneswar Gold Rate]({GOLD_URL})
    - 🇮🇳 [Worldometer – India Population]({POPULATION_URL})
    - 📰 News headlines are aggregated through Google News RSS.
    """
)


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="footer">

        <strong>© Swarup Daily News Dashboard</strong><br>

        Curated automatically from online news and data sources.

        <div class="eco">
            🌳 Save paper, save trees, save the Earth 🌍
        </div>

        <br>

        <small>
            News content belongs to the respective publishers.
            This dashboard provides headlines and links for informational purposes.
        </small>

    </div>
    """,
    unsafe_allow_html=True
)
