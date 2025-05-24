import React, { useState, useMemo } from 'react';
import { Calendar as BigCalendar, momentLocalizer } from 'react-big-calendar';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import moment from 'moment';
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';
import { supabase } from '../supabase/client';

// Backend API URL - easier to change if needed
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:12345';

const localizer = momentLocalizer(moment);

// Custom Apple-style toolbar component
const CustomToolbar = ({ label, onNavigate, onView, view, views }) => {
  return (
    <div className="calendar-toolbar">
      <div className="toolbar-navigation">
        <button 
          type="button" 
          className="nav-button today-button"
          onClick={() => onNavigate('TODAY')}
        >
          Today
        </button>
        <div className="nav-arrows">
          <button 
            type="button" 
            className="nav-arrow prev-button"
            onClick={() => onNavigate('PREV')}
            aria-label="Previous"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M10 12L6 8L10 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
          <button 
            type="button" 
            className="nav-arrow next-button"
            onClick={() => onNavigate('NEXT')}
            aria-label="Next"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M6 4L10 8L6 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>
      </div>
      
      <div className="toolbar-title">
        {label}
      </div>
      
      <div className="toolbar-views">
        {views.map(name => (
          <button
            key={name}
            type="button"
            className={`view-button ${view === name ? 'active' : ''}`}
            onClick={() => onView(name)}
          >
            {name.charAt(0).toUpperCase() + name.slice(1)}
          </button>
        ))}
      </div>
    </div>
  );
};

