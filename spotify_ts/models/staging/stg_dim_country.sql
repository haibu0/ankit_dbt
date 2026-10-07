
with raw_dim_country as
(
    select * from {{source('SPOTIFY_TI_RAW','raw_dim_country')}}
),
cleaned as(

    select
        case
            when try_cast(trim(country_id) as integer) < 0 then null
            else try_cast(trim(country_id) as integer)
        end as country_id,

        initcap(trim(regexp_replace(country, '[^A-Za-z ]', ''))) as country
    
    from raw_dim_country
)

select * from cleaned