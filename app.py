import streamlit as st
import requests
import feedparser
import re
from bs4 import BeautifulSoup
from urllib.parse import quote
from datetime import datetime
from email.utils import parsedate_to_datetime


# ============================================================
# STREAMLIT CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Daily News Dashboard",
    page_icon="📰",
    layout="wide"
)


# ============================================================
# CONSTANTS
# ============================================================

GOODRETURNS_URL = "https://www.goodreturns.in/gold-rates/bhubaneswar.html"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0 Safari/537.36"
    )
}


# ============================================================
# PAGE TITLE
# ============================================================

st.title("📰 Daily News Dashboard")

st.caption(
    "International • IT Industry • India • War & Conflicts • TCS India • Gold"
)

st.write(
    f"Last update: {datetime.now().strftime('%d %B %Y, %I:%M %p')}"
)


# ============================================================
# GOOGLE NEWS RSS
# ============================================================

def google_news_rss(query, language="en-IN", country="IN"):
    """
    Get Google News RSS results for a search query.
    """

    encoded_query = quote(query)

    url = (
        f"https://news.google.com/rss/search?"
        f"q={encoded_query}"
        f"&hl={language}"
        f"&gl={country}"
        f"&ceid={country}:{language[:2]}"
    )

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        response.raise_for_status()

        feed = feedparser.parse(response.content)

        news = []

        for entry in feed.entries:

            title = clean_text(entry.get("title", ""))

            summary = clean_text(
                entry.get("summary", "")
            )

            published = entry.get("published", "")

            source = ""

            if hasattr(entry, "source"):
                source = entry.source.get("title", "")

            news.append({
                "title": title,
                "summary": summary,
                "published": published,
                "source": source
            })

        return news

    except Exception as e:

        return []


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):

    if not text:
        return ""

    soup = BeautifulSoup(text, "html.parser")

    text = soup.get_text(" ", strip=True)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# REMOVE DUPLICATE NEWS
# ============================================================

def remove_duplicates(news):

    unique = []

    seen = set()

    for item in news:

        title = item["title"].lower()

        # Remove punctuation
        normalized = re.sub(
            r"[^a-z0-9 ]",
            "",
            title
        )

        normalized = re.sub(
            r"\s+",
            " ",
            normalized
        ).strip()

        if normalized in seen:
            continue

        seen.add(normalized)

        unique.append(item)

    return unique


# ============================================================
# SORT NEWS BY DATE
# ============================================================

def sort_by_date(news):

    def get_date(item):

        try:
            return parsedate_to_datetime(
                item["published"]
            )

        except Exception:

            return datetime.min

    return sorted(
        news,
        key=get_date,
        reverse=True
    )


# ============================================================
# GET TOP NEWS
# ============================================================

def get_top_news(query, count=10):

    news = google_news_rss(query)

    news = remove_duplicates(news)

    news = sort_by_date(news)

    return news[:count]


# ============================================================
# GOLD RATE
# ============================================================

