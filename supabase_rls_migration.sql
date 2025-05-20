-- Supabase RLS Implementation for AI Calendar
-- This migration applies best practices for Row Level Security

-- First, create the private schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS private;

-- Create the events table if it doesn't exist
CREATE TABLE IF NOT EXISTS events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT,
  start TIMESTAMPTZ NOT NULL,
  "end" TIMESTAMPTZ NOT NULL,
  allDay BOOLEAN DEFAULT FALSE,
  user_id UUID DEFAULT auth.uid(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes for columns used in RLS policies
CREATE INDEX IF NOT EXISTS idx_events_user_id ON events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_start ON events(start);

-- Enable Row Level Security
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view their own events" ON events;
DROP POLICY IF EXISTS "Users can insert their own events" ON events;
DROP POLICY IF EXISTS "Users can update their own events" ON events;
DROP POLICY IF EXISTS "Users can delete their own events" ON events;

-- Create optimized policies using RLS best practices
-- 1. Use SELECT to wrap auth.uid() calls
-- 2. Explicitly specify roles
-- 3. Use clear naming conventions

-- Policy for SELECT operations
CREATE POLICY "Users can view their own events"
ON events FOR SELECT
TO authenticated
USING (
  (SELECT auth.uid()) = user_id
);

-- Policy for INSERT operations
CREATE POLICY "Users can insert their own events"
ON events FOR INSERT
TO authenticated
WITH CHECK (
  (SELECT auth.uid()) = user_id
);

-- Policy for UPDATE operations
CREATE POLICY "Users can update their own events"
ON events FOR UPDATE
TO authenticated
USING (
  (SELECT auth.uid()) = user_id
)
WITH CHECK (
  (SELECT auth.uid()) = user_id
);

-- Policy for DELETE operations
CREATE POLICY "Users can delete their own events"
ON events FOR DELETE
TO authenticated
USING (
  (SELECT auth.uid()) = user_id
);

-- Create a security definer function to get events efficiently
CREATE OR REPLACE FUNCTION private.get_user_events(user_uuid UUID)
RETURNS SETOF events
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT *
  FROM events
  WHERE user_id = user_uuid
  ORDER BY start DESC;
$$;

-- Create a function to efficiently check if a user belongs to an event
CREATE OR REPLACE FUNCTION private.user_owns_event(event_id UUID, user_uuid UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1
    FROM events
    WHERE id = event_id AND user_id = user_uuid
  );
END;
$$;

-- Create a trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_timestamp ON events;
CREATE TRIGGER set_timestamp
BEFORE UPDATE ON events
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- Add public access policy (optional, only if needed)
-- This allows events to be viewed by unauthenticated users (anon)
-- CREATE POLICY "Public events are viewable by everyone"
-- ON events FOR SELECT
-- TO anon, authenticated
-- USING (
--   public = TRUE  -- You would need to add a "public" column to your events table
-- ); 