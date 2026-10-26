import os
import json
import snowflake.connector
from google import genai
from google.genai import types
from dotenv import load_dotenv
from google.auth import default


load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
model = "gemini-3.5-flash-lite"

sample_size = 5


system_prompt = """
You are an expert music metadata classifier.
Analyze the provided track's audio and streaming features to infer its qualitative metadata.

Field Interpretation Rules:
1. primary_mood: Base this on energy, danceability, loudness, and mood_cluster.
2. playlist_contexts: Base this on tempo, instrumentalness, and duration (e.g., high instrumentalness = Focus/Study; high tempo + energy = Workout; low loudness + long duration = Late Night Drive).
3. micro_genre: Refine the base genre using tempo, instrumentalness, and danceability.
4. vibe_keywords: 3-5 sensory/aesthetic tags (e.g., "atmospheric", "hypnotic", "punchy bass").
5. target_audience: Base this on retention_quadrant, viral_ratio, and is_explicit.

Return ONLY a valid JSON object matching this structure:
{
  "track_id": "string",
  "primary_mood": "string",
  "playlist_contexts": ["string", "string"],
  "micro_genre": "string",
  "vibe_keywords": ["string", "string", "string"],
  "target_audience": "string"
}
"""


def get_connection():
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE"),
    )


def create_output_table(cursor):
    cursor.execute("CREATE SCHEMA IF NOT EXISTS SPOTIFY_TI_DB.AI")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS SPOTIFY_TI_DB.AI.TRACKS_AI_ENRICHED (
            track_id VARCHAR(64) PRIMARY KEY,
            primary_mood VARCHAR(255),
            playlist_contexts VARCHAR(500),
            micro_genre VARCHAR(255),
            vibe_keywords VARCHAR(500),
            target_audience VARCHAR(255),
            raw_response VARIANT,
            enriched_at TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP()
        );
    """)


def get_tracks_to_enrich(cursor):
    query = f"""
        SELECT 
            f.track_id,
            f.track_name,
            coalesce(g.genre, 'Unknown') as genre,
            f.tempo,
            f.danceability,
            f.energy,
            f.loudness,
            f.instrumentalness,
            f.duration_minutes,
            f.is_explicit,
            f.mood_cluster,
            f.retention_quadrant,
            f.viral_ratio
        FROM spotify_ti_db.marts.fct_tracks f
        LEFT JOIN spotify_ti_db.staging.stg_dim_genre g ON f.genre_id = g.genre_id
        LEFT JOIN spotify_ti_db.ai.tracks_ai_enriched e ON f.track_id = e.track_id
        WHERE e.track_id IS NULL
        LIMIT {sample_size};
    """
    cursor.execute(query)
    columns = [col[0].lower() for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def classify_track(track_info):
    response = client.models.generate_content(
        model=model,
        contents=json.dumps(track_info, default=float),
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            temperature=0,
        ),
    )
    return json.loads(response.text)


def save_results(cursor, results):
    # Convert dicts into tuples matching the 7 columns:
    # (track_id, primary_mood, playlist_contexts, micro_genre, vibe_keywords, target_audience, raw_response)
    data_to_insert = [
        (
            item.get("track_id"),
            item.get("primary_mood"),
            json.dumps(item.get("playlist_contexts", [])),
            item.get("micro_genre"),
            json.dumps(item.get("vibe_keywords", [])),
            item.get("target_audience"),
            json.dumps(item),
        )
        for item in results
    ]

    cursor.executemany("""
        INSERT INTO SPOTIFY_TI_DB.AI.TRACKS_AI_ENRICHED (
            track_id,
            primary_mood,
            playlist_contexts,
            micro_genre,
            vibe_keywords,
            target_audience,
            raw_response
        )
        SELECT
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            PARSE_JSON(%s)
    """, data_to_insert)


def main():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        create_output_table(cursor)
        tracks_to_enrich = get_tracks_to_enrich(cursor)
        if not tracks_to_enrich:
            print("No tracks to enrich")
            return

        print(f"Enriching {len(tracks_to_enrich)} tracks...")

        results = []
        for track in tracks_to_enrich:
            try:
                ai_output = classify_track(track)
                ai_output["track_id"] = track["track_id"]
                results.append(ai_output)
                print(f"Enriched: {track.get('track_name')} ({track['track_id']})")
            except Exception as e:
                print(f"Error enriching track {track['track_id']}: {e}")

        if results:
            save_results(cursor, results)
            conn.commit()
            print(f"Successfully saved {len(results)} tracks.")

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()