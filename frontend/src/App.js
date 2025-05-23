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
      
      const response = await axios.get(`${API_BASE_URL}/api/events`, {
        headers: {
          Authorization: accessToken ? `Bearer ${accessToken}` : '',
          'User-Email': user.email
        },
        params: {
          user_id: user.id
        }
      });
      
      // Transform events to ensure they all have IDs and map backend field names to frontend field names
      const fetchedEvents = response.data.map(event => ({
        id: event.id,
        title: event.title,
        start: event.start,
        end: event.end,
        allDay: event.allDay || false,
        description: event.description || '',
        isDeleted: event.is_deleted || false, // Map is_deleted to isDeleted
        rescheduledFrom: event.rescheduled_from || null
      }));
      
      console.log(`Fetched ${fetchedEvents.length} events`);
      if (fetchedEvents.length > 0) {
        console.log(`First event: ${fetchedEvents[0].title}, isDeleted: ${fetchedEvents[0].isDeleted}, rescheduledFrom: ${fetchedEvents[0].rescheduledFrom}`);
      }
      setEvents(fetchedEvents);
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
          console.log('[Chat Delete Action] Event to delete (from chat response):', title, start);
          const titleLower = title?.toLowerCase();
          const startDate = start?.split('T')[0]; // Get just the date part
          
          return prev.map(event => {
            console.log('[Chat Delete Action] Checking event:', event.title, event.start, event.id);
            // Mark as deleted if:
            // 1. Title matches and it's on the same date, or
            // 2. It's on the same date and it's a "meeting" type event
            const eventDate = event.start?.split('T')[0];
            const isEventOnSameDate = startDate && eventDate === startDate;
            const hasTitleMatch = titleLower && event.title?.toLowerCase().includes(titleLower);
            const isMeetingType = event.title?.toLowerCase().includes('meeting');
            
            let markedForDeletion = false;
            if ((isEventOnSameDate && (hasTitleMatch || (titleLower === 'meeting' && isMeetingType)))) {
              console.log('[Chat Delete Action] MATCHED event for deletion:', event.title, event.id);
              markedForDeletion = true;
              return { ...event, isDeleted: true };
            }
            if (!markedForDeletion) {
              console.log('[Chat Delete Action] No match for event:', event.title, event.id, {isEventOnSameDate, hasTitleMatch, isMeetingType, titleLower, startDate, eventDate});
            }
            return event;
          });
        });
      }
      else if (action === 'reschedule') {
        // For reschedule, we should receive a new event object from the backend that already 
        // has all the necessary properties, including the rescheduled_from reference
        console.log('[Chat Reschedule Action] Received event for reschedule:', response.event);
        setEvents(prev => {
          // Find and mark the original event as deleted/rescheduled
          const updatedEvents = prev.map(event => {
            console.log(`[Chat Reschedule Action] Checking event (for original): ${event.title}, ID: ${event.id}, isDeleted: ${event.isDeleted}, rescheduledFrom: ${event.rescheduledFrom}`);
            // Check if this is a rescheduled event (has rescheduled_from ID)
            if (response.event.rescheduled_from && response.event.rescheduled_from === event.id) { // CONDITION 1
              console.log(`[Chat Reschedule Action] Match by rescheduled_from ID: ${event.id}, isDeleted: ${event.isDeleted}, rescheduledFrom: ${event.rescheduledFrom}`);
              // Mark the original event as deleted
              console.log(`[Chat Reschedule Action] Original event found by ID: ${event.id}. Setting isDeleted=true`);
              return {
                ...event,
                isDeleted: true
              };
            }
            
            // Fallback: If rescheduled_from is not available, try to match by title and date
            if (!response.event.rescheduled_from) { // CONDITION 2 (Fallback)
              console.log('[Chat Reschedule Action] No rescheduled_from ID. Attempting fallback match for original.');
              const eventDate = new Date(event.start).toDateString();
              const responseOriginalDate = response.event.originalStart ? new Date(response.event.originalStart).toDateString() : null;
              
              if (event.title.toLowerCase().includes(response.event.title.toLowerCase()) && 
                  eventDate === responseOriginalDate) {
                console.log(`[Chat Reschedule Action] Fallback match found for event: ${event.title} on ${eventDate}. Setting isDeleted=true`);
                return {
                  ...event,
                  isDeleted: true
                };
              }
            }
            
            return event;
          });
          
          // Add the new rescheduled event
          updatedEvents.push({
            ...response.event,
            id: response.event.id || uuidv4(), // Ensure new event has an ID
            isDeleted: response.event.isDeleted || false, // Map backend fields to frontend
            rescheduledFrom: response.event.rescheduled_from || null
          });
          
          return updatedEvents;
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