# Swarup News & India Intelligence Dashboard

A professional Streamlit dashboard that collects and presents:

- 10 top International news — Reuters
- 10 top IT Industry news — Reuters Technology
- 10 top India news — News On AIR
- 10 top Odisha news — OdishaTV
- Today's 24K & 22K gold rate — Goodreturns Bhubaneswar
- 10 TCS newsroom items — TCS
- Current India population — Worldometer

The dashboard includes clickable links to the original publishers and is branded:

> **Sponsored by Swarup**

> **Save paper, save trees, save the Earth**

## Important note about news websites

News websites can change their HTML, RSS feeds, anti-bot rules, and URL structures. This project therefore uses:

1. configured RSS feed URLs where available,
2. automatic RSS/Atom discovery,
3. HTML fallback extraction.

If a publisher changes its layout, the corresponding selector/feed may need a small update.

Always respect each publisher's Terms of Use, robots.txt, copyright, and rate limits. The dashboard displays headlines/short summaries and links users to the original articles rather than copying full articles.

## Run locally

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run:

```bash
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Create a GitHub repository.
2. Upload:
   - `app.py`
   - `requirements.txt`
   - `.gitignore`
   - `README.md`
3. Open Streamlit Community Cloud.
4. Connect the GitHub repository.
5. Select `app.py` as the main file.
6. Deploy.

The resulting Streamlit URL can be shared through WhatsApp.

## Refresh behavior

The app uses a 15-minute Streamlit cache. Every user opening the dashboard will normally see cached data until the cache expires. The sidebar also has a **Refresh now** button.

## WhatsApp

After deployment, simply send the Streamlit URL in WhatsApp. The recipient can open the live dashboard in a browser. If you want scheduled WhatsApp messages containing the actual headlines, that is a separate automation/integration and would require a WhatsApp API/provider.

## Source URLs

- Reuters: https://www.reuters.com/
- Reuters Technology: https://www.reuters.com/technology/
- News On AIR: https://newsonair.gov.in/
- OdishaTV: https://odishatv.in/
- Goodreturns Bhubaneswar Gold: https://www.goodreturns.in/gold-rates/bhubaneswar.html
- TCS Newsroom: https://www.tcs.com/who-we-are/newsroom
- Worldometer India Population: https://www.worldometers.info/world-population/india-population/
