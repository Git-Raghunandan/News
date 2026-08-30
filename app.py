import streamlit as st
import feedparser
import requests
import pandas as pd
from datetime import datetime

# =====================================
# CONFIG
# =====================================

MAX_NEWS = 10

RSS_FEEDS = {
    "International": [
        "https://feeds.reuters.com/Reuters/worldNews",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"
    ],

    "India": [
        "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
        "https://feeds.feedburner.com/ndtvnews-india-news"
    ],

    "IT": [
        "https://techcrunch.com/feed/",
        "https://www.zdnet.com/news/rss.xml"
    ],

    "War": [
        "https://www.defensenews.com/arc/outboundfeeds/rss/",
        "https://www.reuters.com/world/rss"
    ],

    "TCS": [
        "https://news.google.com/rss/search?q=TCS+India"
    ]
}


# =====================================
# NEWS FETCHER
# =====================================

def fetch_news(feed_urls, limit=10):

    news = []

    for url in feed_urls:

        try:
            feed = feedparser.parse(url)

            for entry in feed.entries:

                news.append({
                    "title": entry.title,
                    "summary": entry.get("summary", ""),
                    "published": entry.get("published", "")
                })

        except Exception:
            pass

    return news[:limit]


# =====================================
# SIMPLE SUMMARIZER
# =====================================

def summarize_news(item):

    text = item["summary"]

    if not text:
        return "Summary not available."

    text = text.replace("<p>", "")
    text = text.replace("</p>", "")

    sentences = text.split(".")

    result = []

    for s in sentences[:5]:
        s = s.strip()
        if s:
            result.append("• " + s)

    return "\n".join(result)


# =====================================
# GOLD RATE
# =====================================

def get_gold_rate():

    try:

        url = "https://api.metals.live/v1/spot"

        data = requests.get(url, timeout=10).json()

        gold_usd = None

        for item in data:
            if "gold" in item:
                gold_usd = item["gold"]
                break

        if gold_usd:

            inr_rate = gold_usd * 83

            return {
                "24K": round(inr_rate, 2),
                "22K": round(inr_rate * 0.916, 2)
            }

    except Exception:
        pass

    return {
        "24K": "Unavailable",
        "22K": "Unavailable"
    }


# =====================================
# UI
# =====================================

st.set_page_config(
    page_title="Daily News Dashboard",
    layout="wide"
)

st.title("📰 Daily News Dashboard")

st.write(
    f"Last Updated : {datetime.now().strftime('%d-%b-%Y %H:%M:%S')}"
)

# =====================================
# GOLD
# =====================================

gold = get_gold_rate()

c1, c2 = st.columns(2)

with c1:
    st.metric("Gold 24K", gold["24K"])

with c2:
    st.metric("Gold 22K", gold["22K"])

st.divider()

# =====================================
# NEWS CATEGORIES
# =====================================

for category, feeds in RSS_FEEDS.items():

    st.header(category)

    articles = fetch_news(feeds, MAX_NEWS)

    for idx, article in enumerate(articles, start=1):

        with st.expander(f"{idx}. {article['title']}"):

            st.write("### 5 Line Summary")

            st.write(
                summarize_news(article)
            )

    st.divider()
