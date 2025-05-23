-- Step 1: Get the current view definition
SELECT definition FROM pg_views WHERE viewname = 'upcoming_events';

-- Step 2: Drop the current view
DROP VIEW IF EXISTS public.upcoming_events;

-- Step 3: Recreate the view with SECURITY INVOKER (which is the default)
-- NOTE: Replace the following CREATE VIEW statement with the actual definition 
-- from the SELECT statement above, but WITHOUT the "SECURITY DEFINER" clause.
-- Example:
CREATE VIEW public.upcoming_events AS
  SELECT * FROM events 
  WHERE start > NOW() 
  ORDER BY start;

-- Step 4: Add appropriate RLS policies for the events table
-- This ensures that users can only see their own events
CREATE POLICY IF NOT EXISTS "Users can view their own events" 
  ON events FOR SELECT 
  USING (user_id = auth.uid() OR user_id IS NULL);

-- Step 5: Verify the view no longer has SECURITY DEFINER
SELECT viewname, definition 
FROM pg_views 
WHERE viewname = 'upcoming_events' 
  AND definition NOT LIKE '%SECURITY DEFINER%'; 