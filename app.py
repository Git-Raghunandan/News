from gnews import GNews
import streamlit as st
import pandas as pd
from datetime import datetime

# ---------------------------------------
# Configuration
# ---------------------------------------

google_news = GNews(
    language='en',
    country='IN',
    max_results=10
)

# ---------------------------------------
# Function
# ---------------------------------------

def fetch_news(search_term, limit=10):

    try:
        articles = google_news.get_news(search_term)

        news_list = []

        for article in articles[:limit]:

            title = article.get("title", "N/A")
            description = article.get("description", "No description available")
            source = article.get("publisher", {}).get("title", "Unknown")

            news_list.append({
                "Title": title,
                "Source": source,
                "Description": description
            })

        return news_list

    except Exception as e:
        return [{
            "Title": "Error",
            "Source": "",
            "Description": str(e)
        }]


# ---------------------------------------
# Streamlit UI
# ---------------------------------------

st.set_page_config(
    page_title="Global News Dashboard",
    layout="wide"
)

st.title("📰 Global News Dashboard")

st.write(
    f"Last Refreshed: {datetime.now().strftime('%d-%b-%Y %H:%M:%S')}"
)

tab1, tab2, tab3, tab4 = st.tabs([
    "International",
    "IT Industry",
    "India",
    "War"
])

# ---------------------------------------
# International News
# ---------------------------------------

with tab1:

    st.header("🌎 Top International News")

    news = fetch_news("world")

    for i, item in enumerate(news, 1):

        st.subheader(f"{i}. {item['Title']}")
        st.write(f"**Source:** {item['Source']}")
        st.write(item['Description'])
        st.divider()


# ---------------------------------------
# IT News
# ---------------------------------------

with tab2:

    st.header("💻 IT Industry News")

    news = fetch_news("technology")

    for i, item in enumerate(news, 1):

        st.subheader(f"{i}. {item['Title']}")
        st.write(f"**Source:** {item['Source']}")
        st.write(item['Description'])
        st.divider()


# ---------------------------------------
# India News
# ---------------------------------------

with tab3:

    st.header("🇮🇳 India News")

    news = fetch_news("India")

    for i, item in enumerate(news, 1):

        st.subheader(f"{i}. {item['Title']}")
        st.write(f"**Source:** {item['Source']}")
        st.write(item['Description'])
        st.divider()


# ---------------------------------------
# War News
# ---------------------------------------

with tab4:

    st.header("⚔️ Global War News")

    news = fetch_news(
        "Ukraine Russia OR Israel Hamas OR conflict"
    )

    for i, item in enumerate(news, 1):

        st.subheader(f"{i}. {item['Title']}")
        st.write(f"**Source:** {item['Source']}")
        st.write(item['Description'])
        st.divider()
