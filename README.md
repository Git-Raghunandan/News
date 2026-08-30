# 📰 Swarup Daily News Dashboard

A professional, colorful Streamlit dashboard designed to be hosted on GitHub + Streamlit Community Cloud and shared through WhatsApp.

## What it collects

- 🌍 Top 10 International News
- 🇮🇳 Top 10 India News
- 🌊 Top 10 Odisha News
- 🥇 Today's Bhubaneswar gold rate — 24K and 22K
- 💻 TCS Newsroom — latest TCS items
- 👥 Current India population from Worldometer

## Branding

The dashboard displays:

**Sponsored by Swarup**

and the environmental message:

**Save paper, save trees, save the Earth**

## Data sources

- General news: Google News RSS search feeds
- Gold: https://www.goodreturns.in/gold-rates/bhubaneswar.html
- TCS: https://www.tcs.com/who-we-are/newsroom
- Population: https://www.worldometers.info/world-population/india-population/

The gold, TCS and population pages are fetched directly by the Python application.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the Streamlit URL shown in the terminal.

## Deploy on GitHub + Streamlit Community Cloud

1. Create a new GitHub repository.
2. Upload:
   - `app.py`
   - `requirements.txt`
   - `README.md`
3. Go to Streamlit Community Cloud.
4. Create a new app from your GitHub repository.
5. Select `app.py` as the main file.
6. Deploy.
7. Copy the public Streamlit URL and share it on WhatsApp.

## Refresh behavior

Data is cached for a short period to reduce unnecessary requests. Users can press **Refresh all data** in the sidebar for an immediate refresh.

## Important note

News ranking is based on the order returned by the Google News RSS search. It is not a proprietary editorial ranking.

The GoodReturns gold rates are indicative and may not include GST, TCS or other levies. Always verify the final jewellery price with a local jeweller.

Worldometer's live population is an estimate generated from its population data methodology; the page also publishes a 2026 mid-year estimate.

## Suggested GitHub repository name

`swarup-daily-news-dashboard`
