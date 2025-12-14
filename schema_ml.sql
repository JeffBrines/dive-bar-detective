
ALTER TABLE public.locations 
ADD COLUMN IF NOT EXISTS ml_metadata jsonb default '{}'::jsonb;

