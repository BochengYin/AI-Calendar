import os
import json
import logging
from datetime import datetime, timedelta
import httpx
from openai import OpenAI
import uuid

# Configure logging
logger = logging.getLogger(__name__)

# Initialize OpenAI with your API key
api_key = os.getenv("OPENAI_API_KEY")
client = None

# Clear any proxy environment variables that might interfere with OpenAI client
if "HTTP_PROXY" in os.environ:
    logger.info("Clearing HTTP_PROXY environment variable")
    del os.environ["HTTP_PROXY"]
if "HTTPS_PROXY" in os.environ:
    logger.info("Clearing HTTPS_PROXY environment variable")
    del os.environ["HTTPS_PROXY"]
if "http_proxy" in os.environ:
    logger.info("Clearing http_proxy environment variable")
    del os.environ["http_proxy"]
if "https_proxy" in os.environ:
    logger.info("Clearing https_proxy environment variable")
    del os.environ["https_proxy"]

# Initialize the OpenAI client
if api_key:
    try:
        # Create a basic httpx client without proxies
        http_client = httpx.Client(
            timeout=60.0,
            follow_redirects=True,
        )
        
        # Initialize OpenAI client with the custom http client
        client = OpenAI(
            api_key=api_key,
            http_client=http_client,
        )
        logger.info("OpenAI API key configured successfully")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
else:
    logger.error("OpenAI API key is missing or empty")

# Store conversation history for context
conversation_history = []
last_mentioned_events = []

def test_openai_api():
    """
    Test the OpenAI API connection with a simple request.
    Returns a tuple (success, message).
    """
    try:
        logger.info("Testing OpenAI API connection")
        
        if not api_key:
            logger.error("OpenAI API key is not set")
            return False, "OpenAI API key is not configured"
        
        if not client:
            logger.error("OpenAI client not initialized")
            return False, "OpenAI client not initialized"
        
        # Log API key format (safely)
        key_prefix = api_key[:4] if len(api_key) > 4 else ""
        key_length = len(api_key)
        logger.debug(f"Testing with API key prefix: {key_prefix}... (length: {key_length})")
        
        # Make a simple API call
        logger.debug("Making test call to OpenAI API")
        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",  # Changed from gpt-3.5-turbo to gpt-4o-mini
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say 'API test successful' in JSON format."}
                ],
                max_tokens=20
            )
            
            response_text = completion.choices[0].message.content
            logger.debug(f"OpenAI test response: {response_text}")
            
            return True, "API connection successful"
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return False, f"OpenAI API error: {str(e)}"
            
    except Exception as e:
        logger.error(f"Unexpected error testing OpenAI API: {e}", exc_info=True)
        return False, f"Unexpected error: {str(e)}"

