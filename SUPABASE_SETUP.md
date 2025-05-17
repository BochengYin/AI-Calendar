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
     - Customize the template content as needed

## 3. Set Up Database Schema

1. Go to "SQL Editor" in your Supabase dashboard
2. Create a new query
3. Copy and paste the contents of `backend/schema.sql` from this project
4. Click "Run" to execute the SQL

## 4. Get API Credentials

1. Go to "Project Settings" → "API"
2. Copy the following:
   - URL: Your project URL (e.g., `https://xyzproject.supabase.co`)
   - anon/public key: For frontend authentication
   - service_role key: For backend operations (keep this secret!)

## 5. Configure Environment Variables

### Frontend (.env.development and .env.production):
```
REACT_APP_SUPABASE_URL=your-project-url
REACT_APP_SUPABASE_ANON_KEY=your-anon-key
```

### Backend (.env):
```
SUPABASE_URL=your-project-url
SUPABASE_KEY=your-service-role-key
```

## 6. Enable Email Sending (for production)

For production, set up email sending:

1. Go to "Authentication" → "Email Templates"
2. Under "SMTP Settings," click "Enable custom SMTP"
3. Configure with your SMTP provider details (like SendGrid, Mailgun, etc.)
4. Test the configuration

## 7. CORS Configuration

1. Go to "Project Settings" → "API" → "CORS"
2. Add your origins:
   - `http://localhost:3000` (for development)
   - Your production domain (e.g., `https://ai-calendar-nine.vercel.app`)

## Security Best Practices

1. **Never commit API keys to your repository**
2. Keep service_role key secure and only use it in the backend
3. Set up Row Level Security (already included in the schema.sql)
4. Regularly rotate API keys for production

## Debugging Authentication

If you encounter issues with authentication:

1. Check browser console for errors
2. Verify environment variables are correct
3. Ensure CORS is configured properly
4. Check Supabase logs in "Database" → "Logs"

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