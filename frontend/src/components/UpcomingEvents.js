import React, { useState } from 'react';
import moment from 'moment';

export const UpcomingEvents = ({ events }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Filter events: remove deleted ones and filter duplicates by title + date 
  const upcomingEvents = events
    // .filter(event => !event.isDeleted) // Remove deleted events
    .sort((a, b) => moment(a.start).diff(moment(b.start))) // Sort by date
    .reduce((unique, event) => {
      // Avoid duplicates with same title and same date
      const eventDate = moment(event.start).format('YYYY-MM-DD');
      // Check if we already have an event with this title on this date
      const exists = unique.some(e => {
        const existingDate = moment(e.start).format('YYYY-MM-DD');
        return e.title === event.title && existingDate === eventDate;
      });
      
      if (!exists) {
        unique.push(event);
      }
      
      return unique;
    }, []);

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
            upcomingEvents.map((event, index) => {
              const cardClassName = `upcoming-event-card ${event.isDeleted ? 'deleted-event' : ''}`;
              const titleStyle = event.isDeleted ? { textDecoration: 'line-through' } : {};

              return (
                <div key={event.id || index} className={cardClassName}>
                <div className="event-date">
                  <div className="event-day">
                    {moment(event.start).format('DD')}
                  </div>
                  <div className="event-month">
                    {moment(event.start).format('MMM')}
                  </div>
                </div>
                <div className="event-details">
                    <div className="event-title" style={titleStyle}>{event.title}</div>
                  <div className="event-time">
                    {moment(event.start).format('HH:mm')} - {moment(event.end).format('HH:mm')}
                  </div>
                  <div className="event-description">
                    {event.description}
                  </div>
                </div>
              </div>
              );
            })
          ) : (
            <div className="no-events">No upcoming events</div>
          )}
        </div>
      )}
    </div>
  );
}; 