import re
import html
from datetime import datetime
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import streamlit as st
from bs4 import BeautifulSoup

# ------------------------------------------------------------
# Swarup News Dashboard
# A source-linked dashboard. It reads publicly visible pages and
# displays headlines + short source snippets. It does not bypass
# paywalls, robots.txt, authentication, or anti-bot controls.
# ------------------------------------------------------------

st.set_page_config(
    page_title="Swarup Daily News Dashboard",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0 Safari/537.36 "
        "SwarupNewsDashboard/1.0"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}
TIMEOUT = 18

SOURCES = {
    "International News": "https://www.reuters.com/world/",
    "IT Industry News": "https://www.reuters.com/technology/",
    "India News": "https://newsonair.gov.in/",
    "Odisha News": "https://odishatv.in/",
    "Gold Rate": "https://www.goodreturns.in/gold-rates/bhubaneswar.html",
    "TCS News": "https://www.tcs.com/who-we-are/newsroom",
    "India Population": "https://www.worldometers.info/world-population/india-population/",
}


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def fetch_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return response.text


def soup_for(url: str) -> BeautifulSoup:
    return BeautifulSoup(fetch_html(url), "html.parser")


def absolute_url(base_url: str, href: str) -> str:
    return urljoin(base_url, href)


def same_domain(url: str, domain: str) -> bool:
    return urlparse(url).netloc.lower().endswith(domain)


def article_candidates(base_url: str, section_hint: str = ""):
    """Generic extraction of article-like links from a public HTML page."""
    soup = soup_for(base_url)
    found = []
    seen = set()

    for a in soup.find_all("a", href=True):
        title = clean_text(a.get_text(" ", strip=True))
        href = absolute_url(base_url, a["href"])

        if not title or len(title) < 25:
            continue
        if href.startswith("javascript:") or href.startswith("#"):
            continue

        p = urlparse(href)
        if p.scheme not in ("http", "https"):
            continue

        # Domain-specific URL heuristics.
        path = p.path.lower()
        article_like = False

        if "reuters.com" in p.netloc:
            article_like = (
                (section_hint == "world" and path.startswith("/world/"))
                or (section_hint == "technology" and path.startswith("/technology/"))
            ) and len(path.strip("/").split("/")) >= 2
        elif "newsonair.gov.in" in p.netloc:
            article_like = any(x in path for x in ["/news/", "/category/", "/news-update"])
        elif "odishatv.in" in p.netloc:
            article_like = (
                "/news/" in path
                or "/odisha/" in path
                or "/india/" in path
                or "/national/" in path
            )
        elif "tcs.com" in p.netloc:
            article_like = "/who-we-are/newsroom/" in path

        if not article_like:
            continue

        # Avoid duplicate links and obvious utility/navigation pages.
        if href in seen:
            continue
        bad_words = ["login", "search", "contact", "about-us", "privacy", "terms"]
        if any(w in path for w in bad_words):
            continue

        seen.add(href)
        found.append((title, href))

    return found


def article_description(url: str, fallback: str = "") -> str:
    try:
        soup = soup_for(url)
        for selector in [
            ('meta[property="og:description"]', "content"),
            ('meta[name="description"]', "content"),
        ]:
            tag = soup.select_one(selector[0])
            if tag and tag.get(selector[1]):
                text = clean_text(tag.get(selector[1]))
                if len(text) >= 40:
                    return text

        # Look for a concise first paragraph if metadata is missing.
        for p in soup.find_all("p"):
            text = clean_text(p.get_text(" ", strip=True))
            if 60 <= len(text) <= 500:
                return text
    except Exception:
        pass

    return clean_text(fallback)


def enrich_articles(items, limit=10):
    """Fetch article descriptions concurrently while preserving order."""
    items = items[:limit]
    results = [None] * len(items)

    with ThreadPoolExecutor(max_workers=min(8, max(1, len(items)))) as pool:
        futures = {
            pool.submit(article_description, url, title): i
            for i, (title, url) in enumerate(items)
        }
        for future in as_completed(futures):
            i = futures[future]
            title, url = items[i]
            try:
                desc = future.result()
            except Exception:
                desc = title
            results[i] = {
                "title": title,
                "description": clean_text(desc) or title,
                "url": url,
            }
    return results


