import React, { useState } from 'react';
import { supabase } from '../supabase/client';

export const Auth = ({ onAuthenticated }) => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [showVerificationInput, setShowVerificationInput] = useState(false);
  const [verificationCode, setVerificationCode] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    
    if (!email || !email.includes('@')) {
      setMessage('Please enter a valid email address');
      return;
    }
    
    try {
      setLoading(true);
      setMessage('');
      
      // Send OTP to the user's email
      const { error } = await supabase.auth.signInWithOtp({
        email,
        options: {
          emailRedirectTo: window.location.origin,
        }
      });
      
      if (error) throw error;
      
      setMessage('Check your email for the login link!');
      setShowVerificationInput(true);
    } catch (error) {
      console.error('Error sending login link:', error);
      setMessage(error.error_description || error.message || 'An error occurred during login');
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
      
      // Verify the OTP code
      const { data, error } = await supabase.auth.verifyOtp({
        email,
        token: verificationCode,
        type: 'email'
      });
      
      if (error) throw error;
      
      // Successfully verified
      if (data.user) {
        setMessage('Login successful!');
        onAuthenticated(data.user);
      }
    } catch (error) {
      console.error('Error verifying code:', error);
      setMessage(error.error_description || error.message || 'Invalid verification code');
    } finally {
      setLoading(false);
    }
  };

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
              {loading ? 'Sending...' : 'Send Login Code'}
            </button>
            
            {message && <div className="auth-message">{message}</div>}
          </form>
        ) : (
          <form onSubmit={handleVerification} className="auth-form">
            <div className="form-group">
              <label htmlFor="verification">Verification Code</label>
              <input
                id="verification"
                type="text"
                placeholder="Enter verification code"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value)}
                disabled={loading}
                required
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
            
            {message && <div className="auth-message">{message}</div>}
          </form>
        )}
      </div>
    </div>
  );
}; 