import os
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
    page_title="Spotify AI Music Assistant",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern Spotify-themed look and feel
st.markdown(
    """
    <style>
        /* Main background and accent accents */
        .stApp {
            background-color: #121212;
            color: #FFFFFF;
        }
        
        /* Headers */
        h1, h2, h3 {
            color: #FFFFFF !important;
            font-weight: 700 !important;
        }
        
        /* Card container */
        .track-card {
            background: linear-gradient(145deg, #181818 0%, #202020 100%);
            border: 1px solid #2e2e2e;
            border-left: 4px solid #1DB954;
            border-radius: 10px;
            padding: 16px 20px;
            margin-bottom: 14px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
            transition: all 0.2s ease-in-out;
        }
        .track-card:hover {
            border-color: #1DB954;
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(29, 185, 84, 0.15);
        }
        
        /* Badges */
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 14px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-right: 6px;
            margin-top: 4px;
        }
        .badge-genre {
            background-color: rgba(29, 185, 84, 0.15);
            color: #1DB954;
            border: 1px solid rgba(29, 185, 84, 0.4);
        }
        .badge-metric {
            background-color: #282828;
            color: #d1d1d1;
            border: 1px solid #3d3d3d;
        }
        .badge-score {
            background-color: #1DB954;
            color: #000000;
            font-weight: 700;
        }
        
        /* AI Response block */
        .ai-response-box {
            background: linear-gradient(135deg, #1a241e 0%, #161b17 100%);
            border: 1px solid #1DB954;
            border-radius: 12px;
            padding: 22px;
            margin: 18px 0 26px 0;
            box-shadow: 0 6px 18px rgba(0,0,0,0.3);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# ⚙️ CONSTANTS & CONFIGURATION (BACKEND)
# ==========================================
EMBEDDING_MODEL = "gemini-embedding-001"
CHAT_MODEL = "gemini-3.5-flash-lite"
NUM_TRACKS = 500
TOP_K = 5
CACHE_FILE = "spotify_track_embeddings.parquet"
SAMPLE = 50

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# ==========================================
# 🧠 BACKEND FUNCTIONS (UNCHANGED LOGIC)
# ==========================================

def read_track_info_from_snowflake(sample_size=SAMPLE):
    conn = snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE"),
    )

    query = f"""
    SELECT 
        track_id,
        track_name,
        artist_name,
        genre,
        tempo,
        danceability,
        energy,
        loudness,
        retention_quadrant,
        viral_ratio
    FROM spotify_ti_db.marts.mart_independent_artist_retention
    SAMPLE ({sample_size} ROWS)
    """

    df = conn.cursor().execute(query).fetch_pandas_all()
    conn.close()

    # standardizing columns to lowercase
    df.columns = [col.lower() for col in df.columns]
    return df


def build_track_text(row):
    return (
        f"Track: {row['track_name']} by Artist: {row['artist_name']}. "
        f"Genre: {row.get('genre', 'Unknown')}. "
        f"Tempo: {row.get('tempo', 'N/A')} BPM, "
        f"Danceability: {row.get('danceability', 'N/A')}, "
        f"Energy: {row.get('energy', 'N/A')}. "
        f"Category: {row.get('retention_quadrant', 'Standard')}."
    )


def embed_text(text: str):
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
    )
    # response.embeddings[0].values is a list of floats (the vector)
    return response.embeddings[0].values


def embed_tracks(texts: list[str]):
    embeddings = []
    for text in texts:
        embeddings.append(embed_text(text))
    return embeddings


@st.cache_data
def load_and_embed_tracks():
    # if parquet file is saved, load it
    if os.path.exists(CACHE_FILE):
        return pd.read_parquet(CACHE_FILE)

    # 2. Fetch fresh tracks from Snowflake
    df = read_track_info_from_snowflake(sample_size=SAMPLE)
    # 3. Create the text summary for each row (our text bridge from Step 3)
    df["text_summary"] = df.apply(build_track_text, axis=1)
    # 4. Convert every track summary into a 768-dimension vector
    df["embedding"] = embed_tracks(df["text_summary"].tolist())

    # 5. Save to disk so we never have to do this again
    df.to_parquet(CACHE_FILE)

    return df


def cosine_similarity(vec_a, vec_b):
    # calculate the cosine similarity between 2 vectors    
    vec_a = np.array(vec_a)
    vec_b = np.array(vec_b)
    return np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))


def find_similar_tracks(question: str, df: pd.DataFrame, top_k: int = TOP_K):
    # turn the users question into a vector
    question_vector = embed_text(question)

    scores = []
    # compare the question vector against every track in our table
    for track_vector in df["embedding"]:
        scores.append(cosine_similarity(question_vector, track_vector))

    # copy df into df_scored, and add a new column, similarity_score
    df_scored = df.copy()
    df_scored["similarity_score"] = scores

    # returns top-k highest values in similarity_score column
    return df_scored.nlargest(top_k, "similarity_score")


def ask_gemini(question: str, top_tracks: pd.DataFrame) -> str:
    # 1. Format the retrieved tracks into context text
    context = ""
    for _, row in top_tracks.iterrows():
        context += (
            f"- {row['track_name']} by {row['artist_name']} "
            f"(Genre: {row.get('genre', 'N/A')}, "
            f"Energy: {row.get('energy', 'N/A')}, "
            f"Tempo: {row.get('tempo', 'N/A')} BPM)\n"
        )
    prompt = f"""
    You are a helpful Spotify Music Assistant.
    Answer the user's question using ONLY the provided tracks below.
    Be concise, enthusiastic, and explain WHY these tracks match what the user is looking for.
    If the tracks do not match or cannot answer the question, clearly state that.
    User Question:
    {question}
    Available Track Matches:
    {context}
    """

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=prompt,
    )
    return response.text


# ==========================================
# 🚀 FRONTEND INTERFACE
# ==========================================

# 1. Load cached track dataset
with st.spinner("Loading music knowledge base..."):
    tracks_df = load_and_embed_tracks()

# 2. Sidebar Navigation & Statistics
with st.sidebar:
    st.image("https://storage.googleapis.com/pr-newsroom-wp/1/2023/05/Spotify_Primary_Logo_RGB_Green.png", width=60)
    st.markdown("## 🎵 **Spotify RAG Engine**")
    st.caption("Retrieval-Augmented Generation using Snowflake & Google Gemini.")
    
    st.divider()
    
    st.markdown("### 📊 Catalog Overview")
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Indexed Tracks", len(tracks_df))
    with col_b:
        unique_genres = tracks_df["genre"].nunique() if "genre" in tracks_df.columns else 0
        st.metric("Genres", unique_genres)
        
    st.divider()

    st.markdown("### 💡 Quick Prompt Suggestions")
    suggestions = [
        "⚡ High-energy workout tracks",
        "💃 Upbeat dance party vibes",
        "🌙 Late-night slow acoustic",
        "🧘 Calm focus and low tempo",
    ]
    
    # Initialize prompt state if needed
    if "selected_query" not in st.session_state:
        st.session_state.selected_query = ""

    for s in suggestions:
        if st.button(s, use_container_width=True):
            st.session_state.selected_query = s.split(" ", 1)[1]

    st.divider()
    st.markdown("### ⚙️ System Specs")
    st.caption(f"**Embedding Model:** `{EMBEDDING_MODEL}`")
    st.caption(f"**Chat Model:** `{CHAT_MODEL}`")
    st.caption(f"**Similarity Metric:** Cosine Similarity")


# 3. Main Header & Hero Section
st.title("🎧 Spotify Music AI Assistant")
st.markdown(
    "Ask any question about moods, artists, genres, or audio characteristics. "
    "Our semantic vector engine finds the most relevant tracks from **Snowflake** "
    "and **Gemini** analyzes why they fit your request."
)

st.write("")

# 4. Search Bar & Query Input
col_input, col_btn = st.columns([5, 1])
with col_input:
    user_question = st.text_input(
        "Enter your musical query:",
        value=st.session_state.selected_query,
        placeholder="e.g., Recommend upbeat high-energy dance tracks, or slow acoustic melodies...",
        label_visibility="collapsed",
    )
with col_btn:
    search_clicked = st.button("🔍 Search", type="primary", use_container_width=True)

# 5. Search Execution & Display
if user_question and (search_clicked or user_question != ""):
    st.markdown("---")
    
    with st.spinner("🔎 Searching vector embeddings & asking Gemini..."):
        # Retrieve top matches
        top_matches = find_similar_tracks(question=user_question, df=tracks_df, top_k=TOP_K)
        # Generate LLM answer
        answer = ask_gemini(user_question, top_matches)

    # 5.1 AI Recommendation Card
    st.markdown("### 🤖 Music Assistant Recommendation")
    st.markdown(f'<div class="ai-response-box">{answer}</div>', unsafe_allow_html=True)

    # 5.2 Visual Track Match Cards
    st.markdown("### 🎶 Top Matching Tracks Retrieved")
    
    card_cols = st.columns(min(len(top_matches), 3))
    for idx, (_, row) in enumerate(top_matches.iterrows()):
        col_target = card_cols[idx % 3]
        sim_pct = round(row["similarity_score"] * 100, 1)
        tempo_val = round(row.get("tempo", 0)) if pd.notnull(row.get("tempo")) else "N/A"
        energy_val = round(row.get("energy", 0) * 100) if pd.notnull(row.get("energy")) else "N/A"
        
        with col_target:
            st.markdown(
                f"""
                <div class="track-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <h4 style="margin: 0; color: #FFFFFF; font-size: 1.05rem;">{row['track_name']}</h4>
                        <span class="badge badge-score">{sim_pct}% Match</span>
                    </div>
                    <p style="margin: 4px 0 10px 0; color: #B3B3B3; font-size: 0.9rem;">by <strong style="color: #FFFFFF;">{row['artist_name']}</strong></p>
                    <div style="margin-top: 8px;">
                        <span class="badge badge-genre">{row.get('genre', 'Unknown')}</span>
                        <span class="badge badge-metric">⚡ {energy_val}% Energy</span>
                        <span class="badge badge-metric">🥁 {tempo_val} BPM</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # 5.3 Detailed Data Table in Expander
    st.write("")
    with st.expander("🔍 View Raw Ground-Truth Data from Snowflake"):
        display_cols = ["track_name", "artist_name", "genre", "tempo", "energy", "danceability", "similarity_score"]
        available_cols = [c for c in display_cols if c in top_matches.columns]
        
        st.dataframe(
            top_matches[available_cols],
            column_config={
                "track_name": "Track Title",
                "artist_name": "Artist",
                "genre": "Genre",
                "tempo": st.column_config.NumberColumn("Tempo (BPM)", format="%.0f"),
                "energy": st.column_config.ProgressColumn("Energy", min_value=0, max_value=1, format="%.2f"),
                "danceability": st.column_config.ProgressColumn("Danceability", min_value=0, max_value=1, format="%.2f"),
                "similarity_score": st.column_config.ProgressColumn("Match Score", min_value=0, max_value=1, format="%.2f"),
            },
            hide_index=True,
            use_container_width=True,
        )
