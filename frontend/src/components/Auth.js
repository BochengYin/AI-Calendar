import React, { useState, useEffect } from 'react';
import { supabase } from '../supabase/client';

export const Auth = ({ onAuthenticated }) => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [initError, setInitError] = useState(null);

  // Check if Supabase is properly initialized
  useEffect(() => {
    if (!supabase) {
      console.error('Supabase client is not initialized in Auth component');
      setInitError('Authentication service is not available. Please check your configuration.');
    } else {
      console.log('Auth component: Supabase client initialized');
      
      // Testing supabase connection
      const testConnection = async () => {
        try {
          await supabase.auth.getSession();
          console.log('Supabase connection test successful');
        } catch (error) {
          console.error('Supabase connection test failed:', error);
          setInitError('Could not connect to authentication service. Please try again later.');
        }
      };
      
      testConnection();
    }
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();
    
    if (!email || !email.includes('@')) {
      setMessage('Please enter a valid email address');
      return;
    }
    
    try {
      setLoading(true);
      setMessage('');
      
      console.log('Sending magic link to email:', email);
      
      // Send a magic link to the user's email
      const { error } = await supabase.auth.signInWithOtp({
        email,
        options: {
          emailRedirectTo: window.location.origin,
        }
      });
      
      if (error) {
        console.error('Magic link error:', error);
        throw error;
      }
      
      setMessage('Check your email for the magic link! Click on the "Confirm your mail" link in the email.');
    } catch (error) {
      console.error('Error sending magic link:', error);
      setMessage(error.error_description || error.message || 'An error occurred during login');
    } finally {
      setLoading(false);
    }
  };

  // If there's an initialization error, show it
  if (initError) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <h1>🐱 AI Calendar</h1>
          <h2>Authentication Error</h2>
          <div className="auth-error-message">
            {initError}
          </div>
          <p>Please check the console for more information and ensure your environment variables are set correctly.</p>
          <button 
            className="btn btn-primary auth-button"
            onClick={() => window.location.reload()}
          >
            Reload Page
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1>🐱 AI Calendar</h1>
        <h2>Login to Your Calendar</h2>
        
        <form onSubmit={handleLogin} className="auth-form">
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              placeholder="Your email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              required
            />
          </div>
          
          <button 
            type="submit" 
            className="btn btn-primary auth-button"
            disabled={loading}
          >
            {loading ? 'Sending...' : 'Send Magic Link'}
          </button>
          
          {message && (
            <div className="auth-message">
              {message}
              <div className="auth-note" style={{ marginTop: '10px', fontSize: '14px' }}>
                Note: You may need to check your spam folder if you don't see the email.
              </div>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}; 