/*

  BUSINESS RULES TO APPLY:



  1. Duration Standardization
     - Convert durationms into duration_seconds and duration_minutes.
     - Why: Makes track length human-readable to analyze retention patterns.

  2. Viral vs. Retention Ratio (Velocity & Engagement)
     - Calculate a ratio between stream_count and popularity (e.g. stream_count / popularity).
     - Remember to handle division by zero or nulls using nullif().

  3. Popularity Tiers
     - Bucket popularity (0-100) into categories (e.g. Low, Medium, High, Viral).
     - Why: Enables group comparisons between tiers.

  4. Energy-to-Danceability / Mood Cluster
     - Combine danceability and energy (e.g. high danceability + high energy flag or a mood score).
     - Why: Identifies algorithmic playlist clusters (e.g. party vs chill).

  5. Acoustic / Instrumental Profile Flag
     - Flag tracks as vocal-driven vs instrumental using instrumentalness.
     - Why: Vocals drive viral traction, instrumentals drive repeat study/focus retention.

  6. Tempo / Pace Brackets
     - Bucket tempo (BPM) into categories (e.g. Slow, Mid-Tempo, Fast).
     - Why: Tests how speed impacts virality vs steady repeat listening.

  7. Volume / Loudness Intensity Level
     - Bucket loudness (dB) into ranges (e.g. Quiet, Standard, Loud).
     - Why: Correlates commercial production loudness with algorithmic placement.
*/

with stg_track_info_deduped as (
    select * from {{ref('stg_track_info_deduped')}}
),
enriched as (

    select 
        *,

        case 
            when popularity >= 60 
                and stream_count >= percentile_cont(0.5) within group (order by stream_count) over () 
                then 'Algorithmic Retention'
            when popularity < 50 
                and stream_count >= percentile_cont(0.5) within group (order by stream_count) over () 
                then 'Viral Spike'
            when popularity >= 60 
                and stream_count < percentile_cont(0.5) within group (order by stream_count) over () 
                then 'Slow Burn'
            else 'Niche / Long Tail'
        end as retention_quadrant,


        ROUND(durationms / 60000, 2) as duration_minutes,
        durationms / 1000 as duration_seconds,
        stream_count / popularity as viral_ratio,
        
        case 
            when popularity >= 85 then 'Viral'
            when popularity >= 65 then 'High'
            when popularity >= 35 then 'Medium'
            else 'Low'
        end as popularity_tier, --divided into 3 sections

        danceability / energy as dance_energy_ratio,
        
        case
            when danceability >= 0.65 and energy >= 0.65 then 'Party / High Energy'
            when energy < 0.45 and danceability < 0.60 then 'Chill / Low Energy'
            when instrumentalness >= 0.50 then 'Acoustic / Introspective'
            when danceability >= 0.65 and energy < 0.65 then 'Groove / Danceable'
            else 'Balanced'
        end as mood_cluster,

        case
            when instrumentalness >= 65 then 'High'
            when instrumentalness >= 35 then 'Medium'
            else 'Low'
        end as instrumentalness_tier,

        case when instrumentalness < 20 then true else false
        end as is_vocal_driven,

        case
            when tempo < 90 then 'Slow'
            when tempo < 120 then 'Moderate'
            when tempo < 150 then 'Fast'
            else 'Very Fast'
        end as tempo_tier,

        case
            when loudness < -30 then 'Very Quiet'
            when loudness < -14 then 'Quiet'
            when loudness < -5 then 'Standard Range'
            else 'Loud'
        end as loudness_tier
        

    from stg_track_info_deduped

)
select * from enriched