import React, { useState } from 'react';
import moment from 'moment';

export const UpcomingEvents = ({ events }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Filter out deleted events and sort by start date
  const upcomingEvents = events
    .filter(event => !event.isDeleted)
    .sort((a, b) => moment(a.start).diff(moment(b.start)));

  const toggleCollapse = () => {
    setIsCollapsed(!isCollapsed);
  };

  return (
    <div className={`upcoming-events ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="upcoming-events-header" onClick={toggleCollapse}>
        <h3>Upcoming Events</h3>
        <button className="toggle-button">
          {isCollapsed ? '▼' : '▲'}
        </button>
      </div>
      
      {!isCollapsed && (
        <div className="upcoming-events-content">
          {upcomingEvents.length > 0 ? (
            upcomingEvents.map((event, index) => (
              <div key={index} className="upcoming-event-card">
                <div className="event-date">
                  <div className="event-day">
                    {moment(event.start).format('DD')}
                  </div>
                  <div className="event-month">
                    {moment(event.start).format('MMM')}
                  </div>
                </div>
                <div className="event-details">
                  <div className="event-title">{event.title}</div>
                  <div className="event-time">
                    {moment(event.start).format('HH:mm')} - {moment(event.end).format('HH:mm')}
                  </div>
                  <div className="event-description">
                    {event.description}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="no-events">No upcoming events</div>
          )}
        </div>
      )}
    </div>
  );
}; 