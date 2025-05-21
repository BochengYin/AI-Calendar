import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Calendar } from './components/Calendar';
import { Chatbot } from './components/Chatbot';
import { UpcomingEvents } from './components/UpcomingEvents';
import { Auth } from './components/Auth';
import { useAuth } from './context/AuthContext';
import './index.css';
import axios from 'axios';
import { supabase } from './supabase/client';
import { v4 as uuidv4 } from 'uuid';

// Backend API URL - easier to change if needed
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:12345';

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
  const [refreshError, setRefreshError] = useState(null);
  const refreshTimerRef = useRef(null);
  const refreshIntervalMs = 30000; // Refresh every 30 seconds

  // Use useCallback to memoize the fetchEvents function
  const fetchEvents = useCallback(async () => {
    try {
      setRefreshError(null);
      // Get the current session to get the access token
      const { data: sessionData } = await supabase.auth.getSession();
      const accessToken = sessionData?.session?.access_token;
      
      // Add explicit user_id filter to improve RLS performance
      const response = await axios.get(`${API_BASE_URL}/api/events`, {
        headers: {
          Authorization: accessToken ? `Bearer ${accessToken}` : '',
          'User-Email': user.email
        },
        params: {
          user_id: user.id // Add explicit filter parameter
        }
      });
      
      // Transform events to ensure they all have IDs
      const events = response.data.map(event => 
        event.id ? event : { ...event, id: crypto.randomUUID() }
      );
      
      console.log(`Fetched ${events.length} events`);
      setEvents(events);
      return true;
    } catch (error) {
      console.error('Error fetching events:', error);
      setRefreshError(`Failed to refresh events: ${error.message}`);
      return false;
    }
  }, [user]);

  useEffect(() => {
    if (user) {
      // Initial fetch
      fetchEvents();
      checkSystemStatus();
      
      // Set up periodic refresh
      refreshTimerRef.current = setInterval(() => {
        console.log('Periodic refresh of events...');
        fetchEvents();
      }, refreshIntervalMs);
      
      // Cleanup interval on unmount
      return () => {
        if (refreshTimerRef.current) {
          clearInterval(refreshTimerRef.current);
        }
      };
    }
  }, [user, fetchEvents]);

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
          // Find the original event by title and originalStart (date part, not exact time)
          const updatedEvents = prev.map(event => {
            // Extract just the date parts for comparison
            const eventDatePart = event.start ? event.start.split('T')[0] : '';
            const originalDatePart = response.event.originalStart ? response.event.originalStart.split('T')[0] : '';
            
            // Convert titles to lowercase for case-insensitive comparison
            const eventTitleLower = event.title ? event.title.toLowerCase() : '';
            const originalTitleLower = response.event.title ? response.event.title.toLowerCase() : '';
            
            // Check if this event matches the date and has title keyword overlap
            const dateMatches = eventDatePart === originalDatePart;
            const titleMatches = eventTitleLower.includes(originalTitleLower) || 
                                originalTitleLower.includes(eventTitleLower) ||
                                (eventTitleLower.split(' ').some(word => originalTitleLower.includes(word) && word.length > 3));
            
            if (dateMatches && titleMatches && !event.isDeleted) {
              // Mark original event as deleted/rescheduled
              return { 
                ...event, 
                isDeleted: true, 
                isRescheduled: true,
                rescheduled_from: event.id // Use rescheduled_from to match the expected field in calendarEvents
              };
            }
            return event;
          });
          
          // Add the rescheduled event with the new times (this will be blue)
          const newEvent = {
            ...response.event,
            id: response.event.id || uuidv4(), // Ensure new event has an ID
          };

          return [...updatedEvents, newEvent];
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

  if (authLoading) {
    return <div className="loading-container">Loading...</div>;
  }

  // User is authenticated, show the app
  return (
    <div className="App">
      <div className="experimental-banner">
        This is an experimental product. Please do not share any sensitive information.
      </div>
      {!user && !authLoading ? (
        <Auth />
      ) : (
        <div className="main-layout">
          <header className="app-header">
            <div className="logo-and-title">
              <h1>AI Calendar</h1>
            </div>
            {user && (
              <div className="user-info">
                <span>{user.email}</span>
                <button onClick={signOut} className="signout-button">Sign Out</button>
                <button onClick={() => setShowStatusModal(true)} className="system-status-button">System Status</button>
              </div>
            )}
          </header>
          {refreshError && (
            <div className="error-banner">
              {refreshError}
              <button onClick={fetchEvents}>Retry</button>
            </div>
          )}
          <div className="main-content">
            <div className="left-panel">
              <div className="upcoming-events-container">
                <UpcomingEvents events={events} />
              </div>
            </div>
            <div className="calendar-container">
              <Calendar events={events} onEventsChange={handleEventsChange} user={user} />
            </div>
            <div className="chat-panel">
              <div className="chatbot-container">
                <Chatbot onEventAdded={handleChatResponse} userId={user.id} userEmail={user.email} />
              </div>
            </div>
          </div>
          {showStatusModal && <StatusModal />}
        </div>
      )}
    </div>
  );
}

export default App; 