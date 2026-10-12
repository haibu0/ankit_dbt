
with raw_dim_genre as (
    select * from {{source('SPOTIFY_TI_RAW', 'raw_dim_genre')}}
),

cleaned as (
    select
        case
            when try_cast(trim(genre_id) as integer) < 0 then null
            else try_cast(trim(genre_id) as integer)
        end as genre_id,

        case
    when not regexp_like(trim(genre), '.*[a-zA-Z].*') then null
    else
        initcap(regexp_replace(
                trim(genre),
                '[^a-zA-Z &]+', ''))
        end as genre

    from raw_dim_genre
)

select *
from cleaned