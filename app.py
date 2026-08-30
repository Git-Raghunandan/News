
import streamlit as st
import requests

API_KEY = "6720bdf041f942e3a472dcfdc722fa9c"

URL = (
    f"https://newsapi.org/v2/top-headlines?"
    f"category=general&language=en&pageSize=10&apiKey={API_KEY}"
)

st.set_page_config(
    page_title="International News",
    page_icon="🌍",
    layout="wide"
)

st.title("🌍 Top 10 International News")

try:
    response = requests.get(URL, timeout=20)
    data = response.json()

    if data["status"] == "ok":
        articles = data["articles"]

        for idx, article in enumerate(articles, start=1):

            title = article.get("title", "No Title")
            description = article.get(
                "description",
                "Description not available."
            )

            st.subheader(f"{idx}. {title}")

            if len(description) > 200:
                description = description[:200] + "..."

            st.write(description)

            if article.get("url"):
                st.markdown(
                    f"[Read Full Article]({article['url']})"
                )

            st.divider()

    else:
        st.error("Unable to fetch news.")

except Exception as e:
    st.error(f"Error: {e}")
