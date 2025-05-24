import React from 'react';
import { Link } from 'react-router-dom';

const Footer = () => {
  return (
    <footer className="app-footer">
      <div className="footer-content">
        <div className="footer-links">
          <Link to="/privacy" className="footer-link">Privacy Policy</Link>
          <span className="footer-separator">|</span>
          <a 
            href="https://github.com/BochengYin/AI-Calendar" 
            target="_blank" 
            rel="noopener noreferrer"
            className="footer-link"
          >
            GitHub
          </a>
          <span className="footer-separator">|</span>
          <span className="footer-text">Experimental product - Do not share sensitive information</span>
        </div>
        <div className="footer-disclaimer">
          <p>
            By continuing to use this application, you agree to our{' '}
            <Link to="/privacy" className="footer-link-highlight">Privacy Policy</Link>.
            We only use your email for authentication and do not share your data.
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer; 