
{# 
ids should be > 0 and cast as int
take care of duplicate ids

remove any unwanted chars before / after name.

examine names under 5 chars
Found:
N/A
null
?
-
nan
#}

with raw_dim_album as (
    select * from {{source('SPOTIFY_TI_RAW', 'raw_dim_album')}}

),
cleaned_dim_album as (

    select 
        case 
            when try_cast(trim(album_id)as int) < 0 then null
            else try_cast(trim(album_id)as int)
        end as album_id,

        case
            when
                not regexp_like(trim(album_name), '.*[a-zA-Z0-9].*')
                -- or length(trim(album_name)) <= 5 // the only values under 5 chars are below
                or lower(trim(album_name)) in ('N/A', '?', '-', 'null', 'nan')
                then 'Unknown Album'
            else
                regexp_replace(
                    trim(album_name), '(^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$)', ''
                )
        end as album_name
    from raw_dim_album
),
deduped as (

    select 
        album_id,
        album_name
    from cleaned_dim_album
    qualify row_number() over (
            partition by album_id
            order by case when album_name = 'Unknown Album' then 2 else 1 end, length(album_name) desc
        ) = 1  
),
final as (
    select album_id, album_name
    from deduped
)

select * from final