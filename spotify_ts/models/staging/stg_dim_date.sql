with raw_dim_date as (
    select * from {{source('SPOTIFY_TI_RAW', 'raw_dim_date')}}

),

parsed as (
    select 

        case
            when try_cast(trim(date_id) as int) < 0 then null
            else try_cast(trim(date_id) as int)
        end as date_id,

        try_cast(trim(release_date) as date) as release_date
    from raw_dim_date
    

),

cleaned as (
    
    select 

        date_id,
        release_date,

        year(release_date) as release_year,
        quarter(release_date) as release_quarter,
        month(release_date) as release_month,
        monthname(release_date) as release_month_name,
        day(release_date) as release_day,
        dayname(release_date) as release_day_of_the_week,

        case
            when 
                dayname(release_date) not in ('Sat', 'Sun') then false
                else true
            end as is_weekend_release

    from parsed
    where date_id is not null
    qualify row_number() over (
        partition by date_id
        order by case when release_date is not null then 1 else 2 end
    ) = 1



)

select * from cleaned;