@st.cache_data(ttl=900)
def get_gold_rate():

    try:

        response = requests.get(
            GOODRETURNS_URL,
            headers=HEADERS,
            timeout=20
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        page_text = soup.get_text(
            " ",
            strip=True
        )

        # ----------------------------------------------------
        # 24K
        # ----------------------------------------------------

        match_24k = re.search(
            r"24 karat gold.*?₹\s*([\d,]+)\s*per gram",
            page_text,
            re.IGNORECASE
        )

        # ----------------------------------------------------
        # 22K
        # ----------------------------------------------------

        match_22k = re.search(
            r"22 karat gold.*?₹\s*([\d,]+)\s*per gram",
            page_text,
            re.IGNORECASE
        )

        # Fallback pattern
        if not match_24k:

            match_24k = re.search(
                r"24K\s*Gold\s*/g.*?₹\s*([\d,]+)",
                page_text,
                re.IGNORECASE
            )

        if not match_22k:

            match_22k = re.search(
                r"22K\s*Gold\s*/g.*?₹\s*([\d,]+)",
                page_text,
                re.IGNORECASE
            )

        result = {
            "24K": None,
            "22K": None
        }

        if match_24k:
            result["24K"] = match_24k.group(1)

        if match_22k:
            result["22K"] = match_22k.group(1)

        return result

    except Exception:

        return {
            "24K": None,
            "22K": None
        }


# ============================================================
# TCS NEWS
# ============================================================

def get_tcs_news():

    queries = [

        '"Tata Consultancy Services" India',

        '"TCS" India IT',

        '"TCS" Tata Consultancy Services',

        '"TCS" India technology',

        '"TCS" deal India',

    ]

    all_news = []

    for query in queries:

        news = google_news_rss(query)

        all_news.extend(news)

    all_news = remove_duplicates(all_news)

    all_news = sort_by_date(all_news)

    return all_news[:10]


# ============================================================
# FIVE-LINE TCS EXPLANATION
# ============================================================

def create_tcs_explanation(item):

    title = item["title"]

    summary = item["summary"]

    source = item["source"]

    if not summary:
        summary = (
            "The report discusses a recent development involving "
            "Tata Consultancy Services."
        )

    lines = [

        f"1. {title}.",

        f"2. The report focuses on {summary}.",

        "3. The development is relevant to TCS's business, "
        "technology, clients, employees or market position.",

        "4. It may have implications for TCS's growth, "
        "operations, technology strategy or investors.",

        f"5. Reported by {source if source else 'a news source'}."

    ]

    return lines


# ============================================================
# DISPLAY NEWS
# ============================================================

def display_news(news, show_summary=False):

    if not news:

        st.warning(
            "Unable to retrieve news at the moment."
        )

        return

    for index, item in enumerate(news, start=1):

        st.markdown(
            f"### {index}. {item['title']}"
        )

        if show_summary and item["summary"]:

            st.write(
                item["summary"]
            )

        if item["source"]:

            st.caption(
                f"Source: {item['source']}"
            )

        st.divider()


# ============================================================
# NEWS QUERIES
# ============================================================

INTERNATIONAL_QUERY = (
    "international world news OR global news"
)

IT_QUERY = (
    "technology IT industry AI cloud cybersecurity "
    "Microsoft Google Amazon Nvidia OpenAI"
)

INDIA_QUERY = (
    "India news Narendra Modi government economy "
    "business infrastructure"
)

WAR_QUERY = (
    "war OR military conflict OR armed conflict "
    "OR ceasefire OR airstrike OR battlefield"
)


# ============================================================
# GOLD SECTION
# ============================================================

st.header("🪙 Gold Rate Today — Bhubaneswar")

gold = get_gold_rate()

col1, col2 = st.columns(2)

with col1:

    st.metric(
        "24K Gold / Gram",
        f"₹{gold['24K']}"
        if gold["24K"]
        else "Unavailable"
    )

with col2:

    st.metric(
        "22K Gold / Gram",
        f"₹{gold['22K']}"
        if gold["22K"]
        else "Unavailable"
    )

st.caption(
    "Rates are taken from GoodReturns Bhubaneswar gold-rate page."
)


# ============================================================
# INTERNATIONAL NEWS
# ============================================================

st.header("🌍 Top 10 International News")

international_news = get_top_news(
    INTERNATIONAL_QUERY,
    10
)

display_news(
    international_news,
    show_summary=True
)


# ============================================================
# IT INDUSTRY NEWS
# ============================================================

st.header("💻 Top 10 IT Industry News")

it_news = get_top_news(
    IT_QUERY,
    10
)

display_news(
    it_news,
    show_summary=True
)


# ============================================================
# INDIA NEWS
# ============================================================

st.header("🇮🇳 Top 10 India News")

india_news = get_top_news(
    INDIA_QUERY,
    10
)

display_news(
    india_news,
    show_summary=True
)


# ============================================================
# WAR / CONFLICT NEWS
# ============================================================

st.header("⚔️ Top 10 War & Conflict News Worldwide")

war_news = get_top_news(
    WAR_QUERY,
    10
)

display_news(
    war_news,
    show_summary=True
)


# ============================================================
# TCS NEWS
# ============================================================

st.header("🏢 TCS News — India")

tcs_news = get_tcs_news()

if not tcs_news:

    st.warning(
        "No TCS news could be retrieved."
    )

else:

    for index, item in enumerate(
        tcs_news,
        start=1
    ):

        st.subheader(
            f"{index}. {item['title']}"
        )

        explanation = create_tcs_explanation(
            item
        )

        for line in explanation:

            st.write(line)

        st.divider()


# ============================================================
# FOOTER
# ============================================================

st.caption(
    "News is collected from publicly available online RSS/news sources. "
    "News rankings are based on the returned feed results and may change "
    "throughout the day."
)
