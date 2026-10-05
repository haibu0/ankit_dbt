

WITH spotify_ti_raw as (
    select * from {{ source('SPOTIFY_TI_RAW', 'raw_fact_track') }}  -- schema, table

),
parsed as
(
    select 
        case
            when upper(trim(track_id)) not like 'TRK-%'
                then 'TRK-' || upper(trim(track_id))
            else upper(trim(track_id))
        end as track_id,
        
        initcap(trim(track_name)) as track_name,
        
        case
            when try_cast(trim(artist_id) as integer) < 0 then null
            else try_cast(trim(artist_id) as integer)
        end as artist_id,

        case
            when try_cast(trim(album_id) as integer) < 0 then null
            else try_cast(trim(album_id) as integer)
        end as album_id,

        case
            when try_cast(trim(genre_id) as integer) < 0 then null
            else try_cast(trim(genre_id) as integer)
        end as genre_id,
        
        case
            when try_cast(trim(country_id) as integer) < 0 then null
            else try_cast(trim(country_id) as integer)
        end as country_id,

        case
            when try_cast(trim(label_id) as integer) < 0 then null
            else try_cast(trim(label_id) as integer)
        end as label_id,

        case
            when try_cast(trim(date_id) as integer) < 0 then null
            else try_cast(trim(date_id) as integer)
        end as date_id,

        case
            when try_cast(trim(key) as integer) < 0 then null
            else try_cast(trim(key) as integer)
        end as key,

        case
            when try_cast(trim(mode) as integer) NOT IN (0, 1) then null
            else try_cast(trim(mode) as integer)
        end as mode,

        case
            when try_cast(trim(duration_ms) as integer) < 0 then null
            else try_cast(trim(duration_ms) as integer)
        end as durationms,

        case
            when try_cast(trim(popularity) as integer) < 0 then null
            else try_cast(trim(popularity) as integer)
        end as popularity,

        case
            WHEN trim(stream_count) LIKE '%K' THEN TRY_CAST(REPLACE(trim(stream_count), 'K', '') AS DECIMAL(10,2)) * 1000
            when try_cast(trim(stream_count) as integer) < 0 then null
            else try_cast(trim(stream_count) as integer)
        end as stream_count,

        case
            when try_cast(trim(danceability) as float) < 0 then null
            else try_cast(trim(danceability) as float)
        end as danceability,

        case
            when try_cast(trim(energy) as float) < 0 then null
            else try_cast(trim(energy) as float)
        end as energy,

        try_cast(trim(loudness) as float) as loudness,

        case
            when try_cast(trim(instrumentalness) as float) < 0 then null
            else try_cast(trim(instrumentalness) as float)
        end as instrumentalness,

        case
            when try_cast(replace(trim(tempo), ' bpm', '') as float) < 0 then null
            else try_cast(trim(tempo) as float)
        end as tempo,


        case
            when try_cast(trim(explicit) as integer) = 1 then TRUE
            else FALSE
        end as is_explicit
    from spotify_ti_raw
)

select * from parsed


