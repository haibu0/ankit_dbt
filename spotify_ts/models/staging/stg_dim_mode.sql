with raw_dim_mode as (
    select * from {{source('SPOTIFY_TI_RAW', 'raw_dim_mode')}}
),
parsed as (
    select
        try_cast(trim(mode) as int) as mode_id
    from raw_dim_mode
),

cleaned as (

    select

        mode_id,

        case when mode_id = 0 then 'Minor'
             when mode_id = 1 then 'Major'
             else null
        end as mode_name

    from parsed

    qualify row_number() over (
        partition by mode_id order by mode_name
    ) = 1

)

select * from cleaned