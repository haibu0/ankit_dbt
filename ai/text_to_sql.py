import os
import json
import time
import numpy as np
import pandas as pd
import streamlit as st
import snowflake.connector
from google import genai
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 🎨 STREAMLIT PAGE CONFIG & STYLING
# ==========================================
st.set_page_config(
    page_title="Spotify Text-to-SQL Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for Spotify Dark Aesthetic
st.markdown(
    """
    <style>
        .stApp {
            background-color: #121212;
            color: #FFFFFF;
        }
        h1, h2, h3 {
            color: #FFFFFF !important;
            font-weight: 700 !important;
        }
        .sql-box {
            background: linear-gradient(145deg, #181818 0%, #1e1e1e 100%);
            border: 1px solid #2d2d2d;
            border-left: 4px solid #1DB954;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        }
        .metric-card {
            background-color: #1a1a1a;
            border: 1px solid #2c2c2c;
            border-radius: 10px;
            padding: 14px 18px;
            text-align: center;
        }
        .metric-val {
            font-size: 1.6rem;
            font-weight: 700;
            color: #1DB954;
        }
        .metric-lbl {
            font-size: 0.85rem;
            color: #b3b3b3;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .badge-safe {
            background-color: rgba(29, 185, 84, 0.15);
            color: #1DB954;
            border: 1px solid #1DB954;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 600;
            display: inline-block;
        }
        .badge-danger {
            background-color: rgba(255, 75, 75, 0.15);
            color: #FF4B4B;
            border: 1px solid #FF4B4B;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 600;
            display: inline-block;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# ⚙️ CONSTANTS & CONFIGURATION (BACKEND)
# ==========================================
CHAT_MODEL = "gemini-3.5-flash-lite"

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

FORBIDDEN_WORDS = [
    "drop", "delete", "truncate", "alter", "update",
    "insert", "create", "replace", "grant", "revoke"
]

EXAMPLE_QUESTIONS = [
    "Top 10 artists by total stream count",
    "Average danceability and energy by genre",
    "Which genres have the highest viral ratio?",
    "Top 5 most popular tracks with high energy (> 0.8)",
    "Count of tracks per retention quadrant"
]

SCHEMA = """
Tables available in Snowflake (schema: MARTS). Use bare table names, no database or schema prefix.

1. MART_INDEPENDENT_ARTIST_RETENTION (
    track_id, track_name, artist_name, label_name, genre,
    release_date, release_year, stream_count, popularity,
    popularity_tier, retention_quadrant, viral_ratio,
    tempo, danceability, energy, loudness, instrumentalness, is_vocal_driven
)
Note: This is the primary table for track-level and artist-level queries.

2. MART_AUDIO_FEATURE_VIRALITY_BENCHMARKS (
    genre, retention_quadrant, total_tracks, avg_streams, avg_popularity,
    avg_danceability, avg_energy, avg_tempo_bpm, avg_loudness_db
)
Note: Use this table for high-level genre or quadrant benchmarks and averages.

3. FCT_TRACKS (
    track_id, track_name, stream_count, popularity,
    danceability, energy, tempo, loudness, viral_ratio, retention_quadrant
)
"""

SYSTEM_PROMPT = f"""
You are an expert Snowflake SQL analyst. Write ONE valid SELECT query that accurately answers the user's question.

Rules:
- SELECT queries only, never modify data.
- Use bare table names (e.g. MART_INDEPENDENT_ARTIST_RETENTION, not SPOTIFY_TI_DB.MARTS.MART_INDEPENDENT_ARTIST_RETENTION).
- Prefer MART_INDEPENDENT_ARTIST_RETENTION for artist and track questions.
- Prefer MART_AUDIO_FEATURE_VIRALITY_BENCHMARKS for genre-level aggregations.
- Add a LIMIT of 50, unless the user specifically asks for a single aggregate count/total.
- Return ONLY valid JSON in this exact structure: {{"sql": "your SQL query here"}}
- Allow READ queries ONLY (no drop, truncate, insert, etc... )

{SCHEMA}
"""


# ==========================================
# 🧠 BACKEND FUNCTIONS (UNCHANGED)
# ==========================================

def generate_sql(question: str) -> str:
    prompt = f"""
    {SYSTEM_PROMPT}

    User Query/Question:
    {question}
    """

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=prompt,
        config={"response_mime_type": "application/json"}
    )

    data = json.loads(response.text)
    sql = data["sql"]

    sql = sql.replace("SPOTIFY_TI_DB.MARTS.", "").replace("MARTS.", "")
    return sql.strip().rstrip(";")


def is_safe(sql: str) -> bool:
    lowered = sql.lower().strip()

    if not lowered.startswith("select") and not lowered.startswith("with"):
        return False

    for word in FORBIDDEN_WORDS:
        if f"{word}" in f"{lowered}":
            return False

    return True


@st.cache_resource
def get_connection():
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema="MARTS",  # Connect directly to MARTS schema where our tables live
        role=os.getenv("SNOWFLAKE_ROLE"),
    )


def run_query(sql: str) -> pd.DataFrame:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(sql)
    df = cursor.fetch_pandas_all()

    df.columns = [col.lower() for col in df.columns]
    return df


# ==========================================
# 🚀 FRONTEND INTERFACE
# ==========================================

# 1. Sidebar with Navigation, Schema Guide & Sample Prompts
with st.sidebar:
    st.image("https://storage.googleapis.com/pr-newsroom-wp/1/2023/05/Spotify_Primary_Logo_RGB_Green.png", width=55)
    st.markdown("## 📊 **Spotify SQL Studio**")
    st.caption("Natural Language to Snowflake SQL Analytics Engine")

    st.divider()

    st.markdown("### 💡 Example Inquiries")
    if "user_query_input" not in st.session_state:
        st.session_state.user_query_input = ""

    for q in EXAMPLE_QUESTIONS:
        if st.button(f"🔍 {q}", use_container_width=True):
            st.session_state.user_query_input = q

    st.divider()

    with st.expander("📚 Available Mart Schema"):
        st.markdown(
            """
            - **`MART_INDEPENDENT_ARTIST_RETENTION`**  
              *Grain:* Track & Artist level  
              *Metrics:* Streams, virality, tempo, audio features.
            
            - **`MART_AUDIO_FEATURE_VIRALITY_BENCHMARKS`**  
              *Grain:* Genre & Retention quadrant  
              *Metrics:* Aggregated streams, benchmarks.
            
            - **`FCT_TRACKS`**  
              *Grain:* Fact table with audio characteristics.
            """
        )

    st.divider()
    st.markdown("### 🔒 Active Security")
    st.caption("🛡️ DDL/DML Guardrails: **Enabled**")
    st.caption("⚡ Direct Target Schema: **`MARTS`**")
    st.caption(f"🤖 LLM Model: `{CHAT_MODEL}`")


# 2. Main Hero Section
st.title("⚡ Spotify Text-to-SQL Analytics")
st.markdown(
    "Ask analytical questions about artists, genres, virality, and streams in plain English. "
    "Gemini generates clean Snowflake SQL, verifies security guardrails, and runs the query live."
)

st.write("")

# 3. Input Query Area
col_input, col_btn = st.columns([5, 1])
with col_input:
    question = st.text_input(
        "Enter your analytical question:",
        value=st.session_state.user_query_input,
        placeholder="e.g. Top 10 artists by total stream count, or average danceability by genre...",
        label_visibility="collapsed",
    )
with col_btn:
    submit_clicked = st.button("🚀 Run Query", type="primary", use_container_width=True)

# 4. Query Execution & Results Rendering
if question and (submit_clicked or question != ""):
    st.markdown("---")

    # Step 1: SQL Generation
    with st.spinner("🧠 Translating question into Snowflake SQL..."):
        sql = generate_sql(question)

    # Step 2: Safety Check
    safe = is_safe(sql)

    # Top Execution Status Banner
    st.markdown("### 📝 Generated Snowflake Query")
    st.code(sql, language="sql")

    col_status1, col_status2 = st.columns([1, 4])
    with col_status1:
        if safe:
            st.markdown('<span class="badge-safe">🛡️ Guardrail: PASSED</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="badge-danger">⛔ Guardrail: BLOCKED</span>', unsafe_allow_html=True)

    if not safe:
        st.error("⛔ Security Block: Destructive keywords or non-SELECT query detected. Execution aborted.")
    else:
        # Step 3: Run Live Query on Snowflake
        try:
            start_time = time.time()
            with st.spinner("⚡ Executing query on Snowflake warehouse..."):
                results_df = run_query(sql)
            elapsed = round(time.time() - start_time, 2)

            st.write("")
            st.markdown("### 📈 Query Results")

            # Metrics Row
            m_col1, m_col2, m_col3 = st.columns(3)
            with m_col1:
                st.markdown(
                    f'<div class="metric-card"><div class="metric-val">{len(results_df)}</div><div class="metric-lbl">Rows Returned</div></div>',
                    unsafe_allow_html=True,
                )
            with m_col2:
                st.markdown(
                    f'<div class="metric-card"><div class="metric-val">{len(results_df.columns)}</div><div class="metric-lbl">Columns</div></div>',
                    unsafe_allow_html=True,
                )
            with m_col3:
                st.markdown(
                    f'<div class="metric-card"><div class="metric-val">{elapsed}s</div><div class="metric-lbl">Execution Time</div></div>',
                    unsafe_allow_html=True,
                )

            st.write("")

            # Interactive Tabs: Table View & Auto-Visualization
            if results_df.empty:
                st.info("Query executed successfully, but returned 0 rows.")
            else:
                tab_table, tab_chart = st.tabs(["📋 Data Table", "📊 Visualization"])

                with tab_table:
                    st.dataframe(results_df, use_container_width=True, hide_index=True)

                    # Export to CSV
                    csv_data = results_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="📥 Download Results as CSV",
                        data=csv_data,
                        file_name="spotify_query_results.csv",
                        mime="text/csv",
                    )

                with tab_chart:
                    # Automatic visualization heuristic:
                    # Look for first string/categorical column as X and first numeric column as Y
                    text_cols = results_df.select_dtypes(include=["object", "string", "category"]).columns.tolist()
                    num_cols = results_df.select_dtypes(include=[np.number]).columns.tolist()

                    if text_cols and num_cols:
                        chart_x = text_cols[0]
                        chart_y = num_cols[0]
                        st.caption(f"Auto-plotted: `{chart_y}` grouped by `{chart_x}`")
                        chart_df = results_df.set_index(chart_x)[[chart_y]]
                        st.bar_chart(chart_df)
                    elif num_cols:
                        st.line_chart(results_df[num_cols])
                    else:
                        st.info("No numerical columns available to render a chart.")

        except Exception as e:
            st.error(f"❌ Snowflake Execution Error: {e}")
