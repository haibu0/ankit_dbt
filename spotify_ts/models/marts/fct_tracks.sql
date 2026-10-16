with enriched as (
    select * from {{ ref('stg_track_info_enriched') }}
)

select
    -- Primary Key
    track_id,
    track_name,

    -- Foreign Keys to Conformed Dimensions
    artist_id,
    album_id,
    label_id,
    genre_id,
    country_id,
    date_id,
    key as key_id,
    mode as mode_id,

    -- Core Measures
    stream_count,
    popularity,
    durationms,
    duration_seconds,
    duration_minutes,

    -- Acoustic / Audio Features
    danceability,
    energy,
    loudness,
    instrumentalness,
    tempo,
    is_explicit,

    -- Derived Metrics & Classifications
    viral_ratio,
    popularity_tier,
    retention_quadrant,
    dance_energy_ratio,
    mood_cluster,
    instrumentalness_tier,
    is_vocal_driven,
    tempo_tier,
    loudness_tier

from enriched