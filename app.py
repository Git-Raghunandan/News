import requests
import streamlit as st
from datetime import datetime

# ==========================
# CONFIGURATION
# ==========================

NEWS_API_KEY = "YOUR_NEWSAPI_KEY"

# ==========================
# NEWS FUNCTIONS
# ==========================

def get_news(query, count=10):
    try:
        url = (
            f"https://newsapi.org/v2/everything?"
            f"q={query}&language=en&sortBy=publishedAt&pageSize={count}"
            f"&apiKey={NEWS_API_KEY}"
        )

        response = requests.get(url, timeout=20)
        data = response.json()

        articles = []

        for item in data.get("articles", []):
            articles.append({
                "title": item.get("title"),
                "description": item.get("description"),
                "content": item.get("content")
            })

        return articles

    except Exception as e:
        return [{"title": f"Error: {str(e)}"}]


# ==========================
# GOLD RATE
# ==========================

def get_gold_rate():
    """
    Uses multiple fallbacks so that
    Gold 24K / Gold 22K never become blank.
    """

    try:
        url = "https://www.goldapi.io/api/XAU/INR"

        headers = {
            "x-access-token": "YOUR_GOLD_API_KEY",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, timeout=20)

        if response.status_code == 200:

            data = response.json()

            price_per_gram_24k = round(data["price"] / 31.1035, 2)

            price_per_gram_22k = round(
                price_per_gram_24k * 0.916,
                2
            )

            return {
                "24K": f"₹{price_per_gram_24k}/gm",
                "22K": f"₹{price_per_gram_22k}/gm"
            }

    except:
        pass

    # Fallback values
    return {
        "24K": "Data Source Temporarily Busy",
        "22K": "Data Source Temporarily Busy"
    }


# ==========================
# SUMMARIZER
# ==========================

def summarize(article):

    text = article.get("description")

    if not text:
        text = article.get("content")

    if not text:
        return "Summary not available."

    return text[:400]


# ==========================
# DISPLAY
# ==========================

def show_news_section(title, query):

    st.header(title)

    articles = get_news(query)

    for idx, article in enumerate(articles, start=1):

        st.subheader(f"{idx}. {article['title']}")

        st.write(summarize(article))

        st.markdown("---")


# ==========================
# STREAMLIT UI
# ==========================

st.title("Daily News Dashboard")

st.write(
    f"Last Updated: {datetime.now().strftime('%d-%b-%Y %H:%M:%S')}"
)

# Gold Rate

gold = get_gold_rate()

st.header("Gold Rate Today (India)")

st.write(f"24K Gold : {gold['24K']}")
st.write(f"22K Gold : {gold['22K']}")

st.markdown("---")

# International News

show_news_section(
    "Top 10 International News",
    "world"
)

# IT Industry News

show_news_section(
    "Top 10 IT Industry News",
    "information technology OR cloud OR AI OR cybersecurity"
)

# India News

show_news_section(
    "Top 10 India News",
    "India"
)

# War News

show_news_section(
    "Top 10 Global War News",
    "war OR military OR conflict"
)

# TCS News

show_news_section(
    "Latest TCS News",
    "Tata Consultancy Services OR TCS"
)
