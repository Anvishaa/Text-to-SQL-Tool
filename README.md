# World Bank India Query Tool

A simple tool that lets you ask questions about India's World Bank 
development data (2014–2024) in plain English and get answers back.

You type a question. It generates SQL, runs it on a local database, 
and returns the result with a plain English explanation.

## What it does

- Takes a natural language question as input
- Uses Gemini to generate a SQL query for it
- Runs that query locally on a SQLite database
- Returns the result table and a plain English answer
- Caches answers so repeated questions don't call the API again
- Has a Streamlit UI to interact with it in the browser

## Stack

- Python
- Google Gemini API (gemini-2.5-flash)
- SQLite
- pandas
- Streamlit

## Data

World Bank development indicators for India, 2014–2024.
Covers GDP, population, life expectancy, energy consumption, 
inflation, education, and ~50 other indicators.

## How to run

1. Clone the repo
2. Install dependencies
   pip install google-genai pandas streamlit python-dotenv
3. Add your Gemini API key to a .env file
   GEMINI_API=your_key_here
4. Run setup once to build the database
   python setup.py
5. Start the app
   streamlit run app.py

## Limitations

- Only covers India, 2014–2024
- Some indicators have missing values for certain years
- Complex multi-step questions sometimes produce incorrect SQL
- Free tier Gemini API has rate limits
- might not recognize same question if asked differently from cache
