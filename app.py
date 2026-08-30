import streamlit as st
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote
import re
import html


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Daily News Dashboard",
    page_icon="📰",
    layout="wide"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/151.0 Safari/537.36"
    )
}

GOLD_URL = "https://www.goodreturns.in/gold-rates/bhubaneswar.html"


# ============================================================
# PAGE CSS
# ============================================================

st.markdown("""
<style>

.main-title {
    font-size: 38px;
    font-weight: 700;
    text-align: center;
    margin-bottom: 5px;
}

.subtitle {
    text-align: center;
    color: gray;
    margin-bottom: 25px;
}

.news-card {
    padding: 15px;
    margin-bottom: 12px;
    border-radius: 10px;
    border: 1px solid #dddddd;
    background-color: #fafafa;
}

.news-title {
    font-size: 19px;
    font-weight: 650;
    margin-bottom: 8px;
}

.news-summary {
    font-size: 15px;
    line-height: 1.55;
}

.news-source {
    font-size: 12px;
    color: gray;
    margin-top: 8px;
}

.gold-card {
    padding: 25px;
    border-radius: 12px;
    border: 1px solid #dddddd;
    text-align: center;
}

.gold-price {
    font-size: 30px;
    font-weight: 700;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# NEWS CATEGORIES
# ============================================================

NEWS_CATEGORIES = {

    "🌎 Top International News": [
        "international world news",
        "global politics",
        "world economy",
        "United States world news",
        "Europe world news",
    ],

    "💻 Top IT Industry News": [
        "technology IT industry",
        "artificial intelligence technology",
        "cloud computing technology",
        "cybersecurity technology",
        "Microsoft Google Amazon technology",
    ],

    "🇮🇳 Top India News": [
        "India latest news",
        "India politics",
        "India economy",
        "India business",
        "India government",
    ],

    "⚔️ Top War / Global Conflict News": [
        "war conflict latest",
        "Ukraine Russia war",
        "Iran conflict war",
        "Israel conflict war",
        "Middle East conflict",
    ],

    "🏆 TCS News — India": [
        "TCS Tata Consultancy Services India",
        "TCS India business",
        "TCS India technology",
        "TCS jobs India",
        "TCS contract India",
    ],
}


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = html.unescape(text)

    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text(" ")

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# CREATE GOOGLE NEWS RSS URL
# ============================================================

def google_news_rss(query):

    encoded_query = quote(query)

    return (
        "https://news.google.com/rss/search?"
        f"q={encoded_query}"
        "&hl=en-IN"
        "&gl=IN"
        "&ceid=IN:en"
    )


# ============================================================
# FETCH NEWS
# ============================================================

def fetch_news(query, limit=10):

    url = google_news_rss(query)

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        response.raise_for_status()

        feed = feedparser.parse(response.content)

        articles = []

        for entry in feed.entries:

            title = clean_text(
                entry.get("title", "")
            )

            description = clean_text(
                entry.get("description", "")
            )

            source = ""

            if hasattr(entry, "source"):
                source = clean_text(
                    entry.source.get("title", "")
                )

            published = entry.get(
                "published",
                ""
            )

            if not title:
                continue

            articles.append({
                "title": title,
                "summary": description,
                "source": source,
                "published": published
            })

        return articles[:limit]

    except Exception as e:

        st.warning(
            f"Unable to fetch news for: {query}"
        )

        return []


# ============================================================
# FETCH MULTIPLE QUERIES
# ============================================================

def collect_category_news(queries, total=10):

    all_news = []

    for query in queries:

        news = fetch_news(
            query,
            limit=5
        )

        all_news.extend(news)

    # --------------------------------------------------------
    # Remove duplicate headlines
    # --------------------------------------------------------

    unique_news = []

    seen = set()

    for item in all_news:

        normalized_title = re.sub(
            r"[^a-z0-9]",
            "",
            item["title"].lower()
        )

        if normalized_title in seen:
            continue

        seen.add(normalized_title)

        unique_news.append(item)

        if len(unique_news) >= total:
            break

    return unique_news


# ============================================================
# CREATE SHORT SUMMARY
# ============================================================

def create_summary(text):

    text = clean_text(text)

    if not text:
        return "Details are available in the latest report."

    # Google News descriptions can contain long text.
    # Convert them into approximately 2-3 sentences.

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text
    )

    sentences = [
        s.strip()
        for s in sentences
        if len(s.strip()) > 20
    ]

    if len(sentences) >= 3:

        summary = " ".join(
            sentences[:3]
        )

    elif len(sentences) >= 1:

        summary = " ".join(
            sentences[:2]
        )

    else:

        summary = text

    if len(summary) > 550:

        summary = summary[:550]

        last_space = summary.rfind(" ")

        if last_space > 0:
            summary = summary[:last_space]

        summary += "..."

    return summary


# ============================================================
# DISPLAY NEWS
# ============================================================

def display_news(news):

    if not news:

        st.warning(
            "No news available at the moment."
        )

        return

    for index, item in enumerate(news, 1):

        title = item["title"]

        summary = create_summary(
            item["summary"]
        )

        source = item["source"]

        st.markdown(
            f"""
            <div class="news-card">

                <div class="news-title">
                    {index}. {html.escape(title)}
                </div>

                <div class="news-summary">
                    {html.escape(summary)}
                </div>

                <div class="news-source">
                    Source: {html.escape(source)}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


# ============================================================
# GOLD RATE
# ============================================================

@st.cache_data(ttl=900)
def get_gold_rates():

    try:

        response = requests.get(
            GOLD_URL,
            headers=HEADERS,
            timeout=20
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

        # ----------------------------------------------------
        # Try to locate 24K and 22K values
        # ----------------------------------------------------

        match_24 = re.search(
            r"24K\s*Gold\s*/g\s*₹?\s*([\d,]+)",
            text,
            re.IGNORECASE
        )

        match_22 = re.search(
            r"22K\s*Gold\s*/g\s*₹?\s*([\d,]+)",
            text,
            re.IGNORECASE
        )

        price_24 = (
            match_24.group(1)
            if match_24
            else None
        )

        price_22 = (
            match_22.group(1)
            if match_22
            else None
        )

        # ----------------------------------------------------
        # Alternative table parsing
        # ----------------------------------------------------

        if not price_24 or not price_22:

            tables = soup.find_all("table")

            for table in tables:

                table_text = clean_text(
                    table.get_text(" ")
                )

                if (
                    "24K" in table_text
                    and "22K" in table_text
                ):

                    numbers = re.findall(
                        r"₹?\s*([\d,]+)",
                        table_text
                    )

                    if len(numbers) >= 2:

                        price_24 = (
                            price_24 or numbers[0]
                        )

                        price_22 = (
                            price_22 or numbers[1]
                        )

                        break

        return {
            "24K": price_24,
            "22K": price_22,
            "updated": datetime.now().strftime(
                "%d %B %Y, %I:%M %p"
            )
        }

    except Exception as e:

        return {
            "24K": None,
            "22K": None,
            "updated": "Unable to update"
        }


# ============================================================
# MAIN UI
# ============================================================

st.markdown(
    '<div class="main-title">📰 DAILY NEWS DASHBOARD</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'International • IT • India • Wars • TCS • Gold'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# DATE
# ============================================================

current_time = datetime.now()

st.info(
    "Last dashboard refresh: "
    + current_time.strftime(
        "%d %B %Y, %I:%M %p"
    )
)


# ============================================================
# REFRESH BUTTON
# ============================================================

col1, col2, col3 = st.columns(
    [1, 1, 1]
)

with col2:

    if st.button(
        "🔄 Refresh News",
        use_container_width=True
    ):

        st.cache_data.clear()

        st.rerun()


# ============================================================
# GOLD
# ============================================================

st.header(
    "🥇 Gold Rate — Bhubaneswar"
)

gold = get_gold_rates()

col1, col2 = st.columns(2)

with col1:

    st.markdown(
        f"""
        <div class="gold-card">

        <h3>24K Gold</h3>

        <div class="gold-price">
        ₹{gold["24K"] or "N/A"}
        </div>

        <p>Per Gram</p>

        </div>
        """,
        unsafe_allow_html=True
    )

with col2:

    st.markdown(
        f"""
        <div class="gold-card">

        <h3>22K Gold</h3>

        <div class="gold-price">
        ₹{gold["22K"] or "N/A"}
        </div>

        <p>Per Gram</p>

        </div>
        """,
        unsafe_allow_html=True
    )

st.caption(
    "Gold data is collected from the specified GoodReturns "
    "Bhubaneswar gold-rate page."
)


# ============================================================
# NEWS
# ============================================================

for category, queries in NEWS_CATEGORIES.items():

    st.divider()

    st.header(category)

    with st.spinner(
        f"Collecting {category}..."
    ):

        news = collect_category_news(
            queries,
            total=10
        )

    display_news(news)


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "News dashboard automatically collects current "
    "online news. Headlines and summaries may change "
    "as news sources update."
)
