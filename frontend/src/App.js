import React, { useState, useEffect } from 'react';
import { Calendar } from './components/Calendar';
import { Chatbot } from './components/Chatbot';
import { UpcomingEvents } from './components/UpcomingEvents';
import './index.css';
import axios from 'axios';

function App() {
  const [events, setEvents] = useState([]);
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [statusInfo, setStatusInfo] = useState({
    backendStatus: 'Checking...',
    apiKeyStatus: 'Checking...',
    apiQuotaStatus: 'Checking...',
    lastChecked: new Date().toLocaleTimeString()
  });

  useEffect(() => {
    // Fetch events from the backend when the component mounts
    fetchEvents();
    checkSystemStatus();
  }, []);

  const fetchEvents = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/events');
      
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
    try {
      const response = await axios.get('http://localhost:8000/api/health', { timeout: 3000 });
      
      setStatusInfo({
        backendStatus: 'Connected',
        apiKeyStatus: response.data.api_key_configured ? 'Configured' : 'Missing',
        apiKeyLength: response.data.api_key_length || 0,
        apiQuotaStatus: 'Unknown (Check with Test button)',
        lastChecked: new Date().toLocaleTimeString()
      });
    } catch (error) {
      setStatusInfo({
        backendStatus: 'Disconnected',
        apiKeyStatus: 'Unknown',
        apiQuotaStatus: 'Unknown',
        lastChecked: new Date().toLocaleTimeString(),
        error: error.message
      });
    }
  };

  const addEvent = (event) => {
    setEvents([...events, event]);
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

  return (
    <div className="app-container">
      <div className="app-header">
        <h1>🐱 AI Calendar</h1>
        <div className="header-actions">
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
            <Chatbot onEventAdded={addEvent} />
          </div>
        </div>
      </div>
      {showStatusModal && <StatusModal />}
    </div>
  );
}

export default App; 