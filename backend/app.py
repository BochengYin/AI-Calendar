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
import random # Added for with_retry
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

# Define with_retry function here
def with_retry(func, max_retries=3, base_delay=1):
    """
    Execute a function with retry logic.
    
    Args:
        func: The function to execute
        max_retries: Maximum number of retries
        base_delay: Base delay between retries (will be exponentially increased)
        
    Returns:
        The result of the function call
    """
    retries = 0
    last_exception = None
    
    while retries <= max_retries:
        try:
            return func()
        except Exception as e:
            last_exception = e
            retries += 1
            
            if retries > max_retries:
                break
                
            # Exponential backoff with jitter
            delay = base_delay * (2 ** (retries - 1)) + random.uniform(0, 0.5)
            logger.warning(f"Operation failed, retrying in {delay:.2f}s... ({retries}/{max_retries})")
            logger.warning(f"Error: {str(e)}")
            time.sleep(delay)
    
    # If we've exhausted all retries, raise the last exception
    logger.error(f"All {max_retries} retries failed for function {func.__name__ if hasattr(func, '__name__') else 'unknown'}")
    raise last_exception

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
                        'all_day': event.get('allDay', False),
                        'user_id': event.get('user_id'),
                        'user_email': event.get('user_email')
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
            
            # Convert snake_case fields from Supabase to camelCase for frontend
            converted_events = []
            for event in response.data:
                # Create an adapted version of the event with proper field names
                converted_event = {
                    'id': event.get('id'),
                    'title': event.get('title'),
                    'description': event.get('description', ''),
                    'start': event.get('start'),
                    'end': event.get('end'),
                    'allDay': event.get('all_day', False),  # Convert from snake_case to camelCase
                    'user_id': event.get('user_id'),
                    'user_email': event.get('user_email')
                }
                
                # Add any additional fields from the database
                if event.get('is_deleted'):
                    converted_event['isDeleted'] = event.get('is_deleted')
                if event.get('is_rescheduled'):
                    converted_event['isRescheduled'] = event.get('is_rescheduled')
                if event.get('rescheduled_from'):
                    converted_event['rescheduledFrom'] = event.get('rescheduled_from')
                
                converted_events.append(converted_event)
                
            logger.debug(f"Successfully converted {len(converted_events)} events from Supabase format")
            return converted_events
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
            
            # Use retry logic for Supabase query
            def fetch_events():
                query = supabase.table('events').select('*')
                
                # Apply user filtering if needed (RLS should handle this automatically in Supabase)
                if user_id:
                    query = query.eq('user_id', user_id)
                    
                return query.execute()
            
            # Use the retry function to make the query more resilient
            try:
                response = with_retry(fetch_events) # Call local with_retry
                
                if response.data:
                    logger.info(f"Returned {len(response.data)} events from Supabase")
                    
                    # Backup fetched events to local storage to avoid disappearing events
                    global events
                    if len(response.data) > 0:
                        logger.info(f"Updating local events cache with {len(response.data)} events from Supabase")
                        # Convert from snake_case to camelCase for frontend
                        local_events = []
                        for event in response.data:
                            local_event = {
                                'id': event.get('id'),
                                'title': event.get('title'),
                                'description': event.get('description', ''),
                                'start': event.get('start'),
                                'end': event.get('end'),
                                'allDay': event.get('all_day', False),
                                'user_id': event.get('user_id'),
                                'user_email': event.get('user_email')
                            }
                            if event.get('is_deleted'):
                                local_event['isDeleted'] = event.get('is_deleted')
                            if event.get('is_rescheduled'):
                                local_event['isRescheduled'] = event.get('is_rescheduled')
                            local_events.append(local_event)
                        
                        # Update the global events list but filter for this user if user_id exists
                        if user_id:
                            # Keep events that belong to other users
                            other_events = [e for e in events if e.get('user_id') and e.get('user_id') != user_id]
                            # Then add the events for this user
                            events = other_events + local_events
                        else:
                            events = local_events
                            
                        # Save to JSON file for backup
                        with open('events.json', 'w') as f:
                            json.dump(events, f)
                            logger.info(f"Saved {len(events)} events to events.json")
                    
                    return jsonify(response.data)
            except Exception as e:
                logger.error(f"Error with retry fetching events from Supabase: {e}")
                logger.error(traceback.format_exc())
                # Continue to fallback mechanism
    except Exception as e:
        logger.error(f"Error fetching events from Supabase: {e}")
        logger.error(traceback.format_exc())
    
    # Fall back to local JSON data if Supabase fails
    logger.info("Falling back to local events data")
    # Filter for the requested user if needed
    if user_id:
        user_email_str = user_email if user_email else "unknown"
        logger.info(f"Filtering events for user: {user_id} ({user_email_str})")
        user_events = [event for event in events if event.get('user_id') == user_id]
        return jsonify(user_events)
    else:
        return jsonify(events)

