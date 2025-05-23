import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { AuthProvider } from './context/AuthContext';

// Simple test to see if the App component renders without crashing
it('renders without crashing', () => {
  const div = document.createElement('div');
  const root = createRoot(div); // Create a root.
  root.render(
    <AuthProvider>
      <App />
    </AuthProvider>
  );
  root.unmount(); // Unmount the root.
}); 