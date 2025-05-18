from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
import json
import os
import logging
from dotenv import load_dotenv
import uuid
from datetime import datetime
import time
import traceback
import openai

# Load environment variables first, before imports that might use them
load_dotenv()

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

# IMPORTANT: Handle CORS properly - this is the critical part!
# First, apply a more permissive CORS policy
# Replace your existing CORS configuration with this
CORS(app, 
     resources={r"/*": {
        "origins": "*", 
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "User-Email"]
     }})

# Add this after_request handler after the CORS configuration
@app.after_request
def after_request(response):
    # Remove any existing Access-Control-Allow-Origin headers to prevent duplicates
    if response.headers.get("Access-Control-Allow-Origin"):
        del response.headers["Access-Control-Allow-Origin"]
    
    # Set a single Access-Control-Allow-Origin header
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization, User-Email")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
    return response

# In-memory storage for events
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

# Initialize OpenAI client
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    openai.api_key = openai_api_key
    logger.info(f"OpenAI API key loaded (length: {len(openai_api_key)})")
else:
    logger.warning("OpenAI API key not found in environment variables.")

@app.route('/api/events', methods=['GET'])
def get_events():
    logger.info("GET /api/events endpoint called")
    logger.info(f"Request headers: {dict(request.headers)}")
    
    # Check for user_id in query parameters - this implements RLS-like filtering
    user_id = request.args.get('user_id')
    user_email = request.headers.get('User-Email')
    
    if user_id:
        logger.info(f"Filtering events for user: {user_id} ({user_email})")
        # Filter events by user_id if provided
        filtered_events = [
            event for event in events 
            if event.get('user_id') == user_id or not event.get('user_id')
        ]
        return jsonify(filtered_events)
    else:
        # If no user_id provided, return all events (for admin access or when not using RLS)
        logger.warning("No user_id provided, returning all events")
        return jsonify(events)

@app.route('/api/events', methods=['POST'])
def create_event():
    logger.info("POST /api/events endpoint called")
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Request data: {request.data}")
    
    event = request.json
    
    # Generate a unique ID if not provided
    if 'id' not in event:
        event['id'] = str(uuid.uuid4())
    
    # Add user_id from the authentication header if not already set
    if 'user_id' not in event:
        # Get user_id from Authorization header (Bearer token)
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            user_id = auth_header.split(' ')[1]
            event['user_id'] = user_id
            logger.info(f"Added user_id {user_id} to event")
    
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
                # Validate required fields for create action
                if not all(k in event for k in ['title', 'start', 'end']):
                    missing = [k for k in ['title', 'start', 'end'] if k not in event]
                    logger.warning(f"Event is missing required fields: {missing}")
                    return jsonify({
                        'message': f"I couldn't add your event because some required information was missing: {', '.join(missing)}. Please try again with complete details.",
                        'event': None
                    })
                
                # Add event to storage
                logger.info("Creating new event")
                events.append(event)
                save_events()
                
                return jsonify({
                    'message': response_message,
                    'event': event,
                    'action': action
                })
            
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
    
    response = jsonify({
        'status': 'ok',
        'api_key_configured': has_api_key,
        'api_key_length': key_length,
        'python_version': os.sys.version,
        'cors': 'enabled',
        'timestamp': datetime.now().isoformat(),
        'request_path': request.path
    })
    
    # Explicitly add CORS headers to this response
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
    
    return response

@app.route('/', methods=['GET'])
def root():
    logger.info("Root endpoint called")
    return jsonify({
        'status': 'ok',
        'message': 'AI Calendar Backend API is running',
        'version': '1.0.0',
        'cors': 'Enabled for Vercel deployment',
        'endpoints': {
            'health': '/api/health',
            'events': '/api/events',
            'chat': '/api/chat'
        }
    })

if __name__ == '__main__':
    # Get port from environment variable (useful for deployment)
    port = int(os.environ.get("PORT", 9999))
    logger.info(f"Starting Flask server on port {port}")
    try:
        app.run(host='0.0.0.0', debug=False, port=port)
    except Exception as e:
        logger.error(f"Failed to start Flask server: {e}")
        print(f"Error starting server: {e}") 