def process_event_request(user_message):
    """
    Process the user's message using ChatGPT to extract event details.
    Returns an event object and a response message.
    """
    global conversation_history, last_mentioned_events
    
    try:
        logger.info("Processing event request")
        logger.debug(f"User message: {user_message}")
        
        if not api_key:
            logger.error("OpenAI API key is not set")
            return None, "Sorry, the OpenAI API key is not configured properly."
        
        if not client:
            logger.error("OpenAI client not initialized")
            return None, "Sorry, the OpenAI client could not be initialized."
        
        # Log API key format (safely)
        key_prefix = api_key[:4] if len(api_key) > 4 else ""
        key_length = len(api_key)
        logger.debug(f"Using API key with prefix: {key_prefix}... (length: {key_length})")
        
        # Check if message contains delete/reschedule keywords
        is_delete_request = any(word in user_message.lower() for word in ["delete", "remove", "cancel"])
        is_reschedule_request = "reschedule" in user_message.lower()
        
        # Prepare messages with conversation history
        messages = [
            {"role": "system", "content": """
            You are a helpful calendar assistant. Extract event details from the user's message.
            Important: When the user mentions relative dates like "tomorrow", "next week", etc., 
            calculate the actual date based on the current date which is """ + datetime.now().strftime("%Y-%m-%d") + """.
            For example, if today is """ + datetime.now().strftime("%Y-%m-%d") + """ and the user says "tomorrow at 3pm", 
            use """ + (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d") + """ as the date.
            
            IMPORTANT: Always create descriptive and specific event titles. Never use generic titles like just "meeting" alone.
            Instead, include context about the meeting purpose, attendees, or topic. For example:
            - "Coffee with Mike" instead of "meeting"
            - "Team Standup Meeting" instead of "meeting"
            - "Doctor's Appointment" instead of "appointment"
            - "Budget Review with Finance" instead of "review"
            
            If the user refers to "this meeting" or "the event" without specifics, use the most recently discussed event.
            
            If the user wants to DELETE an event, extract information about which event to delete and include 
            "action": "delete" in your response. For deletion, you only need to provide:
            1. The title of the event (be as specific as possible, not just "meeting")
            2. The date of the event if mentioned (e.g., "tomorrow", "Friday", etc.)
            
            Even if the user is vague like "delete the meeting tomorrow", still try to extract what you can
            and use any context from previous messages to create a more specific title.
            
            If the user wants to RESCHEDULE an event, extract the original event details along with the new time, and include
            "action": "reschedule" in your response.
            
            IMPORTANT: Return your response in valid JSON format WITHOUT ANY COMMENTS. Do not include explanatory comments
            in the JSON. If you need to explain assumptions or provide additional context, include that information in the
            description field or in the message field.
            
            Return your response in JSON format like this:
            For regular event creation:
            {
                "event": {
                    "title": "Event title (be specific and descriptive)",
                    "start": "ISO date string",
                    "end": "ISO date string",
                    "allDay": false,
                    "description": "Event description. Include any assumptions or explanations here."
                },
                "message": "Your response to the user",
                "action": "create"
            }
            
            For event deletion:
            {
                "event": {
                    "title": "Event title to delete (be specific)",
                    "start": "ISO date string of original event" (optional, but include if known)
                },
                "message": "Your response to the user",
                "action": "delete"
            }
            
            For event rescheduling:
            {
                "event": {
                    "title": "Event title (be specific)",
                    "originalStart": "ISO date string of original event",
                    "originalEnd": "ISO date string of original event",
                    "start": "ISO date string of new time",
                    "end": "ISO date string of new time",
                    "allDay": false,
                    "description": "Event description. Include any assumptions about times here."
                },
                "message": "Your response to the user",
                "action": "reschedule"
            }
            
            If you can't extract event details, return:
            {
                "event": null,
                "message": "Your response asking for more information",
                "action": null
            }
            """}
        ]
        
        # Add context about the last mentioned events if available
        if last_mentioned_events:
            context = "Recent events discussed:\n"
            for event in last_mentioned_events:
                # Safely format the event context with error handling for missing fields
                event_summary = f"- {event.get('title', 'Untitled event')}"
                
                if 'start' in event:
                    event_summary += f" on {event['start']}"
                
                if 'end' in event:
                    event_summary += f" to {event['end']}"
                elif 'action' in event and event['action'] == 'delete':
                    # For delete actions, end date isn't necessary
                    pass
                
                context += event_summary + "\n"
            
            messages.append({"role": "system", "content": context})
        
        # Add conversation history (up to 5 previous exchanges)
        for msg in conversation_history[-10:]:
            messages.append(msg)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Call the ChatGPT API to parse the event details
        logger.debug("Calling OpenAI API")
        
        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=messages
            )
            
            # Extract the ChatGPT response
            response_text = completion.choices[0].message.content
            logger.debug(f"OpenAI API response: {response_text}")
            
            # Update conversation history
            conversation_history.append({"role": "user", "content": user_message})
            conversation_history.append({"role": "assistant", "content": response_text})
            
            # Limit conversation history to last 20 messages
            if len(conversation_history) > 20:
                conversation_history = conversation_history[-20:]
            
            # Parse the JSON response
            try:
                response_data = json.loads(response_text)
                event = response_data.get("event")
                message = response_data.get("message", "Event added to calendar!")
                action = response_data.get("action", "create")
                
                if event:
                    # Make sure each event has a unique ID
                    if 'id' not in event:
                        event['id'] = str(uuid.uuid4())
                    
                    # Store the action in the event
                    event['action'] = action
                    
                    logger.info(f"Successfully extracted event: {event.get('title')} with action {action}")
                    
                    # Add to last mentioned events
                    last_mentioned_events.append(event)
                    
                    # Keep only the last 3 events for context
                    if len(last_mentioned_events) > 3:
                        last_mentioned_events = last_mentioned_events[-3:]
                else:
                    logger.info("No event details could be extracted")
                
                return event, message
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.debug(f"Invalid JSON: {response_text}")
                # If we couldn't parse the JSON, generate a response without event
                return None, "I couldn't understand the event details. Could you provide more information?"
                
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None, f"Sorry, there was an error with the OpenAI API: {str(e)}"
            
    except Exception as e:
        logger.error(f"Unexpected error processing event request: {e}", exc_info=True)
        return None, f"Sorry, I encountered an error: {str(e)}"

def create_default_event():
    """Create a default event for testing purposes"""
    logger.info("Creating default test event")
    now = datetime.now()
    start = now + timedelta(hours=1)
    end = start + timedelta(hours=1)
    
    return {
        "title": "Test Calendar Integration",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "allDay": False,
        "description": "This is a test event to verify the calendar integration is working properly"
    } 