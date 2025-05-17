import React from 'react';
import ReactDOM from 'react-dom';
import App from './App';

// Simple test to see if the App component renders without crashing
it('renders without crashing', () => {
  const div = document.createElement('div');
  ReactDOM.render(<App />, div);
  ReactDOM.unmountComponentAtNode(div);
}); 