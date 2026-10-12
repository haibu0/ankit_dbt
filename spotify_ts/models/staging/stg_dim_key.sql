with raw_dim_key as (

    select * from {{source('SPOTIFY_TI_RAW','raw_dim_key')}}
),
cleaned as (

    select 
        case
            when try_cast(trim(key) as integer) between 0 and 11
            then try_cast(trim(key) as integer)
            else null
        end as key_id,

        case
            when upper(trim(key_name)) not in (
                'C',
                'C#',
                'DB',
                'D',
                'D#',
                'EB',
                'E',
                'F',
                'F#',
                'GB',
                'G',
                'G#',
                'AB',
                'A',
                'A#',
                'BB',
                'B'
            ) then null
        else upper(trim(key_name))
        end as key_name

    from raw_dim_key
    where key_id is not null
    qualify row_number() over (
        partition by key_id
        order by key_name 
    ) = 1
)
select * from cleaned