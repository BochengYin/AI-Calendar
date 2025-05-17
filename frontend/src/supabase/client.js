import { createClient } from '@supabase/supabase-js';

// Initialize the Supabase client
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY;

// Log environment variables for debugging (URLs only, not keys)
console.log('Supabase URL from env:', supabaseUrl);
console.log('API URL from env:', process.env.REACT_APP_API_URL);
console.log('Node environment:', process.env.NODE_ENV);

if (!supabaseUrl || !supabaseAnonKey) {
  console.error('⚠️ Supabase URL or Anon Key not found. Authentication will not work.');
  console.error('Please make sure your .env.development file exists and has the correct variables.');
  
  // For development fallback - REMOVE IN PRODUCTION
  if (process.env.NODE_ENV === 'development') {
    console.warn('Using fallback Supabase URL for development');
  }
}

// Ensure we always have values even if env vars fail
const finalSupabaseUrl = supabaseUrl || 'https://ssyhnabptfcxsyydexfc.supabase.co';
const finalSupabaseKey = supabaseAnonKey || '';

export const supabase = createClient(finalSupabaseUrl, finalSupabaseKey); 