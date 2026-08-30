import streamlit as st
import requests
import feedparser
from datetime import datetime

NEWS_API_KEY = "YOUR_NEWSAPI_KEY"

# ---------------------------
# NewsAPI Function
# ---------------------------
def get_news(query=None, category=None, country=None, page_size=10):

    url = "https://newsapi.org/v2/top-headlines"

    params = {
        "apiKey": NEWS_API_KEY,
        "pageSize": page_size
    }

    if query:
        params["q"] = query

    if category:
        params["category"] = category

    if country:
        params["country"] = country

    response = requests.get(url, params=params)

    if response.status_code == 200:
        return response.json().get("articles", [])

    return []


# ---------------------------
# AI-like Summary
# ---------------------------
def summarize(article):

    title = article.get("title", "")
    desc = article.get("description", "")

    summary = f"""
1. {title}
2. {desc}
3. This news is currently receiving significant attention.
4. It may impact related industries or regions.
5. Readers should monitor future developments.
"""

    return summary


# ---------------------------
# Gold Rate
# ---------------------------
def get_gold_rate():

    try:
        url = "https://api.gold-api.com/price/XAU"

        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            return data.get("price")

    except:
        pass

    return "Not Available"


# ---------------------------
# TCS News
# ---------------------------
def get_tcs_news():

    rss_url = (
        "https://news.google.com/rss/search?"
        "q=TCS+India&hl=en-IN&gl=IN&ceid=IN:en"
    )

    feed = feedparser.parse(rss_url)

    return feed.entries[:10]


# ---------------------------
# UI
# ---------------------------
st.set_page_config(layout="wide")

st.title("🌎 Daily News Dashboard")

st.write(datetime.now())

# ===================================
# International News
# ===================================
st.header("Top 10 International News")

international = get_news(page_size=10)

for i, news in enumerate(international, 1):

    st.subheader(f"{i}. {news['title']}")

    st.write(summarize(news))

    st.write(news["url"])

# ===================================
# IT News
# ===================================
st.header("Top 10 IT Industry News")

it_news = get_news(category="technology", page_size=10)

for i, news in enumerate(it_news, 1):

    st.subheader(f"{i}. {news['title']}")

    st.write(summarize(news))

    st.write(news["url"])

# ===================================
# India News
# ===================================
st.header("Top 10 India News")

india_news = get_news(country="in", page_size=10)

for i, news in enumerate(india_news, 1):

    st.subheader(f"{i}. {news['title']}")

    st.write(summarize(news))

    st.write(news["url"])

# ===================================
# War News
# ===================================
st.header("Top 10 War / Defense News")

war_news = get_news(query="war OR military OR conflict", page_size=10)

for i, news in enumerate(war_news, 1):

    st.subheader(f"{i}. {news['title']}")

    st.write(summarize(news))

    st.write(news["url"])

# ===================================
# Gold Rate
# ===================================
st.header("Gold Rate Today (India)")

gold = get_gold_rate()

st.metric(
    label="Gold Price",
    value=str(gold)
)

# ===================================
# TCS News
# ===================================
st.header("Top 10 TCS News")

tcs_news = get_tcs_news()

for i, news in enumerate(tcs_news, 1):

    st.subheader(f"{i}. {news.title}")

    st.write(news.link)
