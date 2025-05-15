from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import logging
from dotenv import load_dotenv
import uuid

# Load environment variables first, before imports that might use them
load_dotenv()

# Log environment setup
print(f"Starting backend server with API key configured: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("backend.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Now import modules that might use environment variables
try:
    from api.chatgpt import process_event_request, test_openai_api
except ImportError as e:
    print(f"Error importing modules: {e}")
    # Define fallback functions if import fails
    def process_event_request(message):
        return None, "API function not available due to import error"
    def test_openai_api():
        return False, "API test function not available due to import error"

logger.info("Environment variables loaded")
logger.debug(f"OPENAI_API_KEY configured: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
logger.debug(f"OPENAI_API_KEY length: {len(os.getenv('OPENAI_API_KEY') or '')}")

app = Flask(__name__)
# Update CORS configuration to be more permissive
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
logger.info("Flask app initialized with enhanced CORS support")

# In-memory storage for events
# In a production app, you'd use a database instead
events = []

# Load saved events if exists
def load_events():
    try:
        if os.path.exists('events.json'):
            with open('events.json', 'r') as f:
                loaded_events = json.load(f)
                # Ensure all events have IDs
                for event in loaded_events:
                    if 'id' not in event:
                        event['id'] = str(uuid.uuid4())
                logger.info(f"Loaded {len(loaded_events)} events from events.json")
                return loaded_events
    except Exception as e:
        logger.error(f"Error loading events: {e}")
    logger.info("No events loaded, starting with empty events list")
    return []

# Save events to file
def save_events():
    try:
        with open('events.json', 'w') as f:
            json.dump(events, f)
            logger.info(f"Saved {len(events)} events to events.json")
    except Exception as e:
        logger.error(f"Error saving events: {e}")

# Load events on startup
events = load_events()

@app.route('/api/events', methods=['GET'])
def get_events():
    logger.info("GET /api/events endpoint called")
    return jsonify(events)

@app.route('/api/events', methods=['POST'])
def create_event():
    logger.info("POST /api/events endpoint called")
    event = request.json
    # Generate a unique ID if not provided
    if 'id' not in event:
        event['id'] = str(uuid.uuid4())
    logger.debug(f"Received event: {event}")
    events.append(event)
    save_events()
    return jsonify(event), 201

@app.route('/api/events/<event_id>', methods=['DELETE'])
def delete_event(event_id):
    logger.info(f"DELETE /api/events/{event_id} endpoint called")
    
    # Find the event with the given ID
    event_to_delete = None
    for i, event in enumerate(events):
        if str(event.get('id')) == event_id:
            event_to_delete = events.pop(i)
            break
    
    if event_to_delete:
        logger.info(f"Event deleted: {event_to_delete}")
        save_events()
        return jsonify({
            'status': 'success',
            'message': 'Event deleted successfully',
            'deleted_event': event_to_delete
        })
    else:
        logger.error(f"Event with ID {event_id} not found")
        return jsonify({
            'status': 'error',
            'message': f'Event with ID {event_id} not found'
        }), 404

@app.route('/api/events/<event_id>', methods=['PUT'])
def update_event(event_id):
    logger.info(f"PUT /api/events/{event_id} endpoint called")
    updated_event = request.json
    
    # Find the event with the given ID
    event_updated = False
    for i, event in enumerate(events):
        if str(event.get('id')) == event_id:
            # Preserve the ID
            updated_event['id'] = event_id
            # Check if this is a reschedule (dates changed)
            is_reschedule = (event.get('start') != updated_event.get('start') or 
                            event.get('end') != updated_event.get('end'))
            
            # If it's a reschedule, mark the original event
            if is_reschedule:
                updated_event['rescheduled_from'] = {
                    'start': event.get('start'),
                    'end': event.get('end')
                }
                
            # Replace the event with the updated one
            events[i] = updated_event
            event_updated = True
            break
    
    if event_updated:
        logger.info(f"Event updated: {updated_event}")
        save_events()
        return jsonify({
            'status': 'success',
            'message': 'Event updated successfully',
            'updated_event': updated_event
        })
    else:
        logger.error(f"Event with ID {event_id} not found")
        return jsonify({
            'status': 'error',
            'message': f'Event with ID {event_id} not found'
        }), 404

@app.route('/api/chat', methods=['POST'])
def chat():
    logger.info("POST /api/chat endpoint called")
    message = request.json.get('message', '')
    logger.debug(f"Received message: {message}")
    
    # Process the message using ChatGPT to extract event details
    try:
        event, response_message = process_event_request(message)
        
        logger.debug(f"ChatGPT response - Event: {event}, Message: {response_message}")
        
        if event:
            action = event.get('action', 'create')
            logger.debug(f"Action to perform: {action}")
            
            if action == 'create':
                # Add event to storage
                logger.info("Creating new event")
                events.append(event)
                save_events()
            
            elif action == 'delete':
                # Find and delete the event
                logger.info(f"Attempting to delete event: {event.get('title')}")
                deleted = False
                
                # Try to find the event to delete
                for i, existing_event in enumerate(events):
                    # Match by title (can be enhanced with more matching criteria)
                    if existing_event.get('title', '').lower() == event.get('title', '').lower():
                        event_to_delete = events.pop(i)
                        logger.info(f"Event deleted: {event_to_delete}")
                        deleted = True
                        save_events()
                        break
                
                if not deleted:
                    logger.warning(f"Could not find event to delete with title: {event.get('title')}")
                    response_message += " However, I couldn't find the exact event to delete."
            
            elif action == 'reschedule':
                # Find and update the event
                logger.info(f"Attempting to reschedule event: {event.get('title')}")
                rescheduled = False
                
                # Copy relevant fields for the new event
                updated_event = {
                    'id': str(uuid.uuid4()),
                    'title': event.get('title'),
                    'start': event.get('start'),
                    'end': event.get('end'),
                    'allDay': event.get('allDay', False),
                    'description': event.get('description', '')
                }
                
                # Try to find the event to reschedule
                for i, existing_event in enumerate(events):
                    # Match by title (can be enhanced with more matching criteria)
                    if existing_event.get('title', '').lower() == event.get('title', '').lower():
                        # Remove the old event
                        events.pop(i)
                        # Add the new event
                        events.append(updated_event)
                        logger.info(f"Event rescheduled: {updated_event}")
                        rescheduled = True
                        save_events()
                        break
                
                if not rescheduled:
                    logger.warning(f"Could not find event to reschedule with title: {event.get('title')}")
                    # Just add as a new event
                    events.append(updated_event)
                    logger.info(f"Added as new event instead: {updated_event}")
                    save_events()
                    response_message += " I couldn't find the original event, so I've created a new one with the updated schedule."
            
            return jsonify({
                'message': response_message,
                'event': event,
                'action': action
            })
        
        logger.info("No event extracted from the message")
        return jsonify({
            'message': response_message
        })
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        return jsonify({
            'message': f"Sorry, an error occurred: {str(e)}"
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    logger.info("Health check endpoint called")
    has_api_key = bool(os.getenv('OPENAI_API_KEY'))
    key_length = len(os.getenv('OPENAI_API_KEY') or '')
    return jsonify({
        'status': 'ok',
        'api_key_configured': has_api_key,
        'api_key_length': key_length,
        'python_version': os.sys.version
    })

@app.route('/api/test-openai', methods=['GET'])
def test_openai():
    logger.info("Testing OpenAI API connection")
    success, message = test_openai_api()
    if success:
        logger.info("OpenAI API test succeeded")
        return jsonify({
            'status': 'success',
            'message': message
        })
    else:
        logger.error(f"OpenAI API test failed: {message}")
        return jsonify({
            'status': 'error',
            'message': message
        }), 500

if __name__ == '__main__':
    logger.info("Starting Flask server on port 8000")
    try:
        app.run(debug=True, port=8000)
    except Exception as e:
        logger.error(f"Failed to start Flask server: {e}")
        print(f"Error starting server: {e}") 