import React, { useState, useEffect } from 'react';
import { supabase } from '../supabase/client';

export const Auth = ({ onAuthenticated }) => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [showVerificationInput, setShowVerificationInput] = useState(false);
  const [verificationCode, setVerificationCode] = useState('');
  const [initError, setInitError] = useState(null);
  const [debugInfo, setDebugInfo] = useState('');
  const [loginAttempted, setLoginAttempted] = useState(false);

  // Check if Supabase is properly initialized
  useEffect(() => {
    // Display configuration information for debugging
    const debug = {
      supabaseUrl: process.env.REACT_APP_SUPABASE_URL || 'not set',
      apiUrl: process.env.REACT_APP_API_URL || 'not set',
      hasSupabaseKey: process.env.REACT_APP_SUPABASE_ANON_KEY ? 'set' : 'not set',
      nodeEnv: process.env.NODE_ENV || 'not set',
      currentUrl: window.location.href,
      keyType: typeof supabase?.auth?.autoRefreshToken,
      supabaseInitialized: !!supabase
    };
    
    setDebugInfo(JSON.stringify(debug, null, 2));
    console.log('Debug info:', debug);
    
    if (!supabase) {
      console.error('Supabase client is not initialized in Auth component');
      setInitError('Authentication service is not available. Please check your configuration.');
    } else {
      console.log('Auth component: Supabase client initialized', supabase);
      
      // Testing supabase connection
      const testConnection = async () => {
        try {
          console.log('Testing Supabase connection...');
          const { data, error } = await supabase.auth.getSession();
          console.log('Supabase connection test result:', { data, error });
          if (error) throw error;
          console.log('Supabase connection test successful');
        } catch (error) {
          console.error('Supabase connection test failed:', error);
          setInitError(`Could not connect to authentication service: ${error.message || error}`);
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
      setLoginAttempted(true);
      
      console.log('Sending OTP to email:', email);
      
      // Send OTP to the user's email
      const { data, error } = await supabase.auth.signInWithOtp({
        email,
        options: {
          emailRedirectTo: window.location.origin,
          shouldCreateUser: true,
        }
      });
      
      console.log('OTP response:', { data, error });
      
      if (error) {
        console.error('OTP error:', error);
        throw error;
      }
      
      setMessage('Check your email for the verification code. If you don\'t receive it within a minute, check your spam folder or try again.');
      setShowVerificationInput(true);
    } catch (error) {
      console.error('Error sending OTP:', error);
      if (error.message === 'Email not confirmed') {
        setMessage('Please verify your email address. Check your inbox for a verification link.');
        setShowVerificationInput(true);
      } else {
        setMessage(`Authentication Error: ${error.error_description || error.message || 'An error occurred during login'}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleVerification = async (e) => {
    e.preventDefault();
    
    if (!verificationCode) {
      setMessage('Please enter the verification code');
      return;
    }
    
    try {
      setLoading(true);
      setMessage('');
      
      console.log('Verifying OTP code for email:', email, 'code:', verificationCode);
      
      // Verify the OTP code
      const { data, error } = await supabase.auth.verifyOtp({
        email,
        token: verificationCode,
        type: 'email'
      });
      
      console.log('Verification response:', { data, error });
      
      if (error) {
        console.error('Verification error:', error);
        throw error;
      }
      
      // Successfully verified
      console.log('Authentication result:', data);
      if (data.user) {
        console.log('User authenticated:', data.user.email);
        setMessage('Login successful!');
        onAuthenticated(data.user);
      } else {
        throw new Error('No user data returned after successful verification');
      }
    } catch (error) {
      console.error('Error verifying code:', error);
      
      // Handle different error types with more specific messages
      if (error.message.includes('expired')) {
        setMessage('The verification code has expired. Please request a new one.');
      } else if (error.message.includes('invalid')) {
        setMessage('Invalid verification code. Please check and try again.');
      } else {
        setMessage(`Verification Error: ${error.error_description || error.message || 'Invalid verification code'}`);
      }
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
          <details>
            <summary>Debug Information</summary>
            <pre>{debugInfo}</pre>
          </details>
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
        
        {!showVerificationInput ? (
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
              {loading ? 'Sending...' : 'Send Verification Code'}
            </button>
            
            {loginAttempted && (
              <div className="auth-note" style={{ marginTop: '10px', fontSize: '14px', color: '#666' }}>
                Note: This app uses passwordless login. You'll receive a verification code via email.
              </div>
            )}
            
            {message && <div className="auth-message">{message}</div>}
            
            <details style={{ marginTop: '20px', fontSize: '12px' }}>
              <summary>Debug Information</summary>
              <pre>{debugInfo}</pre>
            </details>
          </form>
        ) : (
          <form onSubmit={handleVerification} className="auth-form">
            <div className="form-group">
              <label htmlFor="verification">Verification Code</label>
              <input
                id="verification"
                type="text"
                placeholder="Enter verification code from your email"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value)}
                disabled={loading}
                required
                autoComplete="one-time-code"
              />
            </div>
            
            <button 
              type="submit" 
              className="btn btn-primary auth-button"
              disabled={loading}
            >
              {loading ? 'Verifying...' : 'Verify Code'}
            </button>
            
            <button 
              type="button" 
              className="btn btn-secondary auth-button"
              onClick={() => setShowVerificationInput(false)}
              disabled={loading}
            >
              Back
            </button>
            
            {message && (
              <div className="auth-message">
                {message}
                {message.includes('Check your email') && (
                  <div className="auth-note" style={{ marginTop: '10px', fontSize: '14px' }}>
                    Note: You may need to check your spam folder if you don't see the email.
                  </div>
                )}
              </div>
            )}
          </form>
        )}
      </div>
    </div>
  );
}; 