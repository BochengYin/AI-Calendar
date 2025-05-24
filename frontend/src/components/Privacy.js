import React from 'react';

const Privacy = () => {
  return (
    <div className="privacy-container">
      <div className="privacy-content">
        <h1>Privacy Policy</h1>
        <div className="privacy-section">
          <h2>Introduction</h2>
          <p>
            Welcome to AI Calendar! This is an experimental open-source project, and we take your privacy seriously.
            This privacy policy explains how we collect, use, and protect your information.
          </p>
        </div>

        <div className="privacy-section">
          <h2>Information We Collect</h2>
          <ul>
            <li><strong>Email Address:</strong> Used solely for authentication and account identification</li>
            <li><strong>Calendar Events:</strong> Event titles, times, and descriptions you create</li>
            <li><strong>Basic Usage Logs:</strong> For system operation and debugging purposes</li>
          </ul>
        </div>

        <div className="privacy-section">
          <h2>How We Use Your Information</h2>
          <ul>
            <li>User authentication and account management</li>
            <li>Providing personalized calendar services</li>
            <li>System maintenance and improvements</li>
          </ul>
        </div>

        <div className="privacy-section">
          <h2>Third-Party Services</h2>
          <p>We use the following third-party services:</p>
          <ul>
            <li><strong>Supabase:</strong> User authentication and data storage</li>
            <li><strong>OpenAI API:</strong> Providing AI assistant functionality</li>
            <li><strong>Google OAuth:</strong> Google account login</li>
          </ul>
        </div>

        <div className="privacy-section">
          <h2>Data Protection</h2>
          <ul>
            <li>Your data will not be used for commercial purposes</li>
            <li>We do not share your personal information with third parties</li>
            <li>All data transmission uses HTTPS encryption</li>
            <li>You can delete your account and data at any time</li>
          </ul>
        </div>

        <div className="privacy-section">
          <h2>Data Deletion</h2>
          <p>
            If you wish to delete your data, please contact us. We will delete all your personal information 
            within a reasonable timeframe.
          </p>
        </div>

        <div className="privacy-section">
          <h2>Contact Us</h2>
          <p>
            If you have any questions about this privacy policy, please contact us through{' '}
            <a href="https://github.com/BochengYin/AI-Calendar" target="_blank" rel="noopener noreferrer">
              GitHub
            </a>.
          </p>
        </div>

        <div className="privacy-section">
          <p className="last-updated">
            Last updated: {new Date().toLocaleDateString('en-US')}
          </p>
        </div>

        <div className="privacy-actions">
          <button 
            className="btn btn-primary" 
            onClick={() => window.history.back()}
          >
            Back to App
          </button>
        </div>
      </div>
    </div>
  );
};

export default Privacy; 