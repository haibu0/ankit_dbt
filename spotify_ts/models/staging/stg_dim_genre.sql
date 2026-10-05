
with raw_dim_genre as (
    select * from {{source('SPOTIFY_TI_RAW', 'raw_dim_genre')}}
),

with