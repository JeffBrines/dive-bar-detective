-- Enable PostGIS if available (optional, but good for geo-queries)
-- create extension if not exists postgis;

create table public.locations (
  place_id text primary key,
  name text not null,
  address text,
  lat double precision,
  lng double precision,
  rating numeric,
  user_ratings_total integer,
  price_level integer,
  types text[],
  formatted_phone_number text,
  website text,
  created_at timestamp with time zone default now()
);

-- Index on rating for faster sorting
create index locations_rating_idx on public.locations (rating);

-- Index on price_level
create index locations_price_level_idx on public.locations (price_level);

