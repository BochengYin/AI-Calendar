import React, { createContext, useState, useEffect, useContext } from 'react';
import { supabase } from '../supabase/client';

// Create the authentication context
const AuthContext = createContext();

// Provider component that wraps app and makes auth object available
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    console.log('AuthContext initializing...');
    
    // Check if supabase client is properly initialized
    if (!supabase) {
      console.error('Supabase client is not properly initialized');
      setError('Supabase client is not initialized');
      setLoading(false);
      return;
    }

    // Check if there's an active session on initial load
    const initializeAuth = async () => {
      try {
        setLoading(true);
        
        console.log('Checking for existing session...');
        
        // Get the current session
        const { data, error } = await supabase.auth.getSession();
        
        if (error) {
          console.error('Session check error:', error.message);
          throw error;
        }
        
        console.log('Session check result:', data ? 'Session found' : 'No session');
        
        if (data?.session) {
          // Set the user if session exists
          setUser(data.session.user);
        }
      } catch (error) {
        console.error('Error checking authentication:', error);
        setError(error.message || 'Authentication error');
      } finally {
        setLoading(false);
      }
    };

    // Set up auth state listener 
    let authListener = null;
    
    try {
      initializeAuth();

      // Listen for authentication state changes
      const { data } = supabase.auth.onAuthStateChange(
        async (event, session) => {
          console.log('Auth state changed:', event);
          if (session?.user) {
            setUser(session.user);
          } else {
            setUser(null);
          }
          setLoading(false);
        }
      );
      
      authListener = data;
    } catch (err) {
      console.error('Error in auth setup:', err);
      setError(err.message || 'Auth setup error');
      setLoading(false);
    }

    // Cleanup subscription on unmount
    return () => {
      if (authListener?.subscription) {
        console.log('Cleaning up auth listener');
        authListener.subscription.unsubscribe();
      }
    };
  }, []);

  // Sign out function
  const signOut = async () => {
    try {
      setLoading(true);
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
      setUser(null);
    } catch (error) {
      console.error('Error signing out:', error);
      setError(error.message || 'Sign out error');
    } finally {
      setLoading(false);
    }
  };

  // Make the context object with user state and auth methods
  const value = {
    user,
    loading,
    error,
    signOut,
  };

  // Return the provider with the value
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Custom hook to use the auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}; 