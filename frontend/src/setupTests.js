// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// Set up environment variables for tests if not already set
if (!process.env.REACT_APP_SUPABASE_URL) {
  process.env.REACT_APP_SUPABASE_URL = 'https://ssyhnabptfcxsyydexfc.supabase.co';
}

if (!process.env.REACT_APP_SUPABASE_ANON_KEY) {
  process.env.REACT_APP_SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNzeWhuYWJwdGZjeHN5eWRleGZjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDc0Njc4MzMsImV4cCI6MjA2MzA0MzgzM30.igJyoPiOZWxknXXWJOo2MrYfr6YnxpCmPSR-QpZLkO4';
}

if (!process.env.REACT_APP_API_URL) {
  process.env.REACT_APP_API_URL = 'http://localhost:8000';
} 