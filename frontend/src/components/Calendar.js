import React, { useState } from 'react';
import { Calendar as BigCalendar, momentLocalizer } from 'react-big-calendar';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import moment from 'moment';
import axios from 'axios';

// Backend API URL - easier to change if needed
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const localizer = momentLocalizer(moment);

export const Calendar = ({ events, onEventsChange }) => {
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [isRescheduling, setIsRescheduling] = useState(false);
  const [rescheduleData, setRescheduleData] = useState({
    startDate: '',
    startTime: '',
    endDate: '',
    endTime: ''
  });
  
  // Convert the events to the format expected by react-big-calendar
  const calendarEvents = events.map(event => ({
    id: event.id,
    title: event.title,
    start: new Date(event.start),
    end: new Date(event.end),
    allDay: event.allDay || false,
    resource: event,
    isDeleted: event.isDeleted || false,
    isRescheduled: !!event.rescheduled_from
  }));

  const handleSelectEvent = (event) => {
    setSelectedEvent(event.resource);
    setIsRescheduling(false);
  };

  const closeEventDetails = () => {
    setSelectedEvent(null);
    setIsRescheduling(false);
  };

  const handleDeleteEvent = async () => {
    if (!selectedEvent) {
      alert('Cannot delete event: No event selected');
      return;
    }
    
    if (!selectedEvent.id && selectedEvent.id !== 0) {
      // For events without an ID, just update local state
      const updatedEvents = events.filter(event => 
        event.title !== selectedEvent.title || 
        event.start !== selectedEvent.start || 
        event.end !== selectedEvent.end
      );
      
      // Notify parent component about the change
      if (onEventsChange) {
        onEventsChange(updatedEvents);
      }
      
      // Close the modal
      closeEventDetails();
      return;
    }

    try {
      const response = await axios.delete(`${API_BASE_URL}/api/events/${selectedEvent.id}`);
      
      if (response.data.status === 'success') {
        // IMMEDIATELY mark event as deleted in local state without waiting for backend refresh
        const updatedEvents = events.map(event => 
          event.id === selectedEvent.id 
            ? { ...event, isDeleted: true } 
            : event
        );
        
        // Notify parent component about the change
        if (onEventsChange) {
          onEventsChange(updatedEvents);
        }
        
        // Close the modal
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
    // Pre-fill the reschedule form with current dates
    const start = moment(selectedEvent.start);
    const end = moment(selectedEvent.end);
    
    setRescheduleData({
      startDate: start.format('YYYY-MM-DD'),
      startTime: start.format('HH:mm'),
      endDate: end.format('YYYY-MM-DD'),
      endTime: end.format('HH:mm')
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
    
    if (!selectedEvent || !selectedEvent.id) {
      alert('Cannot reschedule event: No event ID found');
      return;
    }
    
    // Create new date objects from the form data
    const startDateTime = moment(`${rescheduleData.startDate} ${rescheduleData.startTime}`).format();
    const endDateTime = moment(`${rescheduleData.endDate} ${rescheduleData.endTime}`).format();
    
    // Create updated event object
    const updatedEvent = {
      ...selectedEvent,
      start: startDateTime,
      end: endDateTime
    };
    
    try {
      const response = await axios.put(
        `${API_BASE_URL}/api/events/${selectedEvent.id}`, 
        updatedEvent
      );
      
      if (response.data.status === 'success') {
        // Update event in local state
        const updatedEvents = events.map(event => 
          event.id === selectedEvent.id 
            ? response.data.updated_event 
            : event
        );
        
        // Notify parent component about the change
        if (onEventsChange) {
          onEventsChange(updatedEvents);
        }
        
        // Close the modal
        closeEventDetails();
      } else {
        alert('Failed to reschedule event');
      }
    } catch (error) {
      console.error('Error rescheduling event:', error);
      alert('An error occurred while rescheduling the event');
    }
  };

  // Custom event component with tooltip
  const EventComponent = ({ event }) => (
    <div className={`calendar-event-wrapper ${event.isDeleted ? 'event-deleted' : ''} ${event.isRescheduled ? 'event-rescheduled' : ''}`}>
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
        {event.isDeleted && (
          <div className="tooltip-status deleted">Deleted</div>
        )}
        {event.isRescheduled && (
          <div className="tooltip-status rescheduled">Rescheduled</div>
        )}
      </div>
    </div>
  );

  // Style getter for events
  const eventStyleGetter = (event) => {
    let style = {
      backgroundColor: '#007aff',
      borderRadius: '5px',
      color: 'white',
      border: 'none',
      display: 'block',
      overflow: 'hidden'
    };
    
    let className = '';
    
    if (event.isDeleted) {
      className = 'event-deleted';
      style.backgroundColor = '#ccc';
      style.color = '#666';
    } else if (event.isRescheduled) {
      className = 'event-rescheduled';
      style.backgroundColor = '#f0d98b';
      style.color = '#896c1d';
    }
    
    return {
      style,
      className
    };
  };

  return (
    <div className="calendar-view">
      <h2 className="text-center mb-4">AI Calendar</h2>
      <BigCalendar
        localizer={localizer}
        events={calendarEvents}
        startAccessor="start"
        endAccessor="end"
        style={{ height: 'calc(100vh - 140px)' }}
        components={{
          event: EventComponent
        }}
        eventPropGetter={eventStyleGetter}
        onSelectEvent={handleSelectEvent}
        popup
      />
      
      {selectedEvent && (
        <div className="event-detail-overlay" onClick={closeEventDetails}>
          <div className="event-detail-modal" onClick={e => e.stopPropagation()}>
            <button className="close-button" onClick={closeEventDetails}>×</button>
            <div className="event-detail-header">
              <h3>{selectedEvent.title}</h3>
              {selectedEvent.isDeleted && <span className="event-status deleted">Deleted</span>}
              {selectedEvent.rescheduled_from && <span className="event-status rescheduled">Rescheduled</span>}
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
                
                {selectedEvent.rescheduled_from && (
                  <div className="detail-row original-schedule">
                    <div className="detail-label">Original Schedule</div>
                    <div className="detail-value">
                      {moment(selectedEvent.rescheduled_from.start).format('MMM D, YYYY h:mm A')} - {moment(selectedEvent.rescheduled_from.end).format('h:mm A')}
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
    </div>
  );
}; 