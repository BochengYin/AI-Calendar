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
from supabase_client import get_supabase_client

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

# Functions for local JSON storage (keeping for debugging and fallback)
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

# Save events to both JSON file and Supabase (if configured)
def save_events():
    # Save to JSON file (for debugging and fallback)
    try:
        with open('events.json', 'w') as f:
            json.dump(events, f)
            logger.info(f"Saved {len(events)} events to events.json")
    except Exception as e:
        logger.error(f"Error saving events to JSON: {e}")
    
    # Save to Supabase if available
    try:
        supabase = get_supabase_client()
        if supabase:
            # This is a simplified approach - in production you'd handle upserts properly
            # First clear existing events (not ideal for production)
            # supabase.table('events').delete().execute()
            
            # Then insert all events
            # NOTE: In a real app, you'd track which events need to be inserted/updated/deleted
            # instead of this bulk approach
            logger.info(f"Attempting to sync {len(events)} events to Supabase")
            batch_size = 20  # Process in batches to avoid request size limits
            
            for i in range(0, len(events), batch_size):
                batch = events[i:i+batch_size]
                
                # Only insert events that have all required fields
                valid_events = []
                for event in batch:
                    # Make sure event has all required fields for Supabase
                    if not all(k in event for k in ['title', 'start', 'end']):
                        logger.warning(f"Skipping event missing required fields: {event}")
                        continue
                    
                    # Prepare a clean version of the event for Supabase
                    clean_event = {
                        'id': event.get('id'),
                        'title': event.get('title'),
                        'description': event.get('description', ''),
                        'start': event.get('start'),
                        'end': event.get('end'),
                        'allDay': event.get('allDay', False),
                        'user_id': event.get('user_id')
                    }
                    valid_events.append(clean_event)
                
                if valid_events:
                    try:
                        # Using upsert to handle both inserts and updates
                        response = supabase.table('events').upsert(valid_events).execute()
                        logger.info(f"Synced batch of {len(valid_events)} events to Supabase")
                    except Exception as e:
                        logger.error(f"Error upserting events to Supabase: {e}")
            
            logger.info("Finished syncing events to Supabase")
    except Exception as e:
        logger.error(f"Error saving events to Supabase: {e}")
        logger.error(traceback.format_exc())

# Function to load events from Supabase
def load_events_from_supabase():
    try:
        supabase = get_supabase_client()
        if not supabase:
            logger.warning("Supabase client not available, using JSON file only")
            return None
            
        response = supabase.table('events').select('*').execute()
        if response.data:
            logger.info(f"Loaded {len(response.data)} events from Supabase")
            return response.data
        else:
            logger.info("No events found in Supabase")
            return []
    except Exception as e:
        logger.error(f"Error loading events from Supabase: {e}")
        logger.error(traceback.format_exc())
        return None

# Try to load events from Supabase first, fall back to JSON if needed
supabase_events = load_events_from_supabase()
if supabase_events is not None:
    events = supabase_events
    # Also save to JSON for debugging
    try:
        with open('events.json', 'w') as f:
            json.dump(events, f)
            logger.info(f"Saved {len(events)} events from Supabase to events.json")
    except Exception as e:
        logger.error(f"Error saving Supabase events to JSON: {e}")
else:
    # Fall back to JSON file
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
    
    # Check for user_id in query parameters
    user_id = request.args.get('user_id')
    user_email = request.headers.get('User-Email')
    
    # Try to get events from Supabase first
    try:
        supabase = get_supabase_client()
        if supabase:
            logger.info(f"Fetching events from Supabase for user: {user_id}")
            query = supabase.table('events').select('*')
            
            # Apply user filtering if needed (RLS should handle this automatically in Supabase)
            if user_id:
                query = query.eq('user_id', user_id)
                
            response = query.execute()
            
            if response.data:
                logger.info(f"Returned {len(response.data)} events from Supabase")
                return jsonify(response.data)
    except Exception as e:
        logger.error(f"Error fetching events from Supabase: {e}")
        logger.error(traceback.format_exc())
    
    # Fall back to local JSON data if Supabase fails
    logger.info("Falling back to local events data")
    if user_id:
        logger.info(f"Filtering events for user: {user_id} ({user_email})")
        # Filter events by user_id if provided
        filtered_events = [
            event for event in events 
            if event.get('user_id') == user_id or not event.get('user_id')
        ]
        return jsonify(filtered_events)
    else:
        # If no user_id provided, return all events (for admin access)
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
    
    # Try to save to Supabase first
    try:
        supabase = get_supabase_client()
        if supabase:
            # Prepare clean event for Supabase
            clean_event = {
                'id': event.get('id'),
                'title': event.get('title'),
                'description': event.get('description', ''),
                'start': event.get('start'),
                'end': event.get('end'),
                'allDay': event.get('allDay', False),
                'user_id': event.get('user_id')
            }
            
            logger.info(f"Inserting event into Supabase: {clean_event}")
            response = supabase.table('events').insert(clean_event).execute()
            logger.info(f"Supabase response: {response.data}")
            
            if response.data:
                # Also add to local events array for backup
                events.append(event)
                save_events()  # This now only updates the JSON file
                return jsonify(response.data[0]), 201
    except Exception as e:
        logger.error(f"Error saving event to Supabase: {e}")
        logger.error(traceback.format_exc())
    
    # Fall back to just local JSON if Supabase fails
    logger.info("Falling back to local JSON storage for event")
    events.append(event)
    save_events()
    return jsonify(event), 201

