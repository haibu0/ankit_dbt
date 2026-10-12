
with raw_dim_label as
(
    select * from {{source('SPOTIFY_TI_RAW','raw_dim_label')}}
),
cleaned as(

    select
        case
            when try_cast(trim(label_id) as integer) < 0 then null
            else try_cast(trim(label_id) as integer)
        end as label_id,

        initcap(trim(regexp_replace(label, '[^A-Za-z ]', ''))) as label
    
    from raw_dim_label
)

select * from cleaned