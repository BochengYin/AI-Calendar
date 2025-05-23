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
import random  # Added for with_retry
from supabase_client import get_supabase_client

# Load environment variables first, before imports that might use them
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("backend.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Now import modules that might use environment variables
try:
    from api.chatgpt import process_event_request, test_openai_api
except ImportError as e:
    print(f"Error importing modules: {e}")

    # Define fallback functions if import fails
    def process_event_request_fallback(message):
        return None, "API function not available due to import error"

    def test_openai_api_fallback():
        return False, "API test function not available due to import error"

    process_event_request = process_event_request_fallback
    test_openai_api = test_openai_api_fallback


logger.info("Environment variables loaded")
logger.debug(
    f"OPENAI_API_KEY configured: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}"
)
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
            logger.warning(
                f"Operation failed, retrying in {delay:.2f}s... ({retries}/{max_retries})"
            )
            logger.warning(f"Error: {str(e)}")
            time.sleep(delay)

    # If we've exhausted all retries, raise the last exception
    func_name = func.__name__ if hasattr(func, "__name__") else "unknown"
    logger.error(f"All {max_retries} retries failed for function {func_name}")
    raise last_exception


app = Flask(__name__)

# IMPORTANT: Handle CORS properly - this is the critical part!
# First, apply a more permissive CORS policy
# Replace your existing CORS configuration with this
CORS(
    app,
    resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "User-Email"],
        }
    },
)


# Add this after_request handler after the CORS configuration
@app.after_request
def after_request(response):
    # Remove any existing Access-Control-Allow-Origin headers to prevent duplicates
    if response.headers.get("Access-Control-Allow-Origin"):
        del response.headers["Access-Control-Allow-Origin"]

    # Set a single Access-Control-Allow-Origin header
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add(
        "Access-Control-Allow-Headers", "Content-Type, Authorization, User-Email"
    )
    response.headers.add(
        "Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS"
    )
    return response


# In-memory storage for events
events = []


# Functions for local JSON storage (keeping for debugging and fallback)
def load_events():
    try:
        if os.path.exists("events.json"):
            with open("events.json", "r") as f:
                loaded_events = json.load(f)
                # Ensure all events have IDs
                for event_item in loaded_events:
                    if "id" not in event_item:
                        event_item["id"] = str(uuid.uuid4())
                logger.info(f"Loaded {len(loaded_events)} events from events.json")
                return loaded_events
    except Exception as e:
        logger.error(f"Error loading events: {e}")
    logger.info("No events loaded, starting with empty events list")
    return []


# Save events to both JSON file and Supabase (if configured)
def save_events_to_json():
    # Save to JSON file (for debugging and fallback)
    try:
        with open("events.json", "w") as f:
            json.dump(events, f)
            logger.info(f"Saved {len(events)} events to events.json")
    except Exception as e:
        logger.error(f"Error saving events to JSON: {e}")


def sync_events_to_supabase():
    # Save to Supabase if available
    try:
        supabase = get_supabase_client()
        if not supabase:
            logger.warning("Supabase client not available for sync.")
            return

        logger.info(f"Attempting to sync {len(events)} events to Supabase")
        batch_size = 20  # Process in batches to avoid request size limits

        for i in range(0, len(events), batch_size):
            batch = events[i : i + batch_size]

            # Only insert events that have all required fields
            valid_events = []
            for event_item in batch:
                # Make sure event has all required fields for Supabase
                if not all(k in event_item for k in ["title", "start", "end"]):
                    logger.warning(
                        f"Skipping event missing required fields: {event_item}"
                    )
                    continue

                # Prepare a clean version of the event for Supabase
                clean_event = {
                    "id": event_item.get("id"),
                    "title": event_item.get("title"),
                    "description": event_item.get("description", ""),
                    "start": event_item.get("start"),
                    "end": event_item.get("end"),
                    "all_day": event_item.get("allDay", False),
                    "user_id": event_item.get("user_id"),
                    "user_email": event_item.get("user_email"),
                }
                valid_events.append(clean_event)

            if valid_events:
                try:
                    # Using upsert to handle both inserts and updates
                    # supabase_response = (
                    # supabase.table("events").upsert(valid_events).execute()
                    # )
                    # logger.info(
                    # f"Synced batch of {len(valid_events)} events to Supabase"
                    # )
                    pass  # Placeholder, actual upsert logic was commented out
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

        response = supabase.table("events").select("*").execute()
        if response.data:
            logger.info(f"Loaded {len(response.data)} events from Supabase")

            # Convert snake_case fields from Supabase to camelCase for frontend
            converted_events = []
            for event_item in response.data:
                # Create an adapted version of the event with proper field names
                converted_event = {
                    "id": event_item.get("id"),
                    "title": event_item.get("title"),
                    "description": event_item.get("description", ""),
                    "start": event_item.get("start"),
                    "end": event_item.get("end"),
                    "allDay": event_item.get(
                        "all_day", False
                    ),  # Convert from snake_case to camelCase
                    "user_id": event_item.get("user_id"),
                    "user_email": event_item.get("user_email"),
                }

                # Add any additional fields from the database
                if event_item.get("is_deleted"):
                    converted_event["isDeleted"] = event_item.get("is_deleted")
                if event_item.get("is_rescheduled"):
                    converted_event["isRescheduled"] = event_item.get("is_rescheduled")
                if event_item.get("rescheduled_from"):
                    converted_event["rescheduledFrom"] = event_item.get(
                        "rescheduled_from"
                    )

                converted_events.append(converted_event)

            logger.debug(
                f"Successfully converted {len(converted_events)} events "
                f"from Supabase format"
            )
            return converted_events
        else:
            logger.info("No events found in Supabase")
            return []
    except Exception as e:
        logger.error(f"Error loading events from Supabase: {e}")
        logger.error(traceback.format_exc())
        return None


