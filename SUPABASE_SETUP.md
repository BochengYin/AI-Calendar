# Supabase Setup Guide for AI Calendar

This guide walks you through setting up Supabase for authentication and database functionality with the AI Calendar application.

## 1. Create a Supabase Project

1. Sign up or log in at [Supabase](https://app.supabase.io/)
2. Click "New Project"
3. Name your project (e.g., "AI Calendar")
4. Set a secure database password
5. Choose a region close to your users
6. Click "Create New Project"

## 2. Configure Authentication

1. In your Supabase dashboard, go to "Authentication" → "Providers"
2. Ensure "Email" provider is enabled
3. In Email Settings, make sure "Enable Email Confirmations" is turned ON
4. Configure Email Templates:
   - Under "Email Auth," click "Email Templates"
   - Customize the "Confirmation" template (used for OTP):
     - From name: "AI Calendar"
     - From email: (use your email or keep default)
     - Subject: "Your AI Calendar Verification Code"
     - Customize the template content with something like:
     ```html
     <h2 style="color: #333; font-family: Arial, sans-serif;">AI Calendar Verification</h2>
     <p style="font-family: Arial, sans-serif; color: #444;">Your verification code for AI Calendar is:</p>
     
     <div style="margin: 30px 0; padding: 20px; background-color: #f7f9fc; border-radius: 6px; text-align: center;">
       <h1 style="font-family: monospace; font-size: 32px; letter-spacing: 5px; color: #007AFF;">{{ .Token }}</h1>
     </div>
     
     <p style="font-family: Arial, sans-serif; color: #444;">Enter this code in the verification screen to complete your login.</p>
     
     <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-family: Arial, sans-serif; color: #666; font-size: 14px;">
       <p>• This code will expire in 60 minutes</p>
       <p>• If you didn't request this code, you can safely ignore this email</p>
     </div>
     
     <p style="text-align: center; margin-top: 30px; font-family: Arial, sans-serif; color: #999;">
       Powered by 🐱 AI Calendar
     </p>
     ```

## 3. Configure URL Settings (CORS & Redirects)

1. Go to "Authentication" → "URL Configuration"
2. Set "Site URL" to your development URL (e.g., `http://localhost:3000`)
3. Under "Redirect URLs", click "Add URL" and add:
   - Your production domain (e.g., `https://ai-calendar-bochengyin.vercel.app`)
   
Note: In newer versions of Supabase, CORS is automatically configured based on your Site URL and Redirect URLs. There is no longer a separate CORS configuration section.

## 4. Set Up Database Schema

1. Go to "SQL Editor" in your Supabase dashboard
2. Create a new query
3. Copy and paste the following SQL schema (or the contents of `backend/schema.sql`):

```sql
-- Create events table with Row Level Security
CREATE TABLE IF NOT EXISTS events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  title TEXT NOT NULL,
  start TIMESTAMPTZ NOT NULL,
  "end" TIMESTAMPTZ NOT NULL,
  all_day BOOLEAN DEFAULT false,
  description TEXT,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  user_email TEXT NOT NULL,
  is_deleted BOOLEAN DEFAULT false,
  is_rescheduled BOOLEAN DEFAULT false,
  rescheduled_from UUID REFERENCES events(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Enable Row Level Security
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- Users can SELECT their own rows
CREATE POLICY events_select_policy
  ON events FOR SELECT TO authenticated
  USING ((SELECT auth.uid()) = user_id);

-- Users can INSERT rows for themselves
CREATE POLICY events_insert_policy
  ON events FOR INSERT TO authenticated
  WITH CHECK ((SELECT auth.uid()) = user_id);

-- Users can UPDATE their own rows
CREATE POLICY events_update_policy
  ON events FOR UPDATE TO authenticated
  USING ((SELECT auth.uid()) = user_id)
  WITH CHECK ((SELECT auth.uid()) = user_id);

-- Users can DELETE their own rows (soft-delete is preferred)
CREATE POLICY events_delete_policy
  ON events FOR DELETE TO authenticated
  USING ((SELECT auth.uid()) = user_id);

-- Drop and recreate upcoming_events without SECURITY DEFINER
DROP VIEW IF EXISTS public.upcoming_events;
CREATE VIEW public.upcoming_events AS
SELECT id, title, start, "end", all_day, description,
       user_id, user_email, is_deleted, is_rescheduled,
       rescheduled_from, created_at, updated_at
FROM events
WHERE is_deleted = false AND "end" > now()
ORDER BY start;

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_events_updated_at ON events;
CREATE TRIGGER update_events_updated_at
BEFORE UPDATE ON events
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Grant privileges to the Authenticated role
GRANT SELECT, INSERT, UPDATE, DELETE ON events TO authenticated;
GRANT SELECT ON public.upcoming_events TO authenticated;
```

Note: Make sure to use double quotes around the "end" column name as it's a reserved word in SQL.

## 5. Get API Credentials

1. Go to "Project Settings" → "API"
2. Copy the following:
   - URL: Your project URL (e.g., `https://xyzproject.supabase.co`)
   - anon/public key: For frontend authentication
   - service_role key: For backend operations (keep this secret!)

## 6. Configure Environment Variables

### Frontend (.env.development and .env.production):
```
REACT_APP_API_URL=http://localhost:8000  # Or your backend URL for production
REACT_APP_SUPABASE_URL=your-project-url
REACT_APP_SUPABASE_ANON_KEY=your-anon-key
```

### Backend (.env):
```
OPENAI_API_KEY=your-openai-api-key
SUPABASE_URL=your-project-url
SUPABASE_KEY=your-service-role-key
```

## 7. Email Sending (Optional for Production)

For production, you can use Supabase's default email service (limited to 10 emails/hour on free tier) or set up a custom SMTP provider:

1. Go to "Authentication" → "Email Templates"
2. Under "SMTP Settings," click "Enable custom SMTP"
3. Configure with your SMTP provider details (SendGrid, Mailgun, etc.)
4. Test the configuration

## 8. Testing Your Setup

### 1. Test Authentication
1. Start your frontend and backend servers
2. Open your app in the browser
3. You should see the login screen
4. Enter your email address
5. Check your email for the verification code
6. Enter the code in your app to log in

### 2. Test Database Access
1. After logging in, create a calendar event using the chat
2. Verify the event appears in the calendar
3. You can also check the Supabase Table Editor to see if events are being saved with the correct user_id

### 3. Debug Common Issues
- Check browser console for any CORS errors
- Verify your environment variables match the keys from Supabase
- Ensure the SQL schema was executed correctly (check Tables section in Supabase)
- If you get authentication errors, check that your redirect URLs are set correctly
- For OTP issues, ensure "Enable Email Confirmations" is enabled in Authentication settings

## Security Best Practices

1. **Never commit API keys to your repository**
2. Keep service_role key secure and only use it in the backend
3. Set up Row Level Security (already included in the schema.sql)
4. Regularly rotate API keys for production

## Recommended Extensions

Consider installing these useful Supabase extensions:

1. **pgvector**: For AI embeddings if you want to extend functionality
   ```sql
   create extension vector with schema public;
   ```

2. **pg_cron**: For scheduled tasks
   ```sql
   create extension pg_cron with schema public;
   ``` 