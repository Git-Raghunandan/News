```python
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
# CONSTANTS
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "Chrome/151.0.0.0 Safari/537.36"
    )
}

MAX_NEWS = 10

GOODRETURNS_URL = (
    "https://www.goodreturns.in/gold-rates/bhubaneswar.html"
)


# ============================================================
# ROYAL DASHBOARD CSS
# ============================================================

st.markdown(
    """
<style>

/* ==========================================================
   MAIN APPLICATION
   ========================================================== */

.stApp {
    background:
        radial-gradient(
            circle at top right,
            #2b2412 0%,
            #0d0d0d 32%,
            #050505 75%
        );

    color: #f5f5f5;
}


/* ==========================================================
   HEADER
   ========================================================== */

.main-title {
    text-align: center;
    padding-top: 10px;
}

.main-title h1 {
    font-size: 46px;
    font-weight: 800;
    letter-spacing: 4px;
    margin-bottom: 3px;

    color: #d4af37;

    text-shadow:
        0 0 10px rgba(212,175,55,0.25),
        0 0 30px rgba(212,175,55,0.10);
}

.main-title p {
    color: #bdbdbd;
    font-size: 15px;
    letter-spacing: 3px;
    margin-top: 0;
}

.sponsored {
    text-align: center;

    color: #d4af37;

    font-size: 14px;
    font-weight: 700;

    letter-spacing: 3px;

    margin-top: 8px;
    margin-bottom: 20px;
}


/* ==========================================================
   SECTION TITLES
   ========================================================== */

.section-title {

    border-left: 5px solid #d4af37;

    padding-left: 12px;

    margin-top: 30px;
    margin-bottom: 16px;

    color: #d4af37;

    font-size: 24px;
    font-weight: 750;
}


/* ==========================================================
   NEWS CARD
   ========================================================== */

.news-card {

    background:
        linear-gradient(
            145deg,
            rgba(30,30,30,0.97),
            rgba(12,12,12,0.98)
        );

    border: 1px solid rgba(212,175,55,0.24);

    border-radius: 14px;

    padding: 16px 18px;

    margin-bottom: 12px;

    box-shadow:
        0 6px 18px rgba(0,0,0,0.35),
        inset 0 1px 0 rgba(255,255,255,0.025);

    transition:
        border 0.2s ease,
        transform 0.2s ease;
}


.news-card:hover {

    border: 1px solid rgba(212,175,55,0.65);

    transform: translateY(-1px);
}


/* ==========================================================
   NEWS NUMBER
   ========================================================== */

.news-number {

    display: inline-block;

    min-width: 32px;

    color: #d4af37;

    font-size: 17px;

    font-weight: 800;

    vertical-align: top;
}


/* ==========================================================
   NEWS HEADLINE
   ========================================================== */

.news-headline {

    display: inline;

    color: #ffffff;

    font-size: 18px;

    font-weight: 700;

    line-height: 1.4;
}


/* ==========================================================
   NEWS SUMMARY
   ========================================================== */

.news-summary {

    color: #c8c8c8;

    font-size: 14px;

    line-height: 1.6;

    margin-top: 8px;

    padding-left: 32px;
}


/* ==========================================================
   SOURCE
   ========================================================== */

.source {

    color: #777777;

    font-size: 11px;

    margin-top: 8px;

    padding-left: 32px;
}


/* ==========================================================
   GOLD CARD
   ========================================================== */

.gold-card {

    background:
        linear-gradient(
            145deg,
            rgba(70,52,10,0.95),
            rgba(20,15,5,0.98)
        );

    border:

        1px solid
        rgba(212,175,55,0.75);

    border-radius: 18px;

    padding: 22px;

    text-align: center;

    box-shadow:
        0 0 25px rgba(212,175,55,0.10);
}


.gold-label {

    color: #d0d0d0;

    font-size: 14px;

    font-weight: 600;

    letter-spacing: 2px;
}


.gold-price {

    color: #d4af37;

    font-size: 34px;

    font-weight: 800;

    margin-top: 5px;
}


.gold-unit {

    color: #999999;

    font-size: 12px;

    margin-top: 3px;
}


/* ==========================================================
   UPDATE INFORMATION
   ========================================================== */

.update-time {

    text-align: center;

    color: #888888;

    font-size: 12px;

    margin-bottom: 15px;
}


/* ==========================================================
   BUTTON
   ========================================================== */

div.stButton > button {

    background:
        linear-gradient(
            90deg,
            #8c6a16,
            #d4af37
        );

    color: #111111;

    font-weight: 800;

    border: none;

    border-radius: 10px;

    padding: 8px 20px;
}


div.stButton > button:hover {

    background:
        linear-gradient(
            90deg,
            #d4af37,
            #f1d56a
        );

    color: #000000;
}


/* ==========================================================
   FOOTER
   ========================================================== */

.footer {

    text-align: center;

    color: #707070;

    font-size: 11px;

    margin-top: 45px;

    padding: 25px 10px;

    border-top:
        1px solid
        rgba(212,175,55,0.15);
}


/* ==========================================================
   MOBILE
   ========================================================== */

@media (max-width: 768px) {

    .main-title h1 {
        font-size: 30px;
        letter-spacing: 2px;
    }

    .main-title p {
        font-size: 10px;
        letter-spacing: 1px;
    }

    .section-title {
        font-size: 20px;
    }

    .news-headline {
        font-size: 16px;
    }

    .news-summary {
        font-size: 13px;
        padding-left: 0;
    }

    .source {
        padding-left: 0;
    }

    .gold-price {
        font-size: 27px;
    }
}

</style>
""",
    unsafe_allow_html=True
)


# ============================================================
# GOOGLE NEWS RSS URL
# ============================================================

def google_news_url(query):

    encoded_query = quote_plus(query)

    return (
        "https://news.google.com/rss/search?"
        f"q={encoded_query}"
        "&hl=en-IN"
        "&gl=IN"
        "&ceid=IN:en"
    )


# ============================================================
# CLEAN HTML / TEXT
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = html.unescape(text)

    soup = BeautifulSoup(
        text,
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

    return text.strip()


# ============================================================
# CLEAN HEADLINE
# ============================================================

def clean_headline(title, source):

    title = clean_text(title)

    source = clean_text(source)

    if not title:
        return ""

    # Remove source appended after hyphen
    if source:

        title = re.sub(
            rf"\s*[-|]\s*{re.escape(source)}\s*$",
            "",
            title,
            flags=re.IGNORECASE
        )

    return title.strip()


# ============================================================
# CLEAN SUMMARY
# ============================================================

def clean_summary(summary, headline, source):

    summary = clean_text(summary)

    headline = clean_text(headline)

    source = clean_text(source)

    if not summary:
        return ""

    # Remove source
    if source:

        summary = re.sub(
            rf"\s*{re.escape(source)}\s*$",
            "",
            summary,
            flags=re.IGNORECASE
        )

    # Remove duplicated headline
    if headline:

        if summary.lower().startswith(
            headline.lower()
        ):

            summary = summary[
                len(headline):
            ].strip()

    # Remove separators
    summary = re.sub(
        r"^[\s\-|:]+",
        "",
        summary
    )

    return summary.strip()


# ============================================================
# FETCH NEWS
# ============================================================

@st.cache_data(
    ttl=300,
    show_spinner=False
)
def fetch_feed(query, limit=10):

    url = google_news_url(query)

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        response.raise_for_status()

        feed = feedparser.parse(
            response.content
        )

        results = []

        seen_titles = set()

        for entry in feed.entries:

            if len(results) >= limit:
                break

            raw_title = getattr(
                entry,
                "title",
                ""
            )

            raw_summary = getattr(
                entry,
                "summary",
                ""
            )

            source = ""

            if hasattr(entry, "source"):

                source = getattr(
                    entry.source,
                    "title",
                    ""
                )

            headline = clean_headline(
                raw_title,
                source
            )

            summary = clean_summary(
                raw_summary,
                headline,
                source
            )

            if not headline:
                continue

            # Duplicate protection
            title_key = headline.lower()

            if title_key in seen_titles:
                continue

            seen_titles.add(title_key)

            if not summary:

                summary = (
                    "This is one of the latest stories "
                    "currently being reported by online "
                    "news sources."
                )

            # Keep summaries short
            if len(summary) > 360:

                summary = (
                    summary[:357]
                    + "..."
                )

            results.append(
                {
                    "title": headline,
                    "summary": summary,
                    "source": clean_text(source)
                }
            )

        return results

    except Exception as error:

        return [
            {
                "title": "News temporarily unavailable",
                "summary": (
                    "The news feed could not be retrieved "
                    "at this moment."
                ),
                "source": "Swarup Daily News"
            }
        ]


# ============================================================
# NEWS CATEGORIES
# ============================================================

CATEGORIES = {

    "📰 Times of India — Top 10":
        (
            "site:timesofindia.indiatimes.com "
            "(India OR World OR Business OR Technology) "
            "when:1d"
        ),

    "🌎 International — Top 10":
        (
            "(international OR world OR geopolitics "
            "OR USA OR Europe OR China OR Russia "
            "OR Middle East) "
            "when:1d"
        ),

    "💻 IT Industry — Top 10":
        (
            "(Microsoft OR Google OR Amazon OR Apple "
            "OR OpenAI OR AI OR cybersecurity OR cloud "
            "OR software OR technology OR IT industry) "
            "when:1d"
        ),

    "🇮🇳 India — Top 10":
        (
            "India news when:1d"
        ),

    "🏝️ Odisha — Top 10":
        (
            "(Odisha OR Bhubaneswar OR Cuttack "
            "OR Rourkela OR Puri) "
            "when:1d"
        ),

    "🏆 TCS India — Top 10":
        (
            '("Tata Consultancy Services" '
            'OR "TCS India") '
            "when:7d"
        )
}


# ============================================================
# DISPLAY NEWS
# ============================================================

def display_news(
    title,
    articles
):

    st.markdown(
        f"""
        <div class="section-title">
            {html.escape(title)}
        </div>
        """,
        unsafe_allow_html=True
    )

    if not articles:

        st.warning(
            "No news available at the moment."
        )

        return

    for index, article in enumerate(
        articles[:MAX_NEWS],
        start=1
    ):

        headline = clean_text(
            article.get(
                "title",
                ""
            )
        )

        summary = clean_text(
            article.get(
                "summary",
                ""
            )
        )

        source = clean_text(
            article.get(
                "source",
                ""
            )
        )

        st.markdown(
            f"""
<div class="news-card">

    <span class="news-number">
        {index:02d}
    </span>

    <span class="news-headline">
        {html.escape(headline)}
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
# GET GOLD RATE
# ============================================================

@st.cache_data(
    ttl=300,
    show_spinner=False
)
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

        text = soup.get_text(
            " ",
            strip=True
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        # ----------------------------------------------------
        # Method 1
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Method 2 - alternate page formatting
        # ----------------------------------------------------

        if not match_24:

            match_24 = re.search(
                r"24\s*karat.*?"
                r"₹\s*([\d,]+)",
                text,
                re.IGNORECASE
            )

        if not match_22:

            match_22 = re.search(
                r"22\s*karat.*?"
                r"₹\s*([\d,]+)",
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
# DISPLAY GOLD
# ============================================================

def display_gold():

    st.markdown(
        """
        <div class="section-title">
            🪙 Gold Rate Today — Bhubaneswar
        </div>
        """,
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
        ₹{html.escape(rate_24)}
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
        ₹{html.escape(rate_22)}
    </div>

    <div class="gold-unit">
        per gram
    </div>

</div>
""",
            unsafe_allow_html=True
        )


# ============================================================
# DASHBOARD HEADER
# ============================================================

st.markdown(
    """
<div class="main-title">

    <h1>
        👑 SWARUP DAILY NEWS
    </h1>

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
# CURRENT TIME
# ============================================================

current_time = datetime.now()

st.markdown(
    f"""
<div class="update-time">

    Last refreshed:
    {current_time.strftime("%d %B %Y • %I:%M %p")}

</div>
""",
    unsafe_allow_html=True
)


# ============================================================
# REFRESH BUTTON
# ============================================================

button_col1, button_col2, button_col3 = st.columns(
    [1, 2, 1]
)

with button_col2:

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
# FETCH NEWS IN PARALLEL
# ============================================================

news_data = {}

with st.spinner(
    "👑 Collecting today's news..."
):

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

                news_data[category] = (
                    job.result()
                )

            except Exception:

                news_data[category] = []


# ============================================================
# DISPLAY ALL NEWS
# ============================================================

for category in CATEGORIES:

    display_news(
        category,
        news_data.get(
            category,
            []
        )
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
<div class="footer">

    👑 <b>SWARUP DAILY NEWS</b>

    <br><br>

    ✦ SPONSORED BY SWARUP ✦

    <br><br>

    News is automatically collected from
    publicly available online news feeds.

    <br>

    Headlines and summaries are provided
    for informational purposes.

    <br><br>

    © 2026 Swarup Daily News

</div>
""",
    unsafe_allow_html=True
)
```
