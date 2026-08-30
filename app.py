import os
import re
from datetime import datetime, timezone, timedelta

import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="Swarup Royal News Desk",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -----------------------------
# Configuration
# -----------------------------
GNEWS_URL = "https://gnews.io/api/v4/search"
GOLD_URL = "https://www.goodreturns.in/gold-rates/bhubaneswar.html"

CATEGORIES = {
    "TOI Top 10": 'site:timesofindia.indiatimes.com',
    "International Top 10": "international world latest news",
    "IT Industry Top 10": "IT industry technology AI cloud cybersecurity software companies",
    "India Top 10": "India latest national news",
    "Odisha Top 10": "Odisha Bhubaneswar Cuttack latest news",
    "TCS India Top 10": '"Tata Consultancy Services" OR TCS India',
}

# -----------------------------
# Royal dashboard styling
# No HTML is used.
# -----------------------------
st.title("👑 SWARUP ROYAL NEWS DESK")
st.caption("Sponsored by Swarup • Live online news intelligence dashboard")

api_key = st.secrets.get("GNEWS_API_KEY", os.getenv("GNEWS_API_KEY", ""))

def clean_text(text):
    if not text:
        return ""
    text = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def fetch_news(query, max_items=10):
    if not api_key:
        return [{
            "title": "GNews API key is not configured",
            "description": "Add GNEWS_API_KEY in Streamlit Secrets or as an environment variable to activate live news feeds.",
            "source": "System"
        }]

    params = {
        "q": query,
        "lang": "en",
        "country": "in",
        "max": max_items,
        "apikey": api_key,
    }

    try:
        response = requests.get(GNEWS_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        articles = []

        for item in data.get("articles", [])[:max_items]:
            title = clean_text(item.get("title"))
            description = clean_text(item.get("description"))
            source = clean_text((item.get("source") or {}).get("name", "News source"))

            if not title:
                continue

            if not description:
                description = "Latest update from the online news source."

            articles.append({
                "title": title,
                "description": description,
                "source": source,
            })

        return articles

    except Exception as exc:
        return [{
            "title": "Unable to load this news section",
            "description": f"Temporary online-source/API problem: {exc}",
            "source": "System"
        }]

def fetch_gold():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/151 Safari/537.36"
        )
    }

    try:
        response = requests.get(GOLD_URL, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = clean_text(soup.get_text(" ", strip=True))

        # GoodReturns page currently presents the rate as:
        # "₹15,824 per gram for 24 karat ... ₹14,505 per gram for 22 karat"
        match = re.search(
            r"₹([\d,]+)\s+per gram for 24 karat.*?₹([\d,]+)\s+per gram for 22 karat",
            text,
            flags=re.I,
        )

        if match:
            return {
                "24K": f"₹{match.group(1)} / gram",
                "22K": f"₹{match.group(2)} / gram",
                "status": "Live rate fetched from GoodReturns",
            }

        # Fallback: parse the visible rate table.
        for row in soup.find_all("tr"):
            cells = [clean_text(c.get_text(" ", strip=True)) for c in row.find_all(["th", "td"])]
            row_text = " | ".join(cells)
            if "24K" in row_text and "22K" in row_text:
                nums = re.findall(r"₹[\d,]+", row_text)
                if len(nums) >= 2:
                    return {
                        "24K": f"{nums[0]} / gram",
                        "22K": f"{nums[1]} / gram",
                        "status": "Live rate fetched from GoodReturns",
                    }

        return {
            "24K": "Unavailable",
            "22K": "Unavailable",
            "status": "GoodReturns page format changed; parser needs updating.",
        }

    except Exception as exc:
        return {
            "24K": "Unavailable",
            "22K": "Unavailable",
            "status": f"Gold feed error: {exc}",
        }

def show_news_section(title, query):
    st.subheader(title)
    articles = fetch_news(query, 10)

    for idx, article in enumerate(articles, 1):
        st.markdown(f"**{idx}. {article['title']}**")
        st.write(article["description"])
        st.caption(f"Source: {article['source']}")
        if idx != len(articles):
            st.divider()

# -----------------------------
# Sidebar controls
# -----------------------------
with st.sidebar:
    st.header("Dashboard Controls")
    if st.button("🔄 Refresh All News", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.write("News mode: Live online fetch")
    st.write("Dashboard: Royal")
    st.write("Sponsor: Swarup")

# -----------------------------
# Header
# -----------------------------
now = datetime.now(timezone.utc).astimezone()
st.info(
    f"Last page refresh: {now.strftime('%d %B %Y, %I:%M %p %Z')}  •  "
    "Open or refresh the Streamlit URL from WhatsApp to get current feeds."
)

# Gold
st.subheader("🪙 Gold Rate Today — Bhubaneswar")
gold = fetch_gold()

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("24K Gold", gold["24K"])
with c2:
    st.metric("22K Gold", gold["22K"])
with c3:
    st.metric("Feed", "GoodReturns")

st.caption(gold["status"])
st.divider()

# News sections
show_news_section("📰 Times of India — Top 10", CATEGORIES["TOI Top 10"])
st.divider()

show_news_section("🌍 International — Top 10", CATEGORIES["International Top 10"])
st.divider()

show_news_section("💻 IT Industry — Top 10", CATEGORIES["IT Industry Top 10"])
st.divider()

show_news_section("🇮🇳 India — Top 10", CATEGORIES["India Top 10"])
st.divider()

show_news_section("🌊 Odisha — Top 10", CATEGORIES["Odisha Top 10"])
st.divider()

show_news_section("🏢 TCS India — Top 10", CATEGORIES["TCS India Top 10"])

st.divider()
st.caption("👑 SWARUP ROYAL NEWS DESK • Sponsored by Swarup")