# Try to load events from Supabase first, fall back to JSON if needed
supabase_events_data = load_events_from_supabase()
if supabase_events_data is not None:
    events = supabase_events_data
    # Also save to JSON for debugging
    save_events_to_json()
else:
    # Fall back to JSON file
    events = load_events()

# Initialize OpenAI client
openai_api_key_env = os.getenv("OPENAI_API_KEY")
if openai_api_key_env:
    openai.api_key = openai_api_key_env
    logger.info(f"OpenAI API key loaded (length: {len(openai_api_key_env)})")
else:
    logger.warning("OpenAI API key not found in environment variables.")


@app.route("/api/events", methods=["GET"])
def get_events_route():
    logger.info("GET /api/events endpoint called")
    logger.info(f"Request headers: {dict(request.headers)}")

    # Check for user_id in query parameters
    user_id_param = request.args.get("user_id")

    # Try to get events from Supabase first
    try:
        supabase = get_supabase_client()
        if supabase:
            logger.info(f"Fetching events from Supabase for user: {user_id_param}")

            # Use retry logic for Supabase query
            def fetch_events_from_db():
                query = supabase.table("events").select("*")

                # Apply user filtering if needed (RLS should handle this automatically in Supabase)
                if user_id_param:
                    query = query.eq("user_id", user_id_param)

                return query.execute()

            # Use the retry function to make the query more resilient
            try:
                response = with_retry(fetch_events_from_db)  # Call local with_retry

                if response.data:
                    logger.info(f"Returned {len(response.data)} events from Supabase")

                    # Backup fetched events to local storage to avoid disappearing events
                    global events
                    if len(response.data) > 0:
                        logger.info(
                            f"Updating local events cache with {len(response.data)} "
                            f"events from Supabase"
                        )
                        # Convert from snake_case to camelCase for frontend
                        local_events_cache = []
                        for event_item in response.data:
                            local_event = {
                                "id": event_item.get("id"),
                                "title": event_item.get("title"),
                                "description": event_item.get("description", ""),
                                "start": event_item.get("start"),
                                "end": event_item.get("end"),
                                "allDay": event_item.get("all_day", False),
                                "user_id": event_item.get("user_id"),
                                "user_email": event_item.get("user_email"),
                            }
                            if event_item.get("is_deleted"):
                                local_event["isDeleted"] = event_item.get("is_deleted")
                            if event_item.get("is_rescheduled"):
                                local_event["isRescheduled"] = event_item.get(
                                    "is_rescheduled"
                                )
                            local_events_cache.append(local_event)

                        # Update the global events list but filter for this user if user_id exists
                        if user_id_param:
                            # Keep events that belong to other users
                            other_user_events = [
                                e
                                for e in events
                                if e.get("user_id")
                                and e.get("user_id") != user_id_param
                            ]
                            # Then add the events for this user
                            events = other_user_events + local_events_cache
                        else:
                            events = local_events_cache

                        # Save to JSON file for backup
                        save_events_to_json()

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
    if user_id_param:
        user_email_str = request.headers.get("User-Email", "unknown")
        logger.info(f"Filtering events for user: {user_id_param} ({user_email_str})")
        user_events_local = [
            event_item
            for event_item in events
            if event_item.get("user_id") == user_id_param
        ]
        return jsonify(user_events_local)
    else:
        return jsonify(events)


