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
        logger.debug(
            f"Testing with API key prefix: {key_prefix}... (length: {key_length})"
        )

        # Make a simple API call
        logger.debug("Making test call to OpenAI API")
        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {
                        "role": "user",
                        "content": "Say 'API test successful' in JSON format.",
                    },
                ],
                max_tokens=20,
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

        key_prefix = api_key[:4] if len(api_key) > 4 else ""
        key_length = len(api_key)
        logger.debug(
            f"Using API key with prefix: {key_prefix}... (length: {key_length})"
        )

        is_delete_request = any(
            word in user_message.lower() for word in ["delete", "remove", "cancel"]
        )
        if is_delete_request:  # Hint for linters
            pass

        message_lower = user_message.lower()
        is_reschedule_request = "reschedule" in message_lower or any(
            pattern in message_lower
            for pattern in [
                "the meeting",
                "the appointment",
                "the event",
                "the session",
                "this meeting",
                "this appointment",
                "this event",
                "this session",
                "last meeting",
                "last appointment",
                "last event",
                "last session",
                "that meeting",
                "that appointment",
                "that event",
                "that session",
            ]
        )
        if is_reschedule_request:  # Hint for linters
            pass

        if any(
            pattern in message_lower
            for pattern in [
                "a meeting",
                "a new meeting",
                "an appointment",
                "a session",
                "a catch up",
                "a new appointment",
                "an event",
                "a new event",
                "a new session",
            ]
        ):
            is_reschedule_request = False

        current_date_str = datetime.now().strftime("%Y-%m-%d")
        tomorrow_date_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        system_prompt = (
            f"You are a helpful calendar assistant. "
            f"Extract event details from the user's message.\n"
            f'Important: When the user mentions relative dates like "tomorrow", '
            f'"next week", etc.,\n'
            f"calculate the actual date based on the current date which is "
            f'"{current_date_str}".\n'
            f'For example, if today is "{current_date_str}" and the user says '
            f'"tomorrow at 3pm",\n'
            f'use "{tomorrow_date_str}" as the date.\n\n'
            f"IMPORTANT: Always create descriptive and specific event titles.\n"
            f'Never use generic titles like just "meeting" alone.\n'
            f"Instead, include context about the meeting purpose, attendees, or topic. "
            f"For example:\n"
            f'- "Coffee with Mike" instead of "meeting"\n'
            f'- "Team Standup Meeting" instead of "meeting"\n'
            f'- "Doctor\'s Appointment" instead of "appointment"\n'
            f'- "Budget Review with Finance" instead of "review"\n\n'
            f"CRITICAL - Article Usage to Determine Action:\n"
            f'- When the user says phrases with "THE meeting", "THE event", '
            f'"LAST meeting",\n'
            f'  or "THIS event", they are referring to an EXISTING event.\n'
            f"  In these cases, check if they want to reschedule and set action to "
            f'"reschedule".\n'
            f'- When the user says phrases with "A meeting", "A catch up", '
            f'"AN appointment",\n'
            f"  they are creating a NEW event.\n"
            f'  In these cases, always set action to "create".\n\n'
            f'- Example: "schedule the meeting for tomorrow" (reschedule)\n'
            f'           vs "schedule a meeting for tomorrow" (create)\n\n'
            f'If the user refers to "this meeting" or "the event" without '
            f"specifics,\n"
            f"use the most recently discussed event.\n\n"
            f"If the user wants to DELETE an event, extract information about which "
            f"event to delete\n"
            f'and include "action": "delete" in your response. '
            f"For deletion, you only need to provide:\n"
            f'1. The title of the event (be as specific as possible, not just "meeting")\n'  # noqa E501
            f'2. The date of the event if mentioned (e.g., "tomorrow", "Friday", etc.)\n\n'  # noqa E501
            f'Even if the user is vague like "delete the meeting tomorrow", '
            f"still try to extract\n"
            f"what you can and use any context from previous messages to create a "
            f"more specific title.\n\n"
            f"If the user wants to RESCHEDULE an event, extract the original event "
            f"details\n"
            f'along with the new time, and include "action": "reschedule" '
            f"in your response.\n\n"
            f"CRITICAL FOR RESCHEDULING: Provide these details:\n"
            f"1. A specific, descriptive title that matches the original event\n"
            f"   (this will be used for fuzzy matching)\n"
            f"2. The original date of the event (only the date part is crucial)\n"
            f"3. The new date and time for the rescheduled event\n\n"
            f"When the system looks for events to reschedule, it will match based on:\n"
            f"- Events occurring on the same date as originalStart (date part only)\n"
            f"- Events with titles that contain similar keywords as the provided title\n\n"  # noqa E501
            f"The more specific and accurate your title and date information,\n"
            f"the better the system can find the right event to reschedule.\n\n"
            f"IMPORTANT: Return your response in valid JSON format WITHOUT ANY COMMENTS.\n"  # noqa E501
            f"Do not include explanatory comments in the JSON. If you need to explain\n"
            f"assumptions or provide additional context, include that information in the\n"  # noqa E501
            f"description field or in the message field.\n\n"
            f"Return your response in JSON format like this:\n"
            f"For regular event creation:\n"
            f"{{\n"
            f'    "event": {{\n'
            f'        "title": "Event title (be specific and descriptive)",\n'
            f'        "start": "ISO date string",\n'
            f'        "end": "ISO date string",\n'
            f'        "allDay": false,\n'
            f'        "description": "Event description. Include assumptions here."\n'
            f"    }},\n"
            f'    "message": "Your response to the user",\n'
            f'    "action": "create"\n'
            f"}}\n\n"
            f"For event deletion:\n"
            f"{{\n"
            f'    "event": {{\n'
            f'        "title": "Event title to delete (be specific)",\n'
            f'        "start": "ISO date string of original event"\n'
            f"    }},\n"
            f'    "message": "Your response to the user",\n'
            f'    "action": "delete"\n'
            f"}}\n\n"
            f"For event rescheduling:\n"
            f"{{\n"
            f'    "event": {{\n'
            f'        "title": "Event title (specific, for matching original)",\n'
            f'        "originalStart": "ISO date string of original event",\n'
            f'        "originalEnd": "ISO date string of original event",\n'
            f'        "start": "ISO date string of new time",\n'
            f'        "end": "ISO date string of new time",\n'
            f'        "allDay": false,\n'
            f'        "description": "Event description. Include assumptions here."\n'
            f"    }},\n"
            f'    "message": "Your response to the user",\n'
            f'    "action": "reschedule"\n'
            f"}}\n\n"
            f"If you can't extract event details, return:\n"
            f"{{\n"
            f'    "event": null,\n'
            f'    "message": "Your response asking for more information",\n'
            f'    "action": null\n'
            f"}}\n"
        )

        messages = [{"role": "system", "content": system_prompt}]

        if last_mentioned_events:
            context = "Recent events discussed:\n"
            for event_item in last_mentioned_events:
                event_summary = f"- {event_item.get('title', 'Untitled event')}"
                if "start" in event_item:
                    event_summary += f" on {event_item['start']}"
                if "end" in event_item:
                    event_summary += f" to {event_item['end']}"
                context += event_summary + "\n"
            messages.append({"role": "system", "content": context})

        for msg in conversation_history[-10:]:  # Keep history manageable
            messages.append(msg)

        messages.append({"role": "user", "content": user_message})

        logger.debug(f"Messages sent to OpenAI: {json.dumps(messages, indent=2)}")

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        response_content = completion.choices[0].message.content
        logger.debug(f"Raw OpenAI response: {response_content}")

        try:
            response_data = json.loads(response_content)
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to decode JSON from OpenAI: {e}. Response: {response_content}"
            )
            return (
                None,
                "Sorry, I received an invalid response from the AI. Please try again.",
            )

        event = response_data.get("event")
        response_message = response_data.get(
            "message", "Okay, I've processed your request."
        )
        action = response_data.get(
            "action", "create"
        )  # Default to create if not specified

        if event:
            if "id" not in event or not event["id"]:  # Ensure ID if event exists
                event["id"] = str(uuid.uuid4())
            event["action"] = action  # Store action within the event
            logger.info(
                f"Successfully extracted event: {event.get('title')} "
                f"with action {action}"
            )
            last_mentioned_events.append(event)
            if len(last_mentioned_events) > 3:
                last_mentioned_events = last_mentioned_events[-3:]
        else:
            logger.info("No event details could be extracted by OpenAI.")

        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": response_content})
        if len(conversation_history) > 20:  # Limit overall history
            conversation_history = conversation_history[-20:]

        return event, response_message

    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error from OpenAI: {e.response.status_code} - {e.response.text}"
        )
        return None, f"Sorry, there was an HTTP error: {e.response.status_code}"
    except httpx.RequestError as e:
        logger.error(f"Network error connecting to OpenAI: {e}")
        return (
            None,
            "Sorry, I couldn't connect to the AI service. Please check your network.",
        )
    except Exception as e:
        logger.error(f"Error processing event request: {e}", exc_info=True)
        return None, f"Sorry, an unexpected error occurred: {str(e)}"


def create_default_event():
    """Helper to create a default event structure."""
    return {
        "id": str(uuid.uuid4()),
        "title": "Default Event Title (from create_default_event)",
        "start": (datetime.now() + timedelta(days=1)).isoformat(),
        "end": (datetime.now() + timedelta(days=1, hours=1)).isoformat(),
        "allDay": False,
        "description": "This is a default event created by the system.",
        "action": "create",
    }
