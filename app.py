import streamlit as st
import pandas as pd
import sqlite3
from google import genai
from dotenv import load_dotenv
import os
import json
import hashlib
from datetime import datetime

# ── SETUP ────────────────────────────────────────────────────
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API"))

conn = sqlite3.connect("worldbank.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='india_indicators'")
schema = cursor.fetchone()[0]
cursor.execute("SELECT * FROM india_indicators LIMIT 3")
sample_rows = cursor.fetchall()

# ── CACHE  ────────────────────────────────────────────────────

CACHE_FILE = "cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

def make_key(question):
    return hashlib.md5(question.lower().strip().encode()).hexdigest()

def ask(question):
    cache = load_cache()
    key = make_key(question)

    if key in cache:
        entry = cache[key]
        result_df = pd.DataFrame(entry['result_data'], columns=entry['result_columns'])
        return {
            "answer": entry['answer'],
            "sql": entry['sql'],
            "result_df": result_df,
            "from_cache": True
        }

    sql_prompt = f"""
You are a SQL expert working with a SQLite database.
Table name: india_indicators
World Bank data for India from 2014 to 2024.

Schema:
{schema}

Sample rows:
{sample_rows}

Rules:
- Year columns are named: 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024
- "Series Name" column has indicator names like "GDP (current US$)"
- Missing values are NULL
- Return ONLY raw SQL. No markdown, no backticks, no explanation.

Question: {question}
"""
    sql_response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=sql_prompt
    )
    sql_query = sql_response.text.strip()

    result_df = None
    max_retries = 2
    for attempt in range(max_retries):
        try:
            result_df = pd.read_sql_query(sql_query, conn)
            break
        except Exception as e:
            if attempt < max_retries - 1:
                fix_response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"Fix this SQLite error:\n{e}\n\nBroken query:\n{sql_query}\n\nReturn ONLY fixed SQL. No markdown, no backticks."
                )
                sql_query = fix_response.text.strip()
            else:
                return {"error": f"Could not fix SQL after retries. Last error: {e}"}

    if result_df is None:
        return {"error": "No results returned."}

    explain_response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f'User asked: "{question}"\nData:\n{result_df.to_string()}\nWrite 2-3 sentence plain English answer with specific numbers.'
    )
    answer = explain_response.text.strip()

    cache[key] = {
        "question": question,
        "sql": sql_query,
        "result_columns": result_df.columns.tolist(),
        "result_data": result_df.values.tolist(),
        "answer": answer
    }
    save_cache(cache)

    return {
        "answer": answer,
        "sql": sql_query,
        "result_df": result_df,
        "from_cache": False,
    }

# ── PAGE CONFIG ───────────────────────────────────────────────
st.set_page_config(
    page_title="India Data Assistant",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_css():
    with open("style.css", "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📦 Previously Answered Questions")
    st.markdown("---")
    cache = load_cache()
    if not cache:
        st.markdown("<p style='color:#aaaaaa;font-size:0.85rem'>No cached questions yet.</p>",
                    unsafe_allow_html=True)
    else:
        st.markdown(f"<p style='color:#6abf6a;font-size:0.85rem'>⚡ {len(cache)} question(s) cached</p>",
                    unsafe_allow_html=True)
        st.markdown("")
        for entry in list(cache.values())[-10:]:
            st.markdown(
                f"<div style='padding:0.4rem 0;border-bottom:1px solid #2a2a3a'>"
                f"<span style='color:#cccccc;font-size:0.82rem'>"
                f"{entry['question'][:45]}{'...' if len(entry['question']) > 45 else ''}"
                f"</span><br>"
                f"<span style='color:#666;font-size:0.75rem;font-family:monospace'>"
                f"</span></div>",
                unsafe_allow_html=True
            )
    st.markdown("---")
    st.markdown("<p style='color:#555;font-size:0.75rem'>Data: World Bank India 2014–2024</p>",
                unsafe_allow_html=True)

# ── MAIN UI ───────────────────────────────────────────────────
st.markdown('<div class="main-title">India Data<br>Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">World Bank Indicators · Natural Language Interface</div>',
            unsafe_allow_html=True)

col1, col2 = st.columns([5, 1])
with col1:
    question = st.text_input(
        label="question",
        label_visibility="collapsed",
        placeholder="e.g. What was India's GDP in 2022?"
    )
with col2:
    ask_btn = st.button("Ask →")

st.markdown(
    "<div style='margin-top:0.5rem'>"
    "<span style='color:#444;font-size:0.8rem;font-family:monospace'>try: </span>"
    "<span style='color:#666;font-size:0.8rem;font-family:monospace'>"
    "life expectancy trend · GDP vs population · electric power consumption · highest inflation year"
    "</span></div>",
    unsafe_allow_html=True
)

st.markdown("---")

# ── RESULT ────────────────────────────────────────────────────
if ask_btn and question.strip():
    with st.spinner("Thinking..."):
        result = ask(question)

    if "error" in result:
        st.error(result["error"])
    else:
        if result["from_cache"]:
            st.markdown(
                f'<div class="cache-hit">⚡ cache hit · {result["timestamp"]}</div>',
                unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="cache-miss">✦ generated · {result["timestamp"]}</div>',
                unsafe_allow_html=True)

        st.markdown('<div class="section-label">Answer</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="answer-card">{result["answer"]}</div>',
                    unsafe_allow_html=True)

        st.markdown('<div class="section-label">Data</div>', unsafe_allow_html=True)
        st.dataframe(result["result_df"], use_container_width=True, hide_index=True)

        col1, col2 = st.columns([1, 5])
        with col1:
            st.download_button(
                label="⬇ CSV",
                data=result["result_df"].to_csv(index=False),
                file_name="result.csv",
                mime="text/csv"
            )

        with st.expander("🔍 SQL query"):
            st.code(result["sql"], language="sql")