@app.route("/api/events", methods=["POST"])
def create_event_route():
    logger.info("POST /api/events endpoint called")
    event_data = request.json

    # Generate ID if not provided
    if "id" not in event_data:
        event_data["id"] = str(uuid.uuid4())

    # Add user_id if available in the auth header
    auth_header_val = request.headers.get("Authorization")
    user_email_header_val = request.headers.get("User-Email")

    if (
        "user_id" not in event_data
        and auth_header_val
        and auth_header_val.startswith("Bearer ")
    ):
        # Extract JWT token
        token = auth_header_val.split(" ")[1]
        user_id_from_token = None

        # If user_id is already provided in the request body, use that
        if "user_id" in event_data:
            user_id_from_token = event_data["user_id"]
            logger.info(f"Using provided user_id: {user_id_from_token}")
        else:
            # Otherwise try to extract from the token or use the token itself as a fallback
            try:
                # Try to decode the JWT token to extract the user ID
                # This is a simple implementation - in production you'd verify the token
                import base64

                # Get the payload part of the JWT (second part)
                payload_str = token.split(".")[1]
                # Add padding if needed
                payload_str += "=" * (4 - len(payload_str) % 4)
                # Decode the payload
                decoded_payload = base64.b64decode(payload_str)
                payload_data_json = json.loads(decoded_payload)

                # Extract the sub claim which contains the user ID
                if "sub" in payload_data_json:
                    user_id_from_token = payload_data_json["sub"]
                    logger.info(f"Extracted user_id from JWT: {user_id_from_token}")
                else:
                    # Fallback to using the token itself
                    user_id_from_token = token
                    logger.warning(
                        "Could not extract user_id from JWT, using token as user_id"
                    )
            except Exception as e:
                # If decoding fails, use the token as the user ID
                logger.error(f"Error decoding JWT: {e}")
                user_id_from_token = token
                logger.warning(f"Using token as user_id due to decoding error")

        event_data["user_id"] = user_id_from_token
        logger.info(f"Added user_id {user_id_from_token} to event")

        # Add user_email if available in headers
        if user_email_header_val:
            event_data["user_email"] = user_email_header_val
            logger.info(f"Added user_email {user_email_header_val} to event")
        else:
            # Fallback to a default email if none provided
            event_data["user_email"] = "user@example.com"
            logger.warning("No user email in request headers, using default")

    logger.debug(f"Received event: {event_data}")

    # Try to save to Supabase first
    try:
        supabase = get_supabase_client()
        if supabase:
            # Validate required fields for Supabase schema
            required_fields = ["id", "title", "start", "end", "user_id", "user_email"]

            # Ensure user_email is present (add default if missing)
            if "user_email" not in event_data and "user_id" in event_data:
                # Check if user email is in headers before defaulting
                user_email_hdr = request.headers.get("User-Email")
                if user_email_hdr:
                    event_data["user_email"] = user_email_hdr
                    logger.info(
                        f"Added user_email from header: {user_email_hdr} to event "
                        f"with ID {event_data.get('id')}"
                    )
                else:
                    event_data["user_email"] = "user@example.com"
                    logger.warning(
                        f"No user email found for user_id {event_data.get('user_id')}, "
                        f"using default"
                    )

            missing_fields = [
                field for field in required_fields if field not in event_data
            ]

            if missing_fields:
                error_msg = "Cannot save to Supabase: Missing required fields: " + ", ".join(missing_fields)
                logger.error(error_msg)
                # Will fall back to local storage below
            else:
                # Prepare clean event for Supabase
                clean_event_supabase = {
                    "id": event_data.get("id"),
                    "title": event_data.get("title"),
                    "description": event_data.get("description", ""),
                    "start": event_data.get("start"),
                    "end": event_data.get("end"),
                    "all_day": event_data.get("allDay", False),
                    "user_id": event_data.get("user_id"),
                    "user_email": event_data.get("user_email"),
                }

                logger.info(f"Inserting event into Supabase: {clean_event_supabase}")
                response = (
                    supabase.table("events").insert(clean_event_supabase).execute()
                )
                logger.info(f"Supabase response: {response.data}")

                if response.data:
                    # Also add to local events array for backup
                    events.append(event_data)
                    save_events_to_json()  # This now only updates the JSON file
                    return jsonify(response.data[0]), 201
    except Exception as e:
        logger.error(f"Error saving event to Supabase: {e}")
        logger.error(traceback.format_exc())

    # Fall back to just local JSON if Supabase fails
    logger.info("Falling back to local JSON storage for event")
    events.append(event_data)
    save_events_to_json()
    return jsonify(event_data), 201


@app.route("/api/events/<event_id_url>", methods=["DELETE"])
def delete_event_route(event_id_url):
    logger.info(f"DELETE /api/events/{event_id_url} endpoint called")

    deleted_from_supabase = False

    # Try to delete from Supabase first
    try:
        supabase = get_supabase_client()
        if supabase:
            logger.info(f"Deleting event {event_id_url} from Supabase")
            response = (
                supabase.table("events").delete().eq("id", event_id_url).execute()
            )

            if response.data:
                logger.info(
                    f"Successfully deleted event from Supabase: {response.data}"
                )
                deleted_from_supabase = True
            else:
                logger.warning(f"Event {event_id_url} not found in Supabase")
    except Exception as e:
        logger.error(f"Error deleting event from Supabase: {e}")
        logger.error(traceback.format_exc())

    # Find and delete from local events list
    event_deleted_local = None
    for i, event_item_local in enumerate(events):
        if str(event_item_local.get("id")) == event_id_url:
            event_deleted_local = events.pop(i)
            break

    if event_deleted_local or deleted_from_supabase:
        if event_deleted_local:
            logger.info(f"Event deleted from local storage: {event_deleted_local}")
            save_events_to_json()  # Update JSON file

        return jsonify(
            {
                "status": "success",
                "message": "Event deleted successfully",
                "deleted_event": (
                    event_deleted_local if event_deleted_local else {"id": event_id_url}
                ),
            }
        )
    else:
        logger.error(f"Event with ID {event_id_url} not found in either storage")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"Event with ID {event_id_url} not found",
                }
            ),
            404,
        )


