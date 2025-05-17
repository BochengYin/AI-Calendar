import React, { useState, useEffect } from 'react';
import { Calendar } from './components/Calendar';
import { Chatbot } from './components/Chatbot';
import { UpcomingEvents } from './components/UpcomingEvents';
import { Auth } from './components/Auth';
import { useAuth } from './context/AuthContext';
import './index.css';
import axios from 'axios';

// Backend API URL - easier to change if needed
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const { user, loading: authLoading, signOut } = useAuth();
  const [events, setEvents] = useState([]);
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [statusInfo, setStatusInfo] = useState({
    backendStatus: 'Checking...',
    apiKeyStatus: 'Checking...',
    apiQuotaStatus: 'Checking...',
    lastChecked: new Date().toLocaleTimeString()
  });

  useEffect(() => {
    // Only fetch events if user is authenticated
    if (user) {
      fetchEvents();
      checkSystemStatus();
    }
  }, [user]);

  const fetchEvents = async () => {
    try {
      // Add the user ID to the request to fetch only this user's events
      const response = await axios.get(`${API_BASE_URL}/api/events`, {
        headers: { 
          'Authorization': `Bearer ${user.id}`,
          'User-Email': user.email
        }
      });
      
      // Ensure all events have IDs for proper handling
      const processedEvents = response.data.map(event => {
        // If the event doesn't have an ID, assign a client-side UUID
        if (!event.id) {
          return { ...event, id: crypto.randomUUID() };
        }
        return event;
      });
      
      setEvents(processedEvents);
    } catch (error) {
      console.error('Error fetching events:', error);
      // If we can't connect to the backend, initialize with empty events array
      setEvents([]);
    }
  };

  const checkSystemStatus = async () => {
    console.log('Checking backend health at:', `${API_BASE_URL}/api/health`);
    try {
      const response = await axios.get(`${API_BASE_URL}/api/health`, { 
        timeout: 30000,
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });
      
      console.log('Backend health response:', response.data);
      setStatusInfo({
        backendStatus: 'Connected',
        apiKeyStatus: response.data.api_key_configured ? 'Configured' : 'Missing',
        apiKeyLength: response.data.api_key_length || 0,
        apiQuotaStatus: 'Unknown (Check with Test button)',
        lastChecked: new Date().toLocaleTimeString()
      });
    } catch (error) {
      console.error('Backend health check failed:', error);
      
      // Provide more detailed error information
      let errorDetails = '';
      if (error.response) {
        errorDetails = `Status: ${error.response.status}, Data: ${JSON.stringify(error.response.data)}`;
      } else if (error.request) {
        errorDetails = 'No response received';
      } else {
        errorDetails = error.message;
      }
      
      console.error('Error details:', errorDetails);
      
      setStatusInfo({
        backendStatus: 'Disconnected',
        apiKeyStatus: 'Unknown',
        apiQuotaStatus: 'Unknown',
        lastChecked: new Date().toLocaleTimeString(),
        error: `${error.message} - ${errorDetails}`
      });
    }
  };

  const handleChatResponse = (response) => {
    if (response.event) {
      const action = response.action || 'create';
      
      if (action === 'create') {
        // Add new event
        setEvents(prev => [...prev, response.event]);
      } 
      else if (action === 'delete') {
        // For delete action, immediately mark the matching events as deleted
        setEvents(prev => {
          const { title, start } = response.event;
          const titleLower = title?.toLowerCase();
          const startDate = start?.split('T')[0]; // Get just the date part
          
          return prev.map(event => {
            // Mark as deleted if:
            // 1. Title matches and it's on the same date, or
            // 2. It's on the same date and it's a "meeting" type event
            const eventDate = event.start?.split('T')[0];
            const isEventOnSameDate = startDate && eventDate === startDate;
            const hasTitleMatch = titleLower && event.title?.toLowerCase().includes(titleLower);
            const isMeetingType = event.title?.toLowerCase().includes('meeting');
            
            if ((isEventOnSameDate && (hasTitleMatch || (titleLower === 'meeting' && isMeetingType)))) {
              return { ...event, isDeleted: true };
            }
            return event;
          });
        });
      }
      else if (action === 'reschedule') {
        // For reschedule, mark original as deleted and add the new one
        setEvents(prev => {
          const updatedEvents = prev.map(event => {
            // Find the original event by title and mark it as deleted/rescheduled
            if (event.title === response.event.title && !event.isDeleted) {
              return { ...event, isDeleted: true, isRescheduled: true };
            }
            return event;
          });
          
          // Add the rescheduled event
          return [...updatedEvents, response.event];
        });
      }
    }
  };

  const handleEventsChange = (updatedEvents) => {
    setEvents(updatedEvents);
  };

  const StatusModal = () => (
    <div className="status-modal-overlay" onClick={() => setShowStatusModal(false)}>
      <div className="status-modal" onClick={e => e.stopPropagation()}>
        <h3>System Status</h3>
        <table className="status-table">
          <tbody>
            <tr>
              <td>Backend:</td>
              <td className={`status ${statusInfo.backendStatus === 'Connected' ? 'status-ok' : 'status-error'}`}>
                {statusInfo.backendStatus}
              </td>
            </tr>
            <tr>
              <td>API Key:</td>
              <td className={`status ${statusInfo.apiKeyStatus === 'Configured' ? 'status-ok' : 'status-error'}`}>
                {statusInfo.apiKeyStatus}
                {statusInfo.apiKeyLength && ` (${statusInfo.apiKeyLength} chars)`}
              </td>
            </tr>
            <tr>
              <td>API Quota:</td>
              <td className="status">
                {statusInfo.apiQuotaStatus}
              </td>
            </tr>
            <tr>
              <td>Last Checked:</td>
              <td>{statusInfo.lastChecked}</td>
            </tr>
          </tbody>
        </table>
        {statusInfo.error && (
          <div className="status-error-message">
            Error: {statusInfo.error}
          </div>
        )}
        {statusInfo.backendStatus === 'Disconnected' && (
          <div className="status-warning-message">
            <p>Note: The backend is hosted on Render's free tier which spins down with inactivity.</p>
            <p>If your first connection fails, please wait 30-60 seconds while Render spins up the server, then try again.</p>
            <p>You can also visit the backend directly to wake it up:</p>
            <a href={`${API_BASE_URL}/api/health`} target="_blank" rel="noopener noreferrer">
              Wake up backend server
            </a>
          </div>
        )}
        <div className="status-actions">
          <button className="btn btn-primary" onClick={checkSystemStatus}>
            Refresh Status
          </button>
          <button className="btn btn-secondary" onClick={() => setShowStatusModal(false)}>
            Close
          </button>
        </div>
      </div>
    </div>
  );

  // If authentication is still loading, show a loading spinner
  if (authLoading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  // If no user is authenticated, show the Auth component
  if (!user) {
    return <Auth onAuthenticated={(user) => console.log('User authenticated:', user)} />;
  }

  // User is authenticated, show the app
  return (
    <div className="app-container">
      <div className="app-header">
        <h1>🐱 AI Calendar</h1>
        <div className="header-actions">
          <div className="user-profile">
            <span className="user-email">{user.email}</span>
            <button className="logout-button" onClick={signOut}>
              Sign Out
            </button>
          </div>
          <button className="status-button" onClick={() => setShowStatusModal(true)}>
            👾 System Status
          </button>
        </div>
      </div>
      <div className="main-content">
        <div className="left-panel">
          <div className="upcoming-events-container">
            <UpcomingEvents events={events} />
          </div>
        </div>
        <div className="calendar-container">
          <Calendar events={events} onEventsChange={handleEventsChange} />
        </div>
        <div className="chat-panel">
          <div className="chatbot-container">
            <Chatbot onEventAdded={handleChatResponse} userId={user.id} userEmail={user.email} />
          </div>
        </div>
      </div>
      {showStatusModal && <StatusModal />}
    </div>
  );
}

export default App; 