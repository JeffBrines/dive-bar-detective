
create table public.reviews (
  id uuid primary key default gen_random_uuid(),
  place_id text references public.locations(place_id) on delete cascade,
  review_text text,
  rating integer,
  author_name text,
  review_timestamp timestamp with time zone,
  review_language text,
  sentiment_score float,
  created_at timestamp with time zone default now()
);

-- Index for fast lookups
create index reviews_place_id_idx on public.reviews (place_id);