def fetch_reuters(section_url, section_hint):
    candidates = article_candidates(section_url, section_hint)
    # Reuters pages can contain repeated/related links. Deduplicate by title.
    unique = []
    titles = set()
    for title, url in candidates:
        key = re.sub(r"[^a-z0-9]+", "", title.lower())
        if key in titles:
            continue
        titles.add(key)
        unique.append((title, url))
    return enrich_articles(unique, 10)


def fetch_newsonair():
    candidates = article_candidates(SOURCES["India News"])
    # Prefer article links; if the homepage changes its markup, fall back
    # to visible headings linked to newsonair.gov.in.
    if not candidates:
        soup = soup_for(SOURCES["India News"])
        for tag in soup.find_all(["h1", "h2", "h3"]):
            title = clean_text(tag.get_text(" ", strip=True))
            a = tag.find("a", href=True) or tag.parent.find("a", href=True)
            if title and a:
                candidates.append((title, absolute_url(SOURCES["India News"], a["href"])))
    return enrich_articles(candidates, 10)


def fetch_otv():
    candidates = article_candidates(SOURCES["Odisha News"])
    return enrich_articles(candidates, 10)


def fetch_tcs():
    candidates = article_candidates(SOURCES["TCS News"])
    return enrich_articles(candidates, 10)


def extract_money(text):
    text = clean_text(text)
    # Supports ₹15,824, Rs 15,824, 15824.
    m = re.search(r"(?:₹|Rs\.?\s*)\s*([\d,]+(?:\.\d+)?)", text)
    return m.group(1) if m else None


def fetch_gold():
    soup = soup_for(SOURCES["Gold Rate"])
    page_text = clean_text(soup.get_text(" ", strip=True))

    result = {"24K": None, "22K": None, "date": None, "url": SOURCES["Gold Rate"]}

    # First inspect tables, which are usually the most stable source of rates.
    for row in soup.find_all("tr"):
        cells = [clean_text(c.get_text(" ", strip=True)) for c in row.find_all(["th", "td"])]
        row_text = " | ".join(cells)
        if "24K" in row_text and "22K" in row_text:
            amounts = re.findall(r"(?:₹|Rs\.?\s*)\s*([\d,]+(?:\.\d+)?)", row_text)
            if len(amounts) >= 2:
                result["24K"], result["22K"] = amounts[0], amounts[1]
                break

    # Fallback: search text around labels.
    if not result["24K"]:
        m = re.search(r"24\s*K.*?(?:₹|Rs\.?\s*)\s*([\d,]+)", page_text, re.I)
        if m:
            result["24K"] = m.group(1)
    if not result["22K"]:
        m = re.search(r"22\s*K.*?(?:₹|Rs\.?\s*)\s*([\d,]+)", page_text, re.I)
        if m:
            result["22K"] = m.group(1)

    date_match = re.search(
        r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})",
        page_text,
        re.I,
    )
    if date_match:
        result["date"] = date_match.group(1)

    return result


def fetch_population():
    soup = soup_for(SOURCES["India Population"])
    text = clean_text(soup.get_text(" ", strip=True))

    # Worldometer publishes the 2026 population prominently. We first
    # locate the India Population section and then the first large integer.
    population = None
    section = re.search(
        r"Population of India.*?India Population\s+([\d,]+)",
        text,
        re.I,
    )
    if section:
        population = section.group(1)

    if not population:
        # Fallback: find a 10+ digit number near "India Population".
        idx = text.lower().find("india population")
        window = text[max(0, idx): idx + 600] if idx >= 0 else text[:3000]
        nums = re.findall(r"\b\d{1,3}(?:,\d{3}){3,}\b", window)
        if nums:
            population = nums[0]

    return {
        "population": population,
        "url": SOURCES["India Population"],
        "checked": datetime.now().strftime("%d %b %Y, %I:%M %p"),
    }


def render_news_section(title, items, source_url):
    st.subheader(title)
    if not items:
        st.warning("No articles could be read from this source right now.")
        st.link_button("Open source", source_url)
        return

    for i, item in enumerate(items, start=1):
        with st.container(border=True):
            st.markdown(f"**{i}. {item['title']}**")
            st.write(item["description"])
            st.link_button("Read original", item["url"])
    st.caption(f"Source: {source_url}")


# ------------------------ UI ------------------------

