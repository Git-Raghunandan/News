# Swarup Daily News Dashboard

A professional Streamlit dashboard that collects and displays:

- 10 International news items from Reuters World
- 10 IT Industry news items from Reuters Technology
- 10 India news items from NewsOnAir
- 10 Odisha news items from OdishaTV
- Today's 24K and 22K gold rates from Goodreturns Bhubaneswar
- Latest TCS newsroom items from TCS
- Current India population from Worldometer
- Headline + a short source-provided/metadata summary + original article link
- Branding: **Sponsored by Swarup**
- Eco message: **Save paper, save trees, save the Earth**

## Important

The app reads publicly visible web pages. It does **not** bypass paywalls, login pages, robots.txt restrictions, or anti-bot systems.

News sites can change their HTML structure. If a source changes its page markup, the corresponding parser may need a selector update.

## Run locally

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

## GitHub + Streamlit Community Cloud

1. Create a GitHub repository.
2. Upload `app.py` and `requirements.txt`.
3. In Streamlit Community Cloud, create a new app.
4. Select your GitHub repository and set the main file to `app.py`.
5. Deploy.
6. Copy the Streamlit URL and share it on WhatsApp.

The app includes a **Refresh all feeds** button and a 15-minute browser refresh option.

## Suggested repository name

`swarup-daily-news-dashboard`

## Source URLs

- Reuters World: https://www.reuters.com/world/
- Reuters Technology: https://www.reuters.com/technology/
- NewsOnAir: https://newsonair.gov.in/
- OdishaTV: https://odishatv.in/
- Goodreturns Bhubaneswar Gold Rates: https://www.goodreturns.in/gold-rates/bhubaneswar.html
- TCS Newsroom: https://www.tcs.com/who-we-are/newsroom
- Worldometer India Population: https://www.worldometers.info/world-population/india-population/
