import { createClient } from '@supabase/supabase-js';

// Initialize the Supabase client
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL || "https://ssyhnabptfcxsyydexfc.supabase.co";
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY;

// Log environment variables for debugging (URLs only, not keys)
console.log('Supabase URL from env:', supabaseUrl);
console.log('API URL from env:', process.env.REACT_APP_API_URL);
console.log('Node environment:', process.env.NODE_ENV);

if (!supabaseUrl || !supabaseAnonKey) {
  console.error('⚠️ Supabase URL or Anon Key not found. Authentication will not work.');
  console.error('Please make sure your environment variables are set correctly.');
  
  // For development environments, provide more detailed guidance
  if (process.env.NODE_ENV === 'development') {
    console.warn('Make sure you have .env.local file with REACT_APP_SUPABASE_URL and REACT_APP_SUPABASE_ANON_KEY');
  }
}

// NEVER provide fallback values for sensitive credentials
// If environment variables are missing, authentication will gracefully fail
export const supabase = createClient(
  supabaseUrl, 
  supabaseAnonKey || ''
); 