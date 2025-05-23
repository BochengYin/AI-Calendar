import { createClient } from '@supabase/supabase-js';

// Initialize the Supabase client
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL || "https://ssyhnabptfcxsyydexfc.supabase.co";
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY;

// For test environment, provide fallback values to prevent errors
const isTestEnvironment = process.env.NODE_ENV === 'test';
const testFallbackKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNzeWhuYWJwdGZjeHN5eWRleGZjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDc0Njc4MzMsImV4cCI6MjA2MzA0MzgzM30.igJyoPiOZWxknXXWJOo2MrYfr6YnxpCmPSR-QpZLkO4';

// Log environment variables for debugging (URLs only, not keys) - but only in development
if (process.env.NODE_ENV === 'development') {
  console.log('Supabase URL being used:', supabaseUrl);
  console.log('API URL from env:', process.env.REACT_APP_API_URL);
  console.log('Node environment:', process.env.NODE_ENV);
  console.log('Anon key length:', supabaseAnonKey?.length || 0);
}

if (!supabaseUrl || !supabaseAnonKey) {
  if (!isTestEnvironment) {
    console.error('⚠️ Supabase URL or Anon Key not found. Authentication will not work.');
    console.error('Please make sure your environment variables are set correctly.');
    
    // For development environments, provide more detailed guidance
    if (process.env.NODE_ENV === 'development') {
      console.warn('Make sure you have .env.local file with REACT_APP_SUPABASE_URL and REACT_APP_SUPABASE_ANON_KEY');
    }
  }
}

// Use fallback values for tests to prevent errors
const finalAnonKey = supabaseAnonKey || (isTestEnvironment ? testFallbackKey : '');

// Create client with detailed options for better debugging
export const supabase = createClient(
  supabaseUrl, 
  finalAnonKey,
  {
    auth: {
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: true,
      storageKey: 'ai-calendar-auth-token',
      debug: process.env.NODE_ENV === 'development',
    },
  }
); 