@app.route('/api/events/<event_id>', methods=['DELETE'])
def delete_event(event_id):
    logger.info(f"DELETE /api/events/{event_id} endpoint called")
    
    deleted_from_supabase = False
    
    # Try to delete from Supabase first
    try:
        supabase = get_supabase_client()
        if supabase:
            logger.info(f"Deleting event {event_id} from Supabase")
            response = supabase.table('events').delete().eq('id', event_id).execute()
            
            if response.data:
                logger.info(f"Successfully deleted event from Supabase: {response.data}")
                deleted_from_supabase = True
            else:
                logger.warning(f"Event {event_id} not found in Supabase")
    except Exception as e:
        logger.error(f"Error deleting event from Supabase: {e}")
        logger.error(traceback.format_exc())
    
    # Find and delete from local events list
    event_to_delete = None
    for i, event in enumerate(events):
        if str(event.get('id')) == event_id:
            event_to_delete = events.pop(i)
            break
    
    if event_to_delete or deleted_from_supabase:
        if event_to_delete:
            logger.info(f"Event deleted from local storage: {event_to_delete}")
            save_events()  # Update JSON file
        
        return jsonify({
            'status': 'success',
            'message': 'Event deleted successfully',
            'deleted_event': event_to_delete if event_to_delete else {'id': event_id}
        })
    else:
        logger.error(f"Event with ID {event_id} not found in either storage")
        return jsonify({
            'status': 'error',
            'message': f'Event with ID {event_id} not found'
        }), 404

@app.route('/api/events/<event_id>', methods=['PUT'])
def update_event(event_id):
    logger.info(f"PUT /api/events/{event_id} endpoint called")
    updated_event = request.json
    
    # Make sure ID is preserved
    updated_event['id'] = event_id
    
    updated_in_supabase = False
    
    # Try to update in Supabase first
    try:
        supabase = get_supabase_client()
        if supabase:
            # Prepare clean event for Supabase
            clean_event = {
                'id': event_id,
                'title': updated_event.get('title'),
                'description': updated_event.get('description', ''),
                'start': updated_event.get('start'),
                'end': updated_event.get('end'),
                'allDay': updated_event.get('allDay', False),
                'user_id': updated_event.get('user_id')
            }
            
            logger.info(f"Updating event in Supabase: {clean_event}")
            response = supabase.table('events').update(clean_event).eq('id', event_id).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Successfully updated event in Supabase: {response.data}")
                updated_in_supabase = True
            else:
                logger.warning(f"Event {event_id} not found in Supabase or no changes made")
    except Exception as e:
        logger.error(f"Error updating event in Supabase: {e}")
        logger.error(traceback.format_exc())
    
    # Update in local events list
    event_updated = False
    for i, event in enumerate(events):
        if str(event.get('id')) == event_id:
            events[i] = updated_event
            event_updated = True
            break
    
    if event_updated or updated_in_supabase:
        if event_updated:
            logger.info(f"Event updated in local storage: {updated_event}")
            save_events()  # Update JSON file
        
        return jsonify({
            'status': 'success',
            'message': 'Event updated successfully',
            'updated_event': updated_event
        })
    else:
        logger.error(f"Event with ID {event_id} not found in either storage")
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
                
                # Generate ID if needed
                if 'id' not in event:
                    event['id'] = str(uuid.uuid4())
                
                # Try to save to Supabase first
                supabase_success = False
                try:
                    supabase = get_supabase_client()
                    if supabase:
                        # Prepare clean event for Supabase
                        clean_event = {
                            'id': event.get('id'),
                            'title': event.get('title'),
                            'description': event.get('description', ''),
                            'start': event.get('start'),
                            'end': event.get('end'),
                            'allDay': event.get('allDay', False),
                            'user_id': event.get('user_id')
                        }
                        
                        logger.info(f"Inserting event from chat into Supabase: {clean_event}")
                        response = supabase.table('events').insert(clean_event).execute()
                        
                        if response.data:
                            logger.info(f"Successfully saved chat event to Supabase: {response.data}")
                            supabase_success = True
                except Exception as e:
                    logger.error(f"Error saving chat event to Supabase: {e}")
                    logger.error(traceback.format_exc())
                
                # Add to local storage as well
                logger.info("Adding chat event to local storage")
                events.append(event)
                save_events()  # This now only updates the JSON file if Supabase failed
                
                return jsonify({
                    'message': response_message,
                    'event': event,
                    'action': action,
                    'storage': 'dual' if supabase_success else 'local_only'
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