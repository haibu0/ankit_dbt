with fct_tracks as (
    select * from {{ ref('fct_tracks') }}
),

dim_labels as (
    select * from {{ ref('stg_dim_label') }}
),

dim_artists as (
    select * from {{ ref('stg_dim_artist') }}
),

dim_genres as (
    select * from {{ ref('stg_dim_genre') }}
),

dim_dates as (
    select * from {{ ref('stg_dim_date') }}
),

mart_retention as (
    select
        -- Track & Artist Identification
        f.track_id,
        f.track_name,
        a.artist_name,

        -- Label Context & Indie Classification
        l.label as label_name,
        {# l.label_category,
        l.is_independent_label, #}

        -- Musical Context
        g.genre,

        -- Release Timing Context
        d.release_date,
        d.release_year,
        d.release_quarter,
        d.release_day_of_the_week,
        d.is_weekend_release,

        -- Performance & Retention Metrics
        f.stream_count,
        f.popularity,
        f.popularity_tier,
        f.retention_quadrant,
        f.viral_ratio,

        -- Audio Profile
        f.tempo,
        f.tempo_tier,
        f.danceability,
        f.energy,
        f.dance_energy_ratio,
        f.mood_cluster,
        f.loudness,
        f.loudness_tier,
        f.instrumentalness,
        f.is_vocal_driven

    from fct_tracks f
    left join dim_labels l on f.label_id = l.label_id
    left join dim_artists a on f.artist_id = a.artist_id
    left join dim_genres g on f.genre_id = g.genre_id
    left join dim_dates d on f.date_id = d.date_id
)

select * from mart_retention