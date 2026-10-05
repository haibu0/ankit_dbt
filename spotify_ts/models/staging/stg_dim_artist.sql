-- remove any unwanted chars before / after name.
-- Examine  artist names under 5 chars 
-- artist id should be > 0 and cast as int 

WITH raw_dim_artist as (
    -- schema, table
    select * from {{ source('SPOTIFY_TI_RAW', 'raw_dim_artist') }}
),

cleaned_dim_artist as (
    select
        case
            when try_cast(trim(artist_id) as int) < 0 then null
            else try_cast(trim(artist_id) as int)
        end as artist_id,

        case
            when
                not regexp_like(trim(artist_name), '.*[a-zA-Z0-9].*')
                or length(trim(artist_name)) <= 5
                -- or lower(trim(artist_name)) in ('N/A', '?', '-', 'null', 'nan')  // the only values under 5 chars
                then 'Unknown Artist'
            else
                initcap(
                    regexp_replace(
                        trim(artist_name), '(^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$)', ''
                    )
                )
        -- initcap could cause some minor issues with band names. ex. Ac/Dc
        end as artist_name
    from raw_dim_artist

)

select * from cleaned_dim_artist