@app.route("/api/events/<event_id_url>", methods=["PUT"])
def update_event_route(event_id_url):
    logger.info(f"PUT /api/events/{event_id_url} endpoint called")
    updated_event_data = request.json
    updated_event_data["id"] = event_id_url

    # Get user email from headers if available
    user_email_hdr_put = request.headers.get("User-Email")
    if user_email_hdr_put and "user_email" not in updated_event_data:
        updated_event_data["user_email"] = user_email_hdr_put
        logger.info(f"Added user_email {user_email_hdr_put} to updated event")

    # Extract user_id from JWT token if available
    if "user_id" not in updated_event_data:
        auth_hdr_put = request.headers.get("Authorization")

        if auth_hdr_put and auth_hdr_put.startswith("Bearer "):
            # Extract JWT token
            token_put = auth_hdr_put.split(" ")[1]
            user_id_put = None

            try:
                # Try to decode the JWT token to extract the user ID
                import base64

                # Get the payload part of the JWT (second part)
                payload_str_put = token_put.split(".")[1]
                # Add padding if needed
                payload_str_put += "=" * (4 - len(payload_str_put) % 4)
                # Decode the payload
                decoded_put = base64.b64decode(payload_str_put)
                payload_data_put = json.loads(decoded_put)

                # Extract the sub claim which contains the user ID
                if "sub" in payload_data_put:
                    user_id_put = payload_data_put["sub"]
                    logger.info(f"Extracted user_id from JWT: {user_id_put}")
                else:
                    # Fallback to using the token itself
                    user_id_put = token_put
                    logger.warning(
                        "Could not extract user_id from JWT, using token as user_id"
                    )
            except Exception as e:
                # If decoding fails, use the token as the user ID
                logger.error(f"Error decoding JWT: {e}")
                user_id_put = token_put
                logger.warning(f"Using token as user_id due to decoding error")

            updated_event_data["user_id"] = user_id_put
            logger.info(f"Added user_id {user_id_put} to updated event")

    updated_in_supabase_flag = False

    # Try to update in Supabase first
    try:
        supabase = get_supabase_client()
        if supabase:
            # Validate required fields
            required_fields_put = [
                "id",
                "title",
                "start",
                "end",
                "user_id",
                "user_email",
            ]

            # Ensure user_email is present (add default if missing)
            if (
                "user_email" not in updated_event_data
                and "user_id" in updated_event_data
            ):
                # Check if user email is in headers before defaulting
                user_email_header_put_inner = request.headers.get("User-Email")
                if user_email_header_put_inner:
                    updated_event_data["user_email"] = user_email_header_put_inner
                    logger.info(
                        f"Added user_email from header: {user_email_header_put_inner} "
                        f"to updated event with ID {event_id_url}"
                    )
                else:
                    updated_event_data["user_email"] = "user@example.com"
                    logger.warning(
                        f"No user email found for user_id "
                        f"{updated_event_data.get('user_id')}, using default"
                    )

            missing_fields_put = [
                field
                for field in required_fields_put
                if field not in updated_event_data
            ]

            if missing_fields_put:
                error_msg_put = "Cannot update in Supabase: Missing required fields: " + ", ".join(missing_fields_put)
                logger.error(error_msg_put)
                # Will still try to update local storage below
            else:
                # Prepare clean event for Supabase
                clean_event_put = {
                    "id": event_id_url,
                    "title": updated_event_data.get("title"),
                    "description": updated_event_data.get("description", ""),
                    "start": updated_event_data.get("start"),
                    "end": updated_event_data.get("end"),
                    "all_day": updated_event_data.get("allDay", False),
                    "user_id": updated_event_data.get("user_id"),
                    "user_email": updated_event_data.get("user_email"),
                }

                logger.info(f"Updating event in Supabase: {clean_event_put}")
                response = (
                    supabase.table("events")
                    .update(clean_event_put)
                    .eq("id", event_id_url)
                    .execute()
                )

                if response.data and len(response.data) > 0:
                    logger.info(
                        f"Successfully updated event in Supabase: {response.data}"
                    )
                    updated_in_supabase_flag = True
                else:
                    logger.warning(
                        f"Event {event_id_url} not found in Supabase or "
                        f"no changes made"
                    )
    except Exception as e:
        logger.error(f"Error updating event in Supabase: {e}")
        logger.error(traceback.format_exc())

    # Update in local events list
    event_updated_locally = False
    for i, event_item_local_put in enumerate(events):
        if str(event_item_local_put.get("id")) == event_id_url:
            events[i] = updated_event_data
            event_updated_locally = True
            break

    if event_updated_locally or updated_in_supabase_flag:
        if event_updated_locally:
            logger.info(f"Event updated in local storage: {updated_event_data}")
            save_events_to_json()  # Update JSON file

        return jsonify(
            {
                "status": "success",
                "message": "Event updated successfully",
                "updated_event": updated_event_data,
            }
        )
    else:
        logger.error(f"Event with ID {event_id_url} not found in either storage")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"Event with ID {event_id_url} not found",
                }
            ),
            404,
        )


