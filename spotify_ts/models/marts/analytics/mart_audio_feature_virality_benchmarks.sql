with fct_tracks as (
    select * from {{ ref('fct_tracks') }}
),

dim_labels as (
    select * from {{ ref('stg_dim_label') }}
),

dim_genres as (
    select * from {{ ref('stg_dim_genre') }}
),

dim_dates as (
    select * from {{ ref('stg_dim_date') }}
),

track_level_features as (
    select
        -- Grouping Dimensions
        coalesce(g.genre, 'Unclassified Genre') as genre,
        coalesce(f.retention_quadrant, 'Niche / Long Tail') as retention_quadrant,

        -- Measures & Metrics to Aggregate
        f.track_id,
        f.stream_count,
        f.popularity,
        f.danceability,
        f.energy,
        f.tempo,
        f.loudness,
        f.instrumentalness,
        f.is_vocal_driven,
        d.is_weekend_release

    from fct_tracks f
    left join dim_labels l on f.label_id = l.label_id
    left join dim_genres g on f.genre_id = g.genre_id
    left join dim_dates d on f.date_id = d.date_id
),

aggregated_benchmarks as (
    select
        -- Dimensional Grain
        genre,
        retention_quadrant,

        -- Volume & Popularity Benchmarks
        count(track_id) as total_tracks,
        round(avg(stream_count), 0) as avg_streams,
        round(avg(popularity), 1) as avg_popularity,

        -- Sonic / Audio Feature Benchmarks
        round(avg(danceability), 3) as avg_danceability,
        round(avg(energy), 3) as avg_energy,
        round(avg(tempo), 1) as avg_tempo_bpm,
        round(avg(loudness), 2) as avg_loudness_db,
        round(avg(instrumentalness), 3) as avg_instrumentalness,

        -- Behavioral & Release Distribution Metrics
        round(avg(case when is_vocal_driven then 1.0 else 0.0 end) * 100, 2) as vocal_driven_track_pct,
        round(avg(case when is_weekend_release then 1.0 else 0.0 end) * 100, 2) as weekend_release_pct

    from track_level_features
    group by
        genre,
        retention_quadrant
)

select * from aggregated_benchmarks
order by
    genre,
    total_tracks desc