@app.route('/api/events', methods=['POST'])
def create_event():
    logger.info("POST /api/events endpoint called")
    event = request.json
    
    # Generate ID if not provided
    if 'id' not in event:
        event['id'] = str(uuid.uuid4())
    
    # Add user_id if available in the auth header
    if 'user_id' not in event:
        auth_header = request.headers.get('Authorization')
        user_email = request.headers.get('User-Email')
        
        if auth_header and auth_header.startswith('Bearer '):
            # Extract JWT token
            token = auth_header.split(' ')[1]
            
            # If user_id is already provided in the request body, use that
            if 'user_id' in event:
                user_id = event['user_id']
                logger.info(f"Using provided user_id: {user_id}")
            else:
                # Otherwise try to extract from the token or use the token itself as a fallback
                try:
                    # Try to decode the JWT token to extract the user ID
                    # This is a simple implementation - in production you'd verify the token
                    import base64
                    import json
                    
                    # Get the payload part of the JWT (second part)
                    payload = token.split('.')[1]
                    # Add padding if needed
                    payload += '=' * (4 - len(payload) % 4)
                    # Decode the payload
                    decoded = base64.b64decode(payload)
                    payload_data = json.loads(decoded)
                    
                    # Extract the sub claim which contains the user ID
                    if 'sub' in payload_data:
                        user_id = payload_data['sub']
                        logger.info(f"Extracted user_id from JWT: {user_id}")
                    else:
                        # Fallback to using the token itself
                        user_id = token
                        logger.warning(f"Could not extract user_id from JWT, using token as user_id")
                except Exception as e:
                    # If decoding fails, use the token as the user ID
                    logger.error(f"Error decoding JWT: {e}")
                    user_id = token
                    logger.warning(f"Using token as user_id due to decoding error")
            
            event['user_id'] = user_id
            logger.info(f"Added user_id {user_id} to event")
            
            # Add user_email if available in headers
            if user_email:
                event['user_email'] = user_email
                logger.info(f"Added user_email {user_email} to event")
            else:
                # Fallback to a default email if none provided
                event['user_email'] = 'user@example.com'
                logger.warning("No user email in request headers, using default")
    
    logger.debug(f"Received event: {event}")
    
    # Try to save to Supabase first
    try:
        supabase = get_supabase_client()
        if supabase:
            # Validate required fields for Supabase schema
            required_fields = ['id', 'title', 'start', 'end', 'user_id', 'user_email']
            
            # Ensure user_email is present (add default if missing)
            if 'user_email' not in event and 'user_id' in event:
                # Check if user email is in headers before defaulting
                user_email_header = request.headers.get('User-Email')
                if user_email_header:
                    event['user_email'] = user_email_header
                    logger.info(f"Added user_email from header: {user_email_header} to event with ID {event.get('id')}")
                else:
                    event['user_email'] = 'user@example.com'
                    logger.warning(f"No user email found for user_id {event.get('user_id')}, using default")
            
            missing_fields = [field for field in required_fields if field not in event]
            
            if missing_fields:
                error_msg = f"Cannot save to Supabase: Missing required fields: {missing_fields}"
                logger.error(error_msg)
                # Will fall back to local storage below
            else:
                # Prepare clean event for Supabase
                clean_event = {
                    'id': event.get('id'),
                    'title': event.get('title'),
                    'description': event.get('description', ''),
                    'start': event.get('start'),
                    'end': event.get('end'),
                    'all_day': event.get('allDay', False),
                    'user_id': event.get('user_id'),
                    'user_email': event.get('user_email')
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
    
    # Get user email from headers if available
    user_email = request.headers.get('User-Email')
    if user_email and 'user_email' not in updated_event:
        updated_event['user_email'] = user_email
        logger.info(f"Added user_email {user_email} to updated event")
    
    # Extract user_id from JWT token if available
    if 'user_id' not in updated_event:
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            # Extract JWT token
            token = auth_header.split(' ')[1]
            
            try:
                # Try to decode the JWT token to extract the user ID
                import base64
                import json
                
                # Get the payload part of the JWT (second part)
                payload = token.split('.')[1]
                # Add padding if needed
                payload += '=' * (4 - len(payload) % 4)
                # Decode the payload
                decoded = base64.b64decode(payload)
                payload_data = json.loads(decoded)
                
                # Extract the sub claim which contains the user ID
                if 'sub' in payload_data:
                    user_id = payload_data['sub']
                    logger.info(f"Extracted user_id from JWT: {user_id}")
                else:
                    # Fallback to using the token itself
                    user_id = token
                    logger.warning(f"Could not extract user_id from JWT, using token as user_id")
            except Exception as e:
                # If decoding fails, use the token as the user ID
                logger.error(f"Error decoding JWT: {e}")
                user_id = token
                logger.warning(f"Using token as user_id due to decoding error")
            
            updated_event['user_id'] = user_id
            logger.info(f"Added user_id {user_id} to updated event")
    
    updated_in_supabase = False
    
    # Try to update in Supabase first
    try:
        supabase = get_supabase_client()
        if supabase:
            # Validate required fields
            required_fields = ['id', 'title', 'start', 'end', 'user_id', 'user_email']
            
            # Ensure user_email is present (add default if missing)
            if 'user_email' not in updated_event and 'user_id' in updated_event:
                # Check if user email is in headers before defaulting
                user_email_header = request.headers.get('User-Email')
                if user_email_header:
                    updated_event['user_email'] = user_email_header
                    logger.info(f"Added user_email from header: {user_email_header} to updated event with ID {event_id}")
                else:
                    updated_event['user_email'] = 'user@example.com'
                    logger.warning(f"No user email found for user_id {updated_event.get('user_id')}, using default")
            
            missing_fields = [field for field in required_fields if field not in updated_event]
            
            if missing_fields:
                error_msg = f"Cannot update in Supabase: Missing required fields: {missing_fields}"
                logger.error(error_msg)
                # Will still try to update local storage below
            else:
                # Prepare clean event for Supabase
                clean_event = {
                    'id': event_id,
                    'title': updated_event.get('title'),
                    'description': updated_event.get('description', ''),
                    'start': updated_event.get('start'),
                    'end': updated_event.get('end'),
                    'all_day': updated_event.get('allDay', False),
                    'user_id': updated_event.get('user_id'),
                    'user_email': updated_event.get('user_email')
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
    data = request.json
    user_message = data.get('message')
    user_id = data.get('userId')  # Get userId from request
    user_email = data.get('userEmail') # Get userEmail from request

    if not user_message:
        logger.warning("No message provided in chat request")
        return jsonify({'message': 'No message provided'}), 400

    logger.info(f"Received chat message from user {user_id} ({user_email}): {user_message}")
    
    # Process the message using ChatGPT API
    event, response_message = process_event_request(user_message)
    
    action = None
    if event:
        action = event.get('action')
        
        # Ensure user_id and user_email are in the event object if available
        if user_id and 'user_id' not in event:
            event['user_id'] = user_id
        if user_email and 'user_email' not in event:
            event['user_email'] = user_email
            
        logger.info(f"Chat action: {action}, Event details: {event}")

        # --- Handle Supabase Operations ---
        supabase_success = False
        supabase = get_supabase_client()

        if supabase:
            try:
                if action == 'create':
                    logger.info(f"Attempting to create event in Supabase: {event}")
                    # Ensure all required fields are present for Supabase
                    required_fields = ['id', 'title', 'start', 'end', 'user_id', 'user_email']
                    missing_fields = [field for field in required_fields if field not in event or event[field] is None]

                    if missing_fields:
                        logger.error(f"Supabase create error: Missing required fields: {missing_fields} in event {event}")
                        response_message = f"I couldn't create the event due to missing details: {', '.join(missing_fields)}. Please try again."
                    else:
                        # Prepare clean event for Supabase
                        clean_event_create = {
                            'id': event.get('id'),
                            'title': event.get('title'),
                            'description': event.get('description', ''),
                            'start': event.get('start'),
                            'end': event.get('end'),
                            'all_day': event.get('allDay', False),
                            'user_id': event.get('user_id'),
                            'user_email': event.get('user_email')
                        }
                        db_response = supabase.table('events').insert(clean_event_create).execute()
                        if db_response.data:
                            logger.info(f"Successfully created event in Supabase: {db_response.data[0]}")
                            event = db_response.data[0] # Use the event data returned by Supabase
                            supabase_success = True
                        else:
                            logger.error(f"Supabase create error: No data returned. Response: {db_response}")
                            response_message = "I tried to create the event, but something went wrong with the database."
                
                elif action == 'delete':
                    event_title_to_delete = event.get('title')
                    event_start_to_delete = event.get('start') # This might be a date string
                    logger.info(f"Attempting to delete event in Supabase: Title='{event_title_to_delete}', Start='{event_start_to_delete}'")

                    if not event_title_to_delete:
                        logger.warning("Supabase delete error: No title provided for deletion.")
                        response_message = "Please specify the title of the event to delete."
                    else:
                        query = supabase.table('events').delete().eq('user_id', user_id).ilike('title', f"%{event_title_to_delete}%")
                        
                        # If start date is provided, try to match it. This is a bit tricky
                        # as the format from LLM might vary. We'll try a basic date match.
                        if event_start_to_delete:
                            try:
                                # Assuming start is YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS
                                date_str = event_start_to_delete.split('T')[0]
                                query = query.gte('start', f"{date_str}T00:00:00").lte('start', f"{date_str}T23:59:59")
                            except Exception as e:
                                logger.warning(f"Could not parse start date for delete query: {event_start_to_delete} - {e}")

                        db_response = query.execute()
                        
                        if db_response.data:
                            logger.info(f"Successfully deleted event(s) from Supabase: {db_response.data}")
                            # We don't send the full event back, just confirmation
                            event = {'id': 'deleted', 'title': event_title_to_delete} # Placeholder for frontend
                            supabase_success = True
                        else:
                            logger.warning(f"Supabase delete: No matching event found or error. Title='{event_title_to_delete}', Start='{event_start_to_delete}'. Response: {db_response}")
                            response_message = f"I couldn't find an event titled '{event_title_to_delete}' to delete."
                            if event_start_to_delete:
                                response_message += f" for {event_start_to_delete}."

                elif action == 'reschedule':
                    # Get the essential details for identifying the original event and creating the new one
                    original_title = event.get('title')
                    original_start = event.get('originalStart')
                    new_start = event.get('start')
                    new_end = event.get('end')
                    description = event.get('description', '')
                    all_day = event.get('allDay', False)
                    
                    logger.info(f"Attempting to reschedule event: Title='{original_title}', Original Start='{original_start}', New Start='{new_start}', New End='{new_end}'")
                    
                    # Validate we have enough info to proceed
                    if not original_title or not original_start or not new_start or not new_end:
                        missing_fields = []
                        if not original_title: missing_fields.append('title')
                        if not original_start: missing_fields.append('originalStart')
                        if not new_start: missing_fields.append('start')
                        if not new_end: missing_fields.append('end')
                        
                        error_msg = f"Cannot reschedule event: Missing required fields: {', '.join(missing_fields)}"
                        logger.error(error_msg)
                        response_message = f"I couldn't reschedule your event because some details were missing: {', '.join(missing_fields)}."
                    else:
                        try:
                            # Ensure proper date format for original_start
                            original_date_part = None
                            try:
                                # Normalize the original_start date format
                                if 'T' in original_start:
                                    original_date_part = original_start.split('T')[0]
                                else:
                                    # If no time part, assume it's just a date
                                    original_date_part = original_start
                                    # Add time part if missing
                                    if len(original_start) == 10:  # YYYY-MM-DD format
                                        original_start = f"{original_start}T00:00:00"
                                logger.info(f"Normalized original start date: {original_date_part} from {original_start}")
                            except Exception as e:
                                logger.error(f"Error parsing original start date: {original_start} - {e}")
                                original_date_part = original_start  # Fallback to original value
                            
                            # Step 1: Find all events on the specified date
                            logger.info(f"Querying events for user {user_id} on date {original_date_part}")
                            find_date_query = supabase.table('events').select('*')\
                                .eq('user_id', user_id)\
                                .eq('is_deleted', False)  # Only consider non-deleted events
                            
                            # Extract just the date part for comparison
                            if original_date_part:
                                logger.info(f"Looking for events on date: {original_date_part} or spanning this date")
                                
                                # Modified query: Events that either start on the target date OR span the target date
                                try:
                                    # Try to use the date part in a query
                                    find_date_query = find_date_query\
                                        .lte('start', f"{original_date_part}T23:59:59")\
                                        .gte('end', f"{original_date_part}T00:00:00")
                                except Exception as e:
                                    logger.error(f"Error in date query construction: {e}")
                                    # Fallback to simpler query if date format issues
                                    find_date_query = find_date_query.ilike('start', f"%{original_date_part}%")
                            
                            # Get all events on that date
                            try:
                                date_events_response = find_date_query.execute()
                                date_events = date_events_response.data
                                logger.info(f"Query executed successfully, found {len(date_events) if date_events else 0} events")
                            except Exception as e:
                                logger.error(f"Error executing Supabase query: {e}")
                                logger.error(traceback.format_exc())
                                date_events = []
                            
                            # Log all events found on this date
                            logger.info(f"Events found on or spanning date {original_date_part}: {len(date_events) if date_events else 0}")
                            for idx, ev in enumerate(date_events or []):
                                logger.info(f"  Event {idx+1}: Title='{ev.get('title')}', Start='{ev.get('start')}', End='{ev.get('end')}', ID='{ev.get('id')}'")
                            
                            # If we found events on that date, try fuzzy matching on title
                            found_event = None
                            if date_events and len(date_events) > 0:
                                # Extract keywords from the requested title
                                title_keywords = original_title.lower().split()
                                logger.info(f"Searching for title keywords: {title_keywords}")
                                
                                # Find the best matching event
                                best_match = None
                                best_match_score = 0
                                
                                for ev in date_events:
                                    if ev.get('title'):
                                        event_title = ev.get('title').lower()
                                        
                                        # Count matching keywords
                                        match_score = 0
                                        matched_keywords = []
                                        for keyword in title_keywords:
                                            if keyword in event_title:
                                                match_score += 1
                                                matched_keywords.append(keyword)
                                        
                                        logger.info(f"  Event '{ev.get('title')}' match score: {match_score}/{len(title_keywords)}, matched keywords: {matched_keywords}")
                                        
                                        # If we found a better match, save it
                                        if match_score > best_match_score:
                                            best_match_score = match_score
                                            best_match = ev
                                            logger.info(f"  New best match: '{ev.get('title')}' with score {match_score}/{len(title_keywords)}")
                                
                                # If we found a match with at least one keyword, use it
                                if best_match and best_match_score > 0:
                                    found_event = best_match
                                    logger.info(f"Best match found: '{best_match.get('title')}' with score {best_match_score}/{len(title_keywords)}")
                                else:
                                    logger.warning(f"No matching event found for title keywords: {title_keywords}")
                            
                            if found_event:
                                # Use the exact title from the found event
                                original_title = found_event.get('title')
                                logger.info(f"Using original event title: '{original_title}'")
                                
                                # Generate new event ID first
                                new_event_id = str(uuid.uuid4())
                                
                                # Step 2: Mark the original event as rescheduled
                                # Update the original event
                                original_id = found_event.get('id')
                                
                                # Validate original_id exists before trying to update
                                if not original_id:
                                    logger.error("Found event has no ID, cannot mark as rescheduled")
                                    raise ValueError("Found event has no ID")
                                
                                try:
                                    update_query = supabase.table('events').update({
                                        'is_deleted': True,
                                        'is_rescheduled': True
                                    }).eq('id', original_id).execute()
                                    
                                    logger.info(f"Updated original event (ID: {original_id}) as deleted and rescheduled: {update_query.data}")
                                    
                                    # Verify update success
                                    if not update_query.data:
                                        logger.warning(f"No data returned from update query for event ID {original_id}")
                                except Exception as e:
                                    logger.error(f"Error updating original event: {e}")
                                    logger.error(traceback.format_exc())
                                    raise Exception(f"Failed to update original event: {e}")
                                
                                # Step 3: Create the new event with the original event's title
                                if original_title:
                                    # Prepare the new event object
                                    new_event = {
                                        'id': new_event_id,
                                        'title': original_title,
                                        'description': description or found_event.get('description', ''),
                                        'start': new_start,
                                        'end': new_end,
                                        'all_day': all_day,
                                        'user_id': user_id,
                                        'user_email': user_email,
                                        'rescheduled_from': original_id,
                                        'is_deleted': False,
                                        'is_rescheduled': False
                                    }
                                    
                                    logger.info(f"Created new rescheduled event object: {new_event}")
                                    
                                    try:
                                        insert_response = supabase.table('events').insert(new_event).execute()
                                        
                                        # Verify insert success
                                        if insert_response.data and len(insert_response.data) > 0:
                                            logger.info(f"Successfully inserted new event: {insert_response.data[0]}")
                                        else:
                                            logger.warning("No data returned from insert query")
                                            raise Exception("Insert failed - no data returned")
                                    except Exception as e:
                                        logger.error(f"Error inserting new event: {e}")
                                        logger.error(traceback.format_exc())
                                        raise Exception(f"Failed to insert new event: {e}")
                                    
                                    # Format dates for user message
                                    try:
                                        original_date_formatted = original_date_part
                                        new_date_formatted = new_start.split('T')[0] if 'T' in new_start else new_start
                                        
                                        # Add success message
                                        response_message = f"Successfully rescheduled '{original_title}' from {original_date_formatted} to {new_date_formatted}"
                                        supabase_success = True
                                        
                                        # Update the event returned to frontend
                                        event.update({
                                            'id': new_event_id,
                                            'title': original_title,
                                            'start': new_start,
                                            'end': new_end,
                                            'isDeleted': False,
                                            'isRescheduled': False
                                        })
                                        logger.info(f"Updated response event with ID {new_event_id} and title '{original_title}'")
                                    except Exception as e:
                                        logger.error(f"Error formatting success message: {e}")
                                        response_message = "Event was rescheduled successfully."
                                else:
                                    # We shouldn't get here, but just in case
                                    logger.error("Original title is missing after finding event")
                                    response_message = "There was an issue rescheduling the event (missing title)."
                            else:
                                # No matching event found
                                logger.warning(f"No matching event found on date {original_date_part} for title '{original_title}'")
                                response_message = f"I couldn't find any event matching '{original_title}' on {original_date_part}. Please try again with more specific details."
                        except Exception as e:
                            logger.error(f"Error rescheduling event: {e}")
                            logger.error(traceback.format_exc())
                            response_message = f"Sorry, there was an error rescheduling the event: {str(e)}"
            
            except openai.APIError as e: # Catch OpenAI specific API errors
                logger.error(f"OpenAI API error during Supabase operation: {e}")
                response_message = f"There was an issue with the AI service while updating the calendar: {e}"
            except Exception as e:
                logger.error(f"Error during Supabase operation ({action}): {e}")
                logger.error(traceback.format_exc())
                response_message = f"I encountered a database error while trying to {action} the event."
        
        else: # No Supabase client
            logger.warning("Supabase client not available. Chat actions will not persist to database.")
            response_message += " (Note: Database not connected, changes are temporary)"

        # Fallback to local storage if Supabase failed or not configured
        # OR always update local cache for responsiveness?
        # For now, only if Supabase failed for create/update. Delete is tricky locally.
        if not supabase_success and action in ['create', 'reschedule_update_part']: # 'reschedule_update_part' isn't a real action type here
             logger.info(f"Action '{action}' failed in Supabase or Supabase not configured. Updating local 'events' list.")
             if action == 'create' and event not in events: # Basic check
                 events.append(event)
             # How to handle reschedule locally is more complex, depends on how frontend uses the response.
             # The current frontend logic for reschedule *replaces* based on originalId.
             save_events() # Save to local JSON


    # Prepare the final response for the frontend
    final_response = {'message': response_message}
    if event:
        # Ensure the event in the response has the action field for the frontend
        event['action'] = action 
        final_response['event'] = event
        
    logger.info(f"Returning chat response to frontend: {final_response}")
    return jsonify(final_response)

@app.route('/api/test-supabase', methods=['GET'])
def test_supabase():
    logger.info("Testing Supabase connection")
    try:
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({
                'status': 'error',
                'message': 'Supabase client not initialized'
            }), 500
            
        # Test basic query
        response = supabase.table('events').select('id', count='exact').limit(1).execute()
        
        # Return detailed connection info
        return jsonify({
            'status': 'success',
            'message': 'Supabase connection successful',
            'event_count': response.count,
            'sample_data': response.data[:1] if response.data else None,
            'supabase_url': os.environ.get('SUPABASE_URL', 'Not set'),
            'api_key_length': len(os.environ.get('SUPABASE_KEY', '')),
            'rls_active': True  # Supabase has RLS enabled by default
        })
    except Exception as e:
        logger.error(f"Supabase connection test failed: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'Supabase connection failed: {str(e)}',
            'supabase_url': os.environ.get('SUPABASE_URL', 'Not set'),
            'api_key_length': len(os.environ.get('SUPABASE_KEY', ''))
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    logger.info("Health check endpoint called")
    has_api_key = bool(os.getenv('OPENAI_API_KEY'))
    key_length = len(os.getenv('OPENAI_API_KEY') or '')
    
    # Check Supabase connection
    supabase_status = 'unknown'
    try:
        supabase = get_supabase_client()
        if supabase:
            # Simple test query
            supabase.table('events').select('id', count='exact').limit(1).execute()
            supabase_status = 'connected'
    except Exception as e:
        logger.error(f"Supabase health check failed: {str(e)}")
        supabase_status = 'error'
    
    response = jsonify({
        'status': 'ok',
        'api_key_configured': has_api_key,
        'api_key_length': key_length,
        'python_version': os.sys.version,
        'cors': 'enabled',
        'supabase_status': supabase_status,
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
    port = int(os.environ.get("PORT", 12345))
    logger.info(f"Starting Flask server on port {port}")
    try:
        app.run(host='0.0.0.0', debug=False, port=port)
    except Exception as e:
        logger.error(f"Failed to start Flask server: {e}")
        print(f"Error starting server: {e}") 