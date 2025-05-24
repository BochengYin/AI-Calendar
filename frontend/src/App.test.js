import React from 'react';
import { render, screen } from '@testing-library/react';

// Simple test to check if React is working
test('renders basic React component', () => {
  const TestComponent = () => <div>Test Component</div>;
  render(<TestComponent />);
  const testElement = screen.getByText(/test component/i);
  expect(testElement).toBeInTheDocument();
}); 