st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 0;
    }
    .subtitle {
        font-size: 1.05rem;
        opacity: .82;
        margin-top: 0.2rem;
    }
    .sponsor {
        display: inline-block;
        padding: .35rem .75rem;
        border-radius: 999px;
        background: linear-gradient(90deg,#ff7a18,#af002d 70%,#319197);
        color: white;
        font-weight: 700;
        margin-top: .6rem;
    }
    .eco {
        text-align:center;
        padding: .8rem;
        border-radius: 14px;
        font-weight: 700;
        margin: 1.2rem 0;
        background: linear-gradient(90deg,#e8f5e9,#fff8e1,#e3f2fd);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="main-title">📰 Swarup Daily News Dashboard</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Headlines, short source summaries, gold rates and India population — refreshed from the requested online sources.</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="sponsor">Sponsored by Swarup</div>', unsafe_allow_html=True)

st.sidebar.title("Dashboard Controls")
if st.sidebar.button("🔄 Refresh all feeds", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

auto_refresh = st.sidebar.checkbox("Auto-refresh every 15 minutes", value=True)
if auto_refresh:
    # Streamlit supports this meta-refresh without an extra dependency.
    st.markdown(
        '<meta http-equiv="refresh" content="900">',
        unsafe_allow_html=True,
    )

st.sidebar.markdown("### Sources")
for name, url in SOURCES.items():
    st.sidebar.link_button(name, url, use_container_width=True)

# No long-lived cache: opening/rerunning the app fetches current source pages.
# A short cache avoids hammering sites when Streamlit reruns multiple times.
@st.cache_data(ttl=300, show_spinner=False)
def load_all():
    data = {}
    errors = {}

    jobs = {
        "International News": lambda: fetch_reuters(SOURCES["International News"], "world"),
        "IT Industry News": lambda: fetch_reuters(SOURCES["IT Industry News"], "technology"),
        "India News": fetch_newsonair,
        "Odisha News": fetch_otv,
        "TCS News": fetch_tcs,
        "Gold Rate": fetch_gold,
        "India Population": fetch_population,
    }

    with ThreadPoolExecutor(max_workers=7) as pool:
        futures = {pool.submit(fn): name for name, fn in jobs.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                data[name] = future.result()
            except Exception as exc:
                data[name] = None
                errors[name] = str(exc)

    return data, errors


with st.spinner("Collecting the latest information…"):
    data, errors = load_all()

# KPI row
gold = data.get("Gold Rate") or {}
pop = data.get("India Population") or {}
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("🥇 Gold 24K / gram", f"₹{gold.get('24K')}" if gold.get("24K") else "Unavailable")
with c2:
    st.metric("🥇 Gold 22K / gram", f"₹{gold.get('22K')}" if gold.get("22K") else "Unavailable")
with c3:
    st.metric("🇮🇳 India Population", pop.get("population") or "Unavailable")
with c4:
    st.metric("🕒 Dashboard checked", datetime.now().strftime("%d %b %Y"))

if gold.get("date"):
    st.caption(f"Gold-rate page date: {gold['date']} • Rates are informational and may differ from a jeweller's final price.")
if pop.get("population"):
    st.caption(f"Population source checked at {pop.get('checked')}. Worldometer presents population as a live/current estimate.")

if errors:
    with st.expander("Source connection notes"):
        for name, message in errors.items():
            st.write(f"**{name}:** {message}")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(
    ["🌍 International", "💻 IT Industry", "🇮🇳 India", "🌿 Odisha"]
)

with tab1:
    render_news_section(
        "Top 10 International News",
        data.get("International News", []),
        SOURCES["International News"],
    )

with tab2:
    render_news_section(
        "Top 10 IT Industry News",
        data.get("IT Industry News", []),
        SOURCES["IT Industry News"],
    )

with tab3:
    render_news_section(
        "Top 10 India News",
        data.get("India News", []),
        SOURCES["India News"],
    )

with tab4:
    render_news_section(
        "Top 10 Odisha News",
        data.get("Odisha News", []),
        SOURCES["Odisha News"],
    )

st.divider()
render_news_section("🏢 TCS — Latest News", data.get("TCS News", []), SOURCES["TCS News"])

st.markdown(
    """
    <div class="eco">
    🌳 Save paper, save trees, save the Earth 🌍
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "This dashboard summarizes and links to publicly available material from the named sources. "
    "All article rights and trademarks remain with their respective publishers. "
    "If a publisher changes its page structure or blocks automated requests, that feed may temporarily show no results."
)
