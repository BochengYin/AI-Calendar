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
3. Configure email auth:
   - Under "Email Auth," click "Email Templates"
   - Customize the Magic Link template:
     - From name: "AI Calendar"
     - From email: (use your email or keep default)
     - Subject: "Your AI Calendar Login Link"
     - Customize the template content with something like:
     ```html
     <h2>Magic Link</h2>
     <p>Follow this link to login:</p>
     <p><a href="{{ .ConfirmationURL }}">Log In</a></p>
     <p>Or copy and paste this URL into your browser:</p>
     <p>{{ .ConfirmationURL }}</p>
     <p style="color: #666; font-size: 14px; margin-top: 20px;">
       • This link will expire in 24 hours<br>
       • If you didn't request this email, you can safely ignore it
     </p>
     <p style="color: #666; font-size: 14px; margin-top: 30px;">
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

-- Create policy to restrict access to events by user_id
-- Users can only see their own events
CREATE POLICY events_user_policy 
ON events
FOR ALL
USING (auth.uid() = user_id);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update updated_at timestamp on row update
CREATE TRIGGER update_events_updated_at
BEFORE UPDATE ON events
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Create a view for upcoming events (not deleted)
CREATE OR REPLACE VIEW upcoming_events AS
SELECT *
FROM events
WHERE is_deleted = false
AND end > now()
ORDER BY start ASC;

-- Grant access to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON events TO authenticated;
GRANT SELECT ON upcoming_events TO authenticated;
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
5. Check your email for the magic link
6. Click the link to log in

### 2. Test Database Access
1. After logging in, create a calendar event using the chat
2. Verify the event appears in the calendar
3. You can also check the Supabase Table Editor to see if events are being saved with the correct user_id

### 3. Debug Common Issues
- Check browser console for any CORS errors
- Verify your environment variables match the keys from Supabase
- Ensure the SQL schema was executed correctly (check Tables section in Supabase)
- If you get authentication errors, check that your redirect URLs are set correctly

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