export const Calendar = ({ events, onEventsChange, user, forceRefresh: externalForceRefresh }) => {
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [isRescheduling, setIsRescheduling] = useState(false);
  const [rescheduleData, setRescheduleData] = useState({
    startDate: '',
    startTime: '',
    endDate: '',
    endTime: ''
  });
  const [showNewEventForm, setShowNewEventForm] = useState(false);
  const [newEventData, setNewEventData] = useState({
    title: '',
    startDate: '',
    startTime: '',
    endDate: '',
    endTime: '',
    description: '',
    allDay: false
  });
  const [forceRefresh, setForceRefresh] = useState(0);
  
  // Convert the events to the format expected by react-big-calendar
  const calendarEvents = events.map(event => ({
    id: event.id,
    title: event.title,
    start: new Date(event.start),
    end: new Date(event.end),
    allDay: event.allDay || false,
    resource: event,
    isDeleted: event.isDeleted || false,
    rescheduledFrom: event.rescheduledFrom || null
  }));

  // Create a key that changes when events change to force BigCalendar re-render
  const calendarKey = useMemo(() => {
    return `${forceRefresh}-${externalForceRefresh || 0}-${events.map(e => `${e.id}-${e.isDeleted}-${e.rescheduledFrom ? 'reschedule' : 'normal'}`).join(',')}`;
  }, [events, forceRefresh, externalForceRefresh]);

  const handleSelectEvent = (event) => {
    setSelectedEvent(event.resource);
    setIsRescheduling(false);
    setShowNewEventForm(false);
  };

  const closeEventDetails = () => {
    setSelectedEvent(null);
    setIsRescheduling(false);
  };
  
  const closeNewEventForm = () => {
    setShowNewEventForm(false);
  };

  // Handle calendar slot selection (clicking on calendar dates/times)
  const handleSelectSlot = ({ start, end }) => {
    // Close any existing forms or details
    setSelectedEvent(null);
    setIsRescheduling(false);
    
    // Initialize new event form with selected date/time
    const startMoment = moment(start);
    const endMoment = moment(end);
    
    setNewEventData({
      title: '',
      startDate: startMoment.format('YYYY-MM-DD'),
      startTime: startMoment.format('HH:mm'),
      endDate: endMoment.format('YYYY-MM-DD'),
      endTime: endMoment.format('HH:mm'),
      description: '',
      allDay: false
    });
    
    setShowNewEventForm(true);
  };
  
  const handleNewEventChange = (e) => {
    const { name, value, type, checked } = e.target;
    setNewEventData({
      ...newEventData,
      [name]: type === 'checkbox' ? checked : value
    });
  };
  
  const submitNewEvent = async (e) => {
    e.preventDefault();
    
    // Create ISO date strings for start and end times
    const startDateTime = moment(`${newEventData.startDate} ${newEventData.startTime}`).format();
    const endDateTime = moment(`${newEventData.endDate} ${newEventData.endTime}`).format();
    
    // Create event object
    const newEvent = {
      id: uuidv4(), // Generate client-side ID
      title: newEventData.title,
      start: startDateTime,
      end: endDateTime,
      allDay: newEventData.allDay,
      description: newEventData.description,
      user_id: user?.id // Add the current user's ID to support RLS
    };
    
    try {
      // Get the current session to get the access token
      const { data: sessionData } = await supabase.auth.getSession();
      const accessToken = sessionData?.session?.access_token;
      
      const response = await axios.post(`${API_BASE_URL}/api/events`, newEvent, {
        headers: {
          'Authorization': accessToken ? `Bearer ${accessToken}` : '',
          'User-Email': user.email
        }
      });
      
      // If successful, add the event to local state
      if (response.status === 201) {
        const createdEvent = response.data;
        
        // Add the new event to the events array
        const updatedEvents = [...events, createdEvent];
        
        // Notify parent component about the change
        if (onEventsChange) {
          onEventsChange(updatedEvents);
        }
        
        // Force calendar re-render for consistency
        setForceRefresh(prev => prev + 1);
        
        // Close the form
        closeNewEventForm();
      } else {
        alert('Failed to create event');
      }
    } catch (error) {
      console.error('Error creating event:', error);
      alert(`Error creating event: ${error.response?.data?.message || error.message}`);
    }
  };

  const handleDeleteEvent = async () => {
    if (!selectedEvent) {
      alert('Cannot delete event: No event selected');
      return;
    }
    
    const isAlreadySoftDeleted = selectedEvent.isDeleted === true;

    if (!selectedEvent.id && selectedEvent.id !== 0) {
      // For events without an ID (e.g., local only, not yet saved), just filter out
      const updatedEvents = events.filter(event => 
        event.title !== selectedEvent.title || 
        event.start !== selectedEvent.start || 
        event.end !== selectedEvent.end
      );
      
      if (onEventsChange) {
        onEventsChange(updatedEvents);
      }
      closeEventDetails();
      return;
    }

    try {
      // Always call the backend to ensure it's deleted there
      const response = await axios.delete(`${API_BASE_URL}/api/events/${selectedEvent.id}`);
      
      if (response.data.status === 'success') {
        let updatedEvents;
        if (isAlreadySoftDeleted) {
          // If it was already soft-deleted (Clean button was clicked), filter it out completely
          updatedEvents = events.filter(event => event.id !== selectedEvent.id);
        } else {
          // If it was an active event (Delete button was clicked), mark it as deleted (soft delete)
          updatedEvents = events.map(event => 
            event.id === selectedEvent.id 
              ? { ...event, isDeleted: true } 
              : event
          );
        }
        
        if (onEventsChange) {
          onEventsChange(updatedEvents);
        }
        
        // Force calendar re-render to immediately show styling changes
        setForceRefresh(prev => prev + 1);
        
        closeEventDetails();
      } else {
        alert('Failed to delete event');
      }
    } catch (error) {
      console.error('Error deleting event:', error);
        alert(`Error deleting event: ${error.response?.data?.message || error.message}`);
    }
  };

  const startReschedule = () => {
    // Set initial reschedule data based on selected event
    setRescheduleData({
      startDate: moment(selectedEvent.start).format('YYYY-MM-DD'),
      startTime: moment(selectedEvent.start).format('HH:mm'),
      endDate: moment(selectedEvent.end).format('YYYY-MM-DD'),
      endTime: moment(selectedEvent.end).format('HH:mm')
    });
    setIsRescheduling(true);
  };

  const handleRescheduleChange = (e) => {
    const { name, value } = e.target;
    setRescheduleData({
      ...rescheduleData,
      [name]: value
    });
  };

  const submitReschedule = async (e) => {
    e.preventDefault();
    
    const startDateTime = moment(`${rescheduleData.startDate} ${rescheduleData.startTime}`).format();
    const endDateTime = moment(`${rescheduleData.endDate} ${rescheduleData.endTime}`).format();
    
    const reschedulePayload = {
      start: startDateTime,
      end: endDateTime
    };
    
    try {
      const response = await axios.put(`${API_BASE_URL}/api/events/${selectedEvent.id}/reschedule`, reschedulePayload);
      
      if (response.status === 200) {
        const rescheduledEvent = response.data;
        
        // Update the events array with the rescheduled event
        const updatedEvents = events.map(event => 
          event.id === selectedEvent.id 
            ? rescheduledEvent 
            : event
        );
        
        // Notify parent component about the change
        if (onEventsChange) {
          onEventsChange(updatedEvents);
        }
        
        // Force calendar re-render for consistency
        setForceRefresh(prev => prev + 1);
        
        // Close the reschedule form
        setIsRescheduling(false);
        closeEventDetails();
      } else {
        alert('Failed to reschedule event');
      }
    } catch (error) {
      console.error('Error rescheduling event:', error);
      alert(`Error rescheduling event: ${error.response?.data?.message || error.message}`);
    }
  };

  // Event component for displaying events
  const EventComponent = ({ event }) => (
    <div className="calendar-event-wrapper">
      <div className="calendar-event">
        {event.title}
      </div>
      <div className="event-tooltip">
        <div className="tooltip-title">{event.title}</div>
        <div className="tooltip-time">
          {moment(event.start).format('h:mm A')} - {moment(event.end).format('h:mm A')}
        </div>
        {event.resource.description && (
          <div className="tooltip-description">{event.resource.description}</div>
        )}
        {event.isDeleted && <div className="tooltip-status deleted">Deleted</div>}
        {event.rescheduledFrom && <div className="tooltip-status rescheduled">Rescheduled</div>}
      </div>
    </div>
  );

  const eventStyleGetter = (event, start, end, isSelected) => {
    const style = {
      backgroundColor: event.isDeleted ? '#FFCC00' : '#007AFF',
      borderRadius: '4px',
      color: event.isDeleted ? '#666' : 'white',
      border: 'none',
      display: 'block',
      textDecoration: event.isDeleted ? 'line-through' : 'none',
      fontWeight: event.isDeleted ? 'normal' : 'bold'
    };
    return {
      style: style
    };
  };

  return (
    <div className="calendar-view">
      <h2 className="text-center mb-4">AI Calendar</h2>
      <div className="calendar-scroll-container">
      <BigCalendar
          key={calendarKey}
        localizer={localizer}
        events={calendarEvents}
        startAccessor="start"
        endAccessor="end"
          style={{ height: '800px', minHeight: '600px' }}
        components={{
            event: EventComponent,
            toolbar: CustomToolbar
        }}
        eventPropGetter={eventStyleGetter}
        onSelectEvent={handleSelectEvent}
        onSelectSlot={handleSelectSlot}
        selectable={true}
        popup
      />
      </div>
      
      {selectedEvent && (
        <div className="event-detail-overlay" onClick={closeEventDetails}>
          <div className="event-detail-modal" onClick={e => e.stopPropagation()}>
            <button className="close-button" onClick={closeEventDetails}>×</button>
            <div className="event-detail-header">
              <h3>{selectedEvent.title}</h3>
              {selectedEvent.isDeleted && <span className="event-status deleted">Deleted</span>}
              {selectedEvent.rescheduledFrom && <span className="event-status rescheduled">Rescheduled</span>}
            </div>
            
            {!isRescheduling ? (
              <div className="event-detail-content">
                <div className="detail-row">
                  <div className="detail-label">Date</div>
                  <div className="detail-value">{moment(selectedEvent.start).format('dddd, MMMM D, YYYY')}</div>
                </div>
                <div className="detail-row">
                  <div className="detail-label">Time</div>
                  <div className="detail-value">
                    {moment(selectedEvent.start).format('h:mm A')} - {moment(selectedEvent.end).format('h:mm A')}
                  </div>
                </div>
                {selectedEvent.description && (
                  <div className="detail-row">
                    <div className="detail-label">Description</div>
                    <div className="detail-value">{selectedEvent.description}</div>
                  </div>
                )}
                
                {selectedEvent.rescheduledFrom && (
                  <div className="detail-row original-schedule">
                    <div className="detail-label">Original Schedule</div>
                    <div className="detail-value">
                      {moment(selectedEvent.rescheduledFrom.start).format('MMM D, YYYY h:mm A')} - {moment(selectedEvent.rescheduledFrom.end).format('h:mm A')}
                    </div>
                  </div>
                )}
                
                {!selectedEvent.isDeleted && (
                  <div className="event-actions">
                    <button 
                      className="btn action-btn reschedule-btn" 
                      onClick={startReschedule}
                    >
                      Reschedule
                    </button>
                    <button 
                      className="btn action-btn delete-btn" 
                      onClick={handleDeleteEvent}
                    >
                      Delete
                    </button>
                  </div>
                )}
                {selectedEvent.isDeleted && (
                  <div className="event-actions">
                    <button
                      className="btn action-btn clean-btn"
                      onClick={handleDeleteEvent}
                      title="Permanently remove this event from calendar"
                    >
                      Clean
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="event-detail-content">
                <h4>Reschedule Event</h4>
                <form onSubmit={submitReschedule}>
                  <div className="form-group">
                    <label>Start Date</label>
                    <input 
                      type="date" 
                      name="startDate" 
                      value={rescheduleData.startDate} 
                      onChange={handleRescheduleChange} 
                      className="form-control"
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Start Time</label>
                    <input 
                      type="time" 
                      name="startTime" 
                      value={rescheduleData.startTime} 
                      onChange={handleRescheduleChange} 
                      className="form-control"
                      required 
                    />
                  </div>
                  <div className="form-group">
                    <label>End Date</label>
                    <input 
                      type="date" 
                      name="endDate" 
                      value={rescheduleData.endDate} 
                      onChange={handleRescheduleChange} 
                      className="form-control"
                      required 
                    />
                  </div>
                  <div className="form-group">
                    <label>End Time</label>
                    <input 
                      type="time" 
                      name="endTime" 
                      value={rescheduleData.endTime} 
                      onChange={handleRescheduleChange} 
                      className="form-control"
                      required 
                    />
                  </div>
                  <div className="form-actions">
                    <button type="submit" className="btn primary-btn">Save Changes</button>
                    <button type="button" className="btn secondary-btn" onClick={() => setIsRescheduling(false)}>Cancel</button>
                  </div>
                </form>
              </div>
            )}
          </div>
        </div>
      )}
      
      {showNewEventForm && (
        <div className="event-detail-overlay" onClick={closeNewEventForm}>
          <div className="event-detail-modal" onClick={e => e.stopPropagation()}>
            <button className="close-button" onClick={closeNewEventForm}>×</button>
            <div className="event-detail-header">
              <h3>Create New Event</h3>
            </div>
            
            <div className="event-detail-content">
              <form onSubmit={submitNewEvent}>
                <div className="form-group">
                  <label>Title</label>
                  <input 
                    type="text" 
                    name="title" 
                    value={newEventData.title} 
                    onChange={handleNewEventChange} 
                    className="form-control"
                    placeholder="Event title"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Start Date</label>
                  <input 
                    type="date" 
                    name="startDate" 
                    value={newEventData.startDate} 
                    onChange={handleNewEventChange} 
                    className="form-control"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Start Time</label>
                  <input 
                    type="time" 
                    name="startTime" 
                    value={newEventData.startTime} 
                    onChange={handleNewEventChange} 
                    className="form-control"
                    required 
                  />
                </div>
                <div className="form-group">
                  <label>End Date</label>
                  <input 
                    type="date" 
                    name="endDate" 
                    value={newEventData.endDate} 
                    onChange={handleNewEventChange} 
                    className="form-control"
                    required 
                  />
                </div>
                <div className="form-group">
                  <label>End Time</label>
                  <input 
                    type="time" 
                    name="endTime" 
                    value={newEventData.endTime} 
                    onChange={handleNewEventChange} 
                    className="form-control"
                    required 
                  />
                </div>
                <div className="form-group">
                  <label>Description</label>
                  <textarea 
                    name="description" 
                    value={newEventData.description} 
                    onChange={handleNewEventChange} 
                    className="form-control"
                    placeholder="Event description"
                    rows="3"
                  />
                </div>
                <div className="form-group">
                  <label className="checkbox-container">
                    <input 
                      type="checkbox" 
                      name="allDay" 
                      checked={newEventData.allDay} 
                      onChange={handleNewEventChange} 
                    />
                    <span className="checkbox-label">All Day Event</span>
                  </label>
                </div>
                <div className="form-actions">
                  <button type="submit" className="btn primary-btn">Create Event</button>
                  <button type="button" className="btn secondary-btn" onClick={closeNewEventForm}>Cancel</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}; 