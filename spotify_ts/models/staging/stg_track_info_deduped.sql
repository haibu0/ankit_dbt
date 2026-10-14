with stg_track_parsed as (
    select * from {{ref("stg_track_info_parsed")}}

),
deduped as (

    select
        *
    from stg_track_parsed
    qualify row_number() over (
        partition by track_id
        order by
            date_id desc nulls last,
            stream_count desc nulls last,
            popularity desc nulls last 
    ) = 1
    -- most meaningful thresholds/tiebreakers (streamcount + popularity)
)
select * from deduped