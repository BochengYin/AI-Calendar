from flask import Flask, jsonify, request
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

# Add ProxyFix middleware to handle Render's proxy correctly
try:
    from werkzeug.middleware.proxy_fix import ProxyFix
    # Handle various proxy setups (X-Forwarded-For, etc.)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    logger.info("ProxyFix middleware applied")
except ImportError:
    logger.warning("ProxyFix middleware not available")

# Update CORS configuration to allow requests from Vercel
CORS(app, resources={r"/*": {"origins": [
    "https://ai-calendar-sigma.vercel.app", 
    "https://ai-calendar-git-main-bochengs-projects.vercel.app",
    "http://localhost:3000", 
    "*"
]}}, 
     supports_credentials=True,
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Origin"])
logger.info("Flask app initialized with enhanced CORS support for Vercel")

# Get port from environment variable (useful for deployment)
port = int(os.environ.get("PORT", 8000))
logger.info(f"Using PORT environment variable: {port}")

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

# Initialize OpenAI client - direct load from .env
try:
    import os.path
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('OPENAI_API_KEY='):
                    openai_api_key = line.split('=', 1)[1].strip()
                    if openai_api_key.startswith('"') and openai_api_key.endswith('"'):
                        openai_api_key = openai_api_key[1:-1]
                    elif openai_api_key.startswith("'") and openai_api_key.endswith("'"):
                        openai_api_key = openai_api_key[1:-1]
                    break
            else:
                openai_api_key = None
    else:
        logger.info("No .env file found, using environment variables")
        openai_api_key = os.getenv("OPENAI_API_KEY")
except Exception as e:
    logger.error(f"Error loading API key directly from .env: {e}")
    openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    openai.api_key = openai_api_key
    logger.info(f"OpenAI API key loaded (length: {len(openai_api_key)})")
else:
    logger.warning("OpenAI API key not found in environment variables.")

@app.route('/api/events', methods=['GET'])
def get_events():
    logger.info("GET /api/events endpoint called")
    
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
            
            elif action == 'delete':
                # For delete, we only need title and optionally other fields to help identify the event
                if 'title' not in event:
                    logger.warning("Delete request missing title field")
                    return jsonify({
                        'message': "I couldn't identify which event to delete. Please specify the event title.",
                        'event': None
                    })
                
                # Find and delete the event
                logger.info(f"Attempting to delete event: {event.get('title')}")
                deleted = False
                
                # Get event details for matching
                title = event.get('title', '').lower()
                event_date = event.get('start', None)
                
                # Try to find the event to delete using multiple matching strategies
                # 1. First try exact title match
                for i, existing_event in enumerate(events):
                    if existing_event.get('title', '').lower() == title:
                        event_to_delete = events.pop(i)
                        logger.info(f"Event deleted (exact title match): {event_to_delete}")
                        deleted = True
                        save_events()
                        break
                
                # 2. If not found and we have a date, try date-based matching
                if not deleted and event_date:
                    logger.info(f"Trying date-based matching for: {event_date}")
                    event_date_prefix = event_date.split('T')[0]  # Get just the date part
                    
                    for i, existing_event in enumerate(events):
                        existing_date = existing_event.get('start', '')
                        # Check if dates match
                        if existing_date and existing_date.startswith(event_date_prefix):
                            event_to_delete = events.pop(i)
                            logger.info(f"Event deleted (date match): {event_to_delete}")
                            deleted = True
                            save_events()
                            break
                
                # 3. Try partial title matching as a last resort
                if not deleted and len(events) > 0:
                    logger.info("Trying partial title matching")
                    
                    # Simple word overlap scoring
                    best_match_idx = -1
                    best_match_score = 0
                    title_words = set(title.split())
                    
                    for i, existing_event in enumerate(events):
                        existing_title = existing_event.get('title', '').lower()
                        existing_words = set(existing_title.split())
                        
                        # Calculate word overlap
                        overlap = len(title_words.intersection(existing_words))
                        
                        if overlap > best_match_score:
                            best_match_score = overlap
                            best_match_idx = i
                    
                    # If we found a reasonable match (at least one word in common)
                    if best_match_score > 0:
                        event_to_delete = events.pop(best_match_idx)
                        logger.info(f"Event deleted (partial match with score {best_match_score}): {event_to_delete}")
                        deleted = True
                        save_events()
                
                # 4. Time-based fallback for "meeting tomorrow" type requests
                if not deleted and event_date:
                    logger.info("Trying time-based fallback for events on specific date")
                    event_date_prefix = event_date.split('T')[0]  # Get just the date part
                    
                    for i, existing_event in enumerate(events):
                        existing_date = existing_event.get('start', '')
                        existing_title = existing_event.get('title', '').lower()
                        
                        # If it's any kind of event on the specified date
                        if (existing_date and existing_date.startswith(event_date_prefix)):
                            event_to_delete = events.pop(i)
                            logger.info(f"Event deleted (date-based fallback): {event_to_delete}")
                            deleted = True
                            save_events()
                            break
                
                if not deleted:
                    logger.warning(f"Could not find event to delete matching: {event}")
                    response_message += " However, I couldn't find the exact event to delete."
                    
                    # Provide helpful information about existing events
                    if len(events) > 0:
                        response_message += " Here are your current events: "
                        for e in events[:3]:  # List up to 3 events
                            event_info = f"{e.get('title')} on {e.get('start').split('T')[0]}"
                            response_message += event_info + ", "
                        response_message = response_message.rstrip(", ") + "."
            
            elif action == 'reschedule':
                # Validate required fields for reschedule action
                if not all(k in event for k in ['title', 'start', 'end']):
                    missing = [k for k in ['title', 'start', 'end'] if k not in event]
                    logger.warning(f"Reschedule event is missing required fields: {missing}")
                    return jsonify({
                        'message': f"I couldn't reschedule your event because some required information was missing: {', '.join(missing)}. Please try again with complete details.",
                        'event': None
                    })
                
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
@app.route('/health', methods=['GET'])  # Add alternate route without /api prefix
def health_check():
    logger.info("Health check endpoint called")
    has_api_key = bool(os.getenv('OPENAI_API_KEY'))
    key_length = len(os.getenv('OPENAI_API_KEY') or '')
    
    # Log request information for debugging
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Request Path: {request.path}")
    logger.info(f"Request Method: {request.method}")
    
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

# Add direct routes without /api prefix - these are crucial fallbacks for Render
@app.route('/', methods=['GET'])
def root():
    logger.info("Root endpoint called")
    return jsonify({
        'status': 'ok',
        'message': 'AI Calendar Backend API is running',
        'version': '1.0.0',
        'cors': 'Enabled for Vercel deployment',
        'endpoints': {
            'root_health': '/health',
            'root_events': '/events',
            'root_chat': '/chat',
            'api_health': '/api/health',
            'api_events': '/api/events',
            'api_chat': '/api/chat'
        }
    })

@app.route('/api', methods=['GET'])
def api_root():
    logger.info("API root endpoint called")
    return jsonify({
        'status': 'ok',
        'message': 'AI Calendar API is available',
        'endpoints': {
            'health': '/api/health',
            'events': '/api/events',
            'chat': '/api/chat'
        }
    })

# Absolute top level handler for the health check
@app.route('/healthcheck', methods=['GET'])
def alt_health_check():
    logger.info("Alternate health check endpoint called")
    return jsonify({
        'status': 'ok',
        'message': 'Backend is running',
        'timestamp': datetime.now().isoformat()
    })

# Catch-all route for any undefined routes
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def catch_all(path):
    logger.info(f"Catch-all route hit: /{path}")
    
    # Convert the path to a standardized format
    path = path.lower().strip('/')
    
    # Special handling for paths that should start with /api but don't
    if path in ['api/health', 'health', 'api/events', 'events', 'api/chat', 'chat', 'api']:
        logger.info(f"Redirecting /{path} to appropriate handler")
        
        # Route to the appropriate handler based on path and method
        if path in ['api/health', 'health'] and request.method == 'GET':
            return health_check()
        elif path in ['api/events', 'events']:
            if request.method == 'GET':
                return get_events()
            elif request.method == 'POST':
                return create_event()
        elif path in ['api/chat', 'chat'] and request.method == 'POST':
            return chat()
        elif path == 'api' and request.method == 'GET':
            return api_root()
    
    # Log all request details for debugging
    logger.warning(f"404 for path: /{path}")
    logger.warning(f"Full URL: {request.url}")
    logger.warning(f"Method: {request.method}")
    logger.warning(f"Headers: {dict(request.headers)}")
    
    # Default 404 response with helpful information
    return jsonify({
        'status': 'error',
        'message': f'Route not found: /{path}',
        'available_endpoints': {
            'root': '/',
            'api': '/api',
            'api_health': '/api/health',
            'health': '/health',
            'api_events': '/api/events',
            'events': '/events',
            'api_chat': '/api/chat',
            'chat': '/chat'
        },
        'request_details': {
            'path': path,
            'method': request.method,
            'url': request.url
        }
    }), 404

# Add an explicit OPTIONS handler for CORS preflight requests
@app.route('/api/health', methods=['OPTIONS'])
@app.route('/health', methods=['OPTIONS'])  # Alternate route without /api prefix
@app.route('/api/events', methods=['OPTIONS'])
@app.route('/events', methods=['OPTIONS'])  # Alternate route without /api prefix
@app.route('/api/chat', methods=['OPTIONS'])
@app.route('/chat', methods=['OPTIONS'])  # Alternate route without /api prefix
def handle_options():
    response = jsonify({'status': 'ok'})
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    return response

# Add explicit versions of all routes without the /api prefix
@app.route('/events', methods=['GET'])
def get_events_alt():
    logger.info("GET /events endpoint called (alternate route)")
    return get_events()

@app.route('/events', methods=['POST'])
def create_event_alt():
    logger.info("POST /events endpoint called (alternate route)")
    return create_event()

@app.route('/events/<event_id>', methods=['DELETE'])
def delete_event_alt(event_id):
    logger.info(f"DELETE /events/{event_id} endpoint called (alternate route)")
    return delete_event(event_id)

@app.route('/events/<event_id>', methods=['PUT'])
def update_event_alt(event_id):
    logger.info(f"PUT /events/{event_id} endpoint called (alternate route)")
    return update_event(event_id)

@app.route('/chat', methods=['POST'])
def chat_alt():
    logger.info("POST /chat endpoint called (alternate route)")
    return chat()

if __name__ == '__main__':
    logger.info(f"Starting Flask server on port {port}")
    try:
        app.run(host='0.0.0.0', debug=False, port=port)
    except Exception as e:
        logger.error(f"Failed to start Flask server: {e}")
        print(f"Error starting server: {e}") 