@app.route("/api/chat", methods=["POST"])
def chat_route():
    logger.info("POST /api/chat endpoint called")
    data_chat = request.json
    user_message_chat = data_chat.get("message")
    user_id_chat = data_chat.get("userId")  # Get userId from request
    user_email_chat = data_chat.get("userEmail")  # Get userEmail from request

    if not user_message_chat:
        logger.warning("No message provided in chat request")
        return jsonify({"message": "No message provided"}), 400

    logger.info(
        f"Received chat message from user {user_id_chat} ({user_email_chat}): "
        f"{user_message_chat}"
    )

    # Process the message using ChatGPT API
    event_details, response_msg_chat = process_event_request(user_message_chat)

    action_chat = None
    if event_details:
        action_chat = event_details.get("action")

        # Ensure user_id and user_email are in the event object if available
        if user_id_chat and "user_id" not in event_details:
            event_details["user_id"] = user_id_chat
        if user_email_chat and "user_email" not in event_details:
            event_details["user_email"] = user_email_chat

        logger.info(f"Chat action: {action_chat}, Event details: {event_details}")

        # --- Handle Supabase Operations ---
        supabase_success_chat = False
        supabase = get_supabase_client()

        if supabase:
            try:
                if action_chat == "create":
                    logger.info(
                        f"Attempting to create event in Supabase: {event_details}"
                    )
                    # Ensure all required fields are present for Supabase
                    required_fields_chat = [
                        "id",
                        "title",
                        "start",
                        "end",
                        "user_id",
                        "user_email",
                    ]
                    missing_fields_chat = [
                        field
                        for field in required_fields_chat
                        if field not in event_details or event_details[field] is None
                    ]

                    if missing_fields_chat:
                        logger.error(
                            f"Supabase create error: Missing required fields: "
                            f"{missing_fields_chat} in event {event_details}"
                        )
                        response_msg_chat = (
                            f"I couldn't create the event due to missing details: "
                            f"{', '.join(missing_fields_chat)}. Please try again."
                        )
                    else:
                        # Prepare clean event for Supabase
                        clean_event_chat_create = {
                            "id": event_details.get("id"),
                            "title": event_details.get("title"),
                            "description": event_details.get("description", ""),
                            "start": event_details.get("start"),
                            "end": event_details.get("end"),
                            "all_day": event_details.get("allDay", False),
                            "user_id": event_details.get("user_id"),
                            "user_email": event_details.get("user_email"),
                        }
                        db_response_chat = (
                            supabase.table("events")
                            .insert(clean_event_chat_create)
                            .execute()
                        )
                        if db_response_chat.data:
                            logger.info(
                                f"Successfully created event in Supabase: "
                                f"{db_response_chat.data[0]}"
                            )
                            event_details = db_response_chat.data[
                                0
                            ]  # Use the event data returned by Supabase
                            supabase_success_chat = True
                        else:
                            logger.error(
                                f"Supabase create error: No data returned. "
                                f"Response: {db_response_chat}"
                            )
                            response_msg_chat = (
                                "I tried to create the event, but something went wrong "
                                "with the database."
                            )

                elif action_chat == "delete":
                    event_title_to_delete = event_details.get("title")
                    event_start_to_delete = event_details.get(
                        "start"
                    )  # This might be a date string
                    logger.info(
                        f"Attempting to delete event in Supabase: "
                        f"Title='{event_title_to_delete}', Start='{event_start_to_delete}'"
                    )

                    if not event_title_to_delete:
                        logger.warning(
                            "Supabase delete error: No title provided for deletion."
                        )
                        response_msg_chat = (
                            "Please specify the title of the event to delete."
                        )
                    else:
                        query_delete = (
                            supabase.table("events")
                            .delete()
                            .eq("user_id", user_id_chat)
                            .ilike("title", f"%{event_title_to_delete}%")
                        )

                        if event_start_to_delete:
                            try:
                                date_str_delete = event_start_to_delete.split("T")[0]
                                query_delete = query_delete.gte(
                                    "start", f"{date_str_delete}T00:00:00"
                                ).lte("start", f"{date_str_delete}T23:59:59")
                            except Exception as e_delete_date:
                                logger.warning(
                                    f"Could not parse start date for delete query: "
                                    f"{event_start_to_delete} - {e_delete_date}"
                                )

                        db_response_delete = query_delete.execute()

                        if db_response_delete.data:
                            logger.info(
                                f"Successfully deleted event(s) from Supabase: "
                                f"{db_response_delete.data}"
                            )
                            event_details = {
                                "id": "deleted",
                                "title": event_title_to_delete,
                            }
                            supabase_success_chat = True
                        else:
                            logger.warning(
                                f"Supabase delete: No matching event found or error. "
                                f"Title='{event_title_to_delete}', "
                                f"Start='{event_start_to_delete}'. Response: {db_response_delete}"
                            )
                            response_msg_chat = (
                                f"I couldn't find an event titled "
                                f"'{event_title_to_delete}' to delete."
                            )
                            if event_start_to_delete:
                                response_msg_chat += f" for {event_start_to_delete}."

                elif action_chat == "reschedule":
                    original_title = event_details.get("title")
                    original_start = event_details.get("originalStart")
                    new_start_reschedule = event_details.get("start")
                    new_end_reschedule = event_details.get("end")
                    description_reschedule = event_details.get("description", "")
                    all_day_reschedule = event_details.get("allDay", False)

                    logger.info(
                        f"Attempting to reschedule event: Title='{original_title}', "
                        f"Original Start='{original_start}', "
                        f"New Start='{new_start_reschedule}', New End='{new_end_reschedule}'"
                    )

                    if not all(
                        [
                            original_title,
                            original_start,
                            new_start_reschedule,
                            new_end_reschedule,
                        ]
                    ):
                        missing_fields_rs = [
                            field
                            for field, value in {
                                "title": original_title,
                                "originalStart": original_start,
                                "start": new_start_reschedule,
                                "end": new_end_reschedule,
                            }.items()
                            if not value
                        ]
                        logger.error(
                            f"Reschedule error: Missing required fields: {missing_fields_rs}"
                        )
                        response_msg_chat = (
                            f"Cannot reschedule event: Missing required fields: "
                            f"{', '.join(missing_fields_rs)}."
                        )
                    else:
                        try:
                            original_date_part_rs = None
                            try:
                                if "T" in original_start:
                                    original_date_part_rs = original_start.split("T")[0]
                                else:
                                    original_date_part_rs = original_start
                                    if len(original_start) == 10:  # YYYY-MM-DD format
                                        original_start = f"{original_start}T00:00:00"
                                logger.info(
                                    f"Normalized original start date: {original_date_part_rs} "
                                    f"from {original_start}"
                                )
                            except Exception as e_parse_rs_date:
                                logger.error(
                                    f"Error parsing original start date: {original_start} - "
                                    f"{e_parse_rs_date}"
                                )
                                original_date_part_rs = original_start

                            logger.info(
                                f"Querying events for user {user_id_chat} on date "
                                f"{original_date_part_rs}"
                            )
                            find_date_query_rs = (
                                supabase.table("events")
                                .select("*")
                                .eq("user_id", user_id_chat)
                                .eq("is_deleted", False)
                            )

                            if original_date_part_rs:
                                logger.info(
                                    f"Looking for events on date: {original_date_part_rs} or "
                                    f"spanning this date"
                                )
                                try:
                                    find_date_query_rs = find_date_query_rs.lte(
                                        "start", f"{original_date_part_rs}T23:59:59"
                                    ).gte("end", f"{original_date_part_rs}T00:00:00")
                                except Exception as e_date_query_rs:
                                    logger.error(
                                        f"Error in date query construction: {e_date_query_rs}"
                                    )
                                    find_date_query_rs = find_date_query_rs.ilike(
                                        "start", f"%{original_date_part_rs}%"
                                    )

                            date_events_rs_data = []
                            try:
                                date_events_response_rs = find_date_query_rs.execute()
                                date_events_rs_data = date_events_response_rs.data
                                logger.info(
                                    f"Query executed successfully, found "
                                    f"{len(date_events_rs_data) if date_events_rs_data else 0} events"
                                )
                            except Exception as e_exec_rs_query:
                                logger.error(
                                    f"Error executing Supabase query: {e_exec_rs_query}"
                                )
                                logger.error(traceback.format_exc())

                            logger.info(
                                f"Events found on or spanning date {original_date_part_rs}: "
                                f"{len(date_events_rs_data) if date_events_rs_data else 0}"
                            )
                            for idx, ev_rs_item in enumerate(date_events_rs_data or []):
                                logger.info(
                                    f"  Event {idx+1}: Title='{ev_rs_item.get('title')}', "
                                    f"Start='{ev_rs_item.get('start')}', "
                                    f"End='{ev_rs_item.get('end')}', ID='{ev_rs_item.get('id')}'"
                                )

                            found_event_rs_match = None
                            if date_events_rs_data and len(date_events_rs_data) > 0:
                                title_keywords_rs = original_title.lower().split()
                                logger.info(
                                    f"Searching for title keywords: {title_keywords_rs}"
                                )
                                best_match_rs_event, best_match_score_rs = None, 0

                                for ev_match_rs_item in date_events_rs_data:
                                    if ev_match_rs_item.get("title"):
                                        event_title_rs_item = ev_match_rs_item.get(
                                            "title"
                                        ).lower()
                                        (
                                            match_score_rs_item,
                                            matched_keywords_rs_item,
                                        ) = (0, [])
                                        for keyword_rs_item in title_keywords_rs:
                                            if keyword_rs_item in event_title_rs_item:
                                                match_score_rs_item += 1
                                                matched_keywords_rs_item.append(
                                                    keyword_rs_item
                                                )
                                        logger.info(
                                            f"  Event '{ev_match_rs_item.get('title')}' "
                                            f"match score: {match_score_rs_item}/"
                                            f"{len(title_keywords_rs)}, matched keywords: "
                                            f"{matched_keywords_rs_item}"
                                        )
                                        if match_score_rs_item > best_match_score_rs:
                                            best_match_score_rs, best_match_rs_event = (
                                                match_score_rs_item,
                                                ev_match_rs_item,
                                            )
                                            logger.info(
                                                f"  New best match: "
                                                f"'{ev_match_rs_item.get('title')}' "
                                                f"with score {match_score_rs_item}"
                                            )
                                if best_match_rs_event and best_match_score_rs > 0:
                                    found_event_rs_match = best_match_rs_event
                                    logger.info(
                                        f"Best match found: "
                                        f"'{best_match_rs_event.get('title')}' "
                                        f"with score {best_match_score_rs}"
                                    )
                                else:
                                    logger.warning(
                                        f"No matching event found for title keywords: "
                                        f"{title_keywords_rs}"
                                    )

                            if found_event_rs_match:
                                original_title = found_event_rs_match.get("title")
                                logger.info(
                                    f"Using original event title: '{original_title}'"
                                )
                                new_event_id_rs_val = str(uuid.uuid4())
                                original_id_rs_val = found_event_rs_match.get("id")
                                if not original_id_rs_val:
                                    logger.error(
                                        "Found event has no ID, cannot mark as rescheduled"
                                    )
                                    raise ValueError("Found event has no ID")
                                try:
                                    update_query_rs_val = (
                                        supabase.table("events")
                                        .update(
                                            {"is_deleted": True, "is_rescheduled": True}
                                        )
                                        .eq("id", original_id_rs_val)
                                        .execute()
                                    )
                                    logger.info(
                                        f"Updated original event (ID: {original_id_rs_val}) "
                                        f"as deleted and rescheduled: {update_query_rs_val.data}"
                                    )
                                    if not update_query_rs_val.data:
                                        logger.warning(
                                            f"No data returned from update query for event ID "
                                            f"{original_id_rs_val}"
                                        )
                                except Exception as e_update_rs_orig:
                                    logger.error(
                                        f"Error updating original event: {e_update_rs_orig}"
                                    )
                                    logger.error(traceback.format_exc())
                                    raise Exception(
                                        f"Failed to update original event: {e_update_rs_orig}"
                                    )

                                if original_title:
                                    new_event_object_rs = {
                                        "id": new_event_id_rs_val,
                                        "title": original_title,
                                        "description": description_reschedule
                                        or found_event_rs_match.get("description", ""),
                                        "start": new_start_reschedule,
                                        "end": new_end_reschedule,
                                        "all_day": all_day_reschedule,
                                        "user_id": user_id_chat,
                                        "user_email": user_email_chat,
                                        "rescheduled_from": original_id_rs_val,
                                        "is_deleted": False,
                                        "is_rescheduled": False,
                                    }
                                    logger.info(
                                        f"Created new rescheduled event object: "
                                        f"{new_event_object_rs}"
                                    )
                                    try:
                                        insert_response_rs_val = (
                                            supabase.table("events")
                                            .insert(new_event_object_rs)
                                            .execute()
                                        )
                                        if (
                                            insert_response_rs_val.data
                                            and len(insert_response_rs_val.data) > 0
                                        ):
                                            logger.info(
                                                f"Successfully inserted new event: "
                                                f"{insert_response_rs_val.data[0]}"
                                            )
                                        else:
                                            logger.warning(
                                                "No data returned from insert query"
                                            )
                                            raise Exception(
                                                "Insert failed - no data returned"
                                            )
                                    except Exception as e_insert_rs_new:
                                        logger.error(
                                            f"Error inserting new event: {e_insert_rs_new}"
                                        )
                                        logger.error(traceback.format_exc())
                                        raise Exception(
                                            f"Failed to insert new event: {e_insert_rs_new}"
                                        )
                                    try:
                                        original_date_formatted_rs = (
                                            original_date_part_rs
                                        )
                                        new_date_formatted_rs = (
                                            new_start_reschedule.split("T")[0]
                                            if "T" in new_start_reschedule
                                            else new_start_reschedule
                                        )
                                        response_msg_chat = (
                                            f"Successfully rescheduled '{original_title}' "
                                            f"from {original_date_formatted_rs} to "
                                            f"{new_date_formatted_rs}"
                                        )
                                        supabase_success_chat = True
                                        event_details.update(
                                            {
                                                "id": new_event_id_rs_val,
                                                "title": original_title,
                                                "start": new_start_reschedule,
                                                "end": new_end_reschedule,
                                                "isDeleted": False,
                                                "isRescheduled": False,
                                            }
                                        )
                                        logger.info(
                                            f"Updated response event with ID {new_event_id_rs_val} "
                                            f"and title '{original_title}'"
                                        )
                                    except Exception as e_format_rs_msg:
                                        logger.error(
                                            f"Error formatting success message: {e_format_rs_msg}"
                                        )
                                        response_msg_chat = (
                                            "Event was rescheduled successfully."
                                        )
                                else:
                                    logger.error(
                                        "Original title is missing after finding event"
                                    )
                                    response_msg_chat = "There was an issue rescheduling the event (missing title)."
                            else:
                                logger.warning(
                                    f"No matching event found on date {original_date_part_rs} for title '{original_title}'"
                                )
                                response_msg_chat = f"I couldn't find any event matching '{original_title}' on {original_date_part_rs}. Please try again with more specific details."
                        except Exception as e_outer_rs_handler:
                            logger.error(
                                f"Error rescheduling event: {e_outer_rs_handler}"
                            )
                            logger.error(traceback.format_exc())
                            response_msg_chat = f"Sorry, there was an error rescheduling the event: {str(e_outer_rs_handler)}"

            except (
                openai.APIError
            ) as e_openai_chat_op:  # Catch OpenAI specific API errors
                logger.error(
                    f"OpenAI API error during Supabase operation: {e_openai_chat_op}"
                )
                response_msg_chat = f"There was an issue with the AI service while updating the calendar: {e_openai_chat_op}"
            except Exception as e_db_op_chat_generic:
                logger.error(
                    f"Error during Supabase operation ({action_chat}): {e_db_op_chat_generic}"
                )
                logger.error(traceback.format_exc())
                raise

        else:  # No Supabase client
            logger.warning(
                "Supabase client not available. Chat actions will not persist to database."
            )
            response_msg_chat += (
                " (Note: Database not connected, changes are temporary)"
            )

        if not supabase_success_chat and action_chat in ["create"]:
            logger.info(
                f"Action '{action_chat}' failed in Supabase or Supabase not configured. "
                "Updating local 'events' list."
            )
            if action_chat == "create" and event_details not in events:
                events.append(event_details)
            save_events_to_json()

    final_response_chat = {"message": response_msg_chat}
    if event_details:
        event_details["action"] = action_chat
        final_response_chat["event"] = event_details

    logger.info(f"Returning chat response to frontend: {final_response_chat}")
    return jsonify(final_response_chat)


@app.route("/api/test-supabase", methods=["GET"])
def test_supabase_route():
    logger.info("Testing Supabase connection")
    try:
        supabase = get_supabase_client()
        if not supabase:
            return (
                jsonify(
                    {"status": "error", "message": "Supabase client not initialized"}
                ),
                500,
            )
        response = (
            supabase.table("events").select("id", count="exact").limit(1).execute()
        )
        return jsonify(
            {
                "status": "success",
                "message": "Supabase connection successful",
                "event_count": response.count,
                "sample_data": response.data[:1] if response.data else None,
                "supabase_url": os.environ.get("SUPABASE_URL", "Not set"),
                "api_key_length": len(os.environ.get("SUPABASE_KEY", "")),
                "rls_active": True,  # Supabase has RLS enabled by default
            }
        )
    except Exception as e_test_sb_conn:
        logger.error(f"Supabase connection test failed: {str(e_test_sb_conn)}")
        logger.error(traceback.format_exc())
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"Supabase connection failed: {str(e_test_sb_conn)}",
                    "supabase_url": os.environ.get("SUPABASE_URL", "Not set"),
                    "api_key_length": len(os.environ.get("SUPABASE_KEY", "")),
                }
            ),
            500,
        )


@app.route("/api/health", methods=["GET"])
def health_check_route():
    logger.info(f"Health check endpoint called for path: {request.path}")
    has_api_key_health = bool(os.getenv("OPENAI_API_KEY"))
    key_length_health = len(os.getenv("OPENAI_API_KEY") or "")
    supabase_status_health = "unknown"
    try:
        supabase = get_supabase_client()
        if supabase:
            supabase.table("events").select("id", count="exact").limit(1).execute()
            supabase_status_health = "connected"
    except Exception as e_health_sb_check:
        logger.error(f"Supabase health check failed: {str(e_health_sb_check)}")
        supabase_status_health = "error"

    response_data_health = {
        "status": "ok",
        "api_key_configured": has_api_key_health,
        "api_key_length": key_length_health,
        "python_version": os.sys.version,
        "cors": "enabled",
        "supabase_status": supabase_status_health,
        "timestamp": datetime.now().isoformat(),
    }
    return jsonify(response_data_health)


@app.route("/", methods=["GET"])
def root_route():
    logger.info("Root endpoint called")
    return jsonify(
        {
            "status": "ok",
            "message": "AI Calendar Backend API is running",
            "version": "1.0.0",
            "cors": "Enabled for Vercel deployment",
            "endpoints": {
                "health": "/api/health",
                "events": "/api/events",
                "chat": "/api/chat",
            },
        }
    )


if __name__ == "__main__":
    port_env = int(os.environ.get("PORT", 12345))
    logger.info(f"Starting Flask server on port {port_env}")
    try:
        app.run(host="0.0.0.0", debug=False, port=port_env)
    except Exception as e_main_start:
        logger.error(
            f"Failed to start Flask server: {type(e_main_start).__name__} - {e_main_start}"
        )
        print(f"Error starting server: {type(e_main_start).__name__} - {e_main_start}")
