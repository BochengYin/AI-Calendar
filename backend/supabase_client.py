import os
import logging
import traceback
import time
import random
from supabase import create_client, Client
from dotenv import load_dotenv

# Initialize logger
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

# Global client variable
supabase = None

# Try to initialize the client
try:
    if not supabase_url or not supabase_key:
        logger.warning("Supabase credentials not found in environment variables.")
        print("Warning: Supabase credentials not found in environment variables.")
    else:
        logger.info(f"Initializing Supabase client with URL: {supabase_url[:20]}...")
        logger.info(f"API key length: {len(supabase_key)}")
        supabase: Client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Supabase client: {str(e)}")
    logger.error(traceback.format_exc())
    print(f"Error initializing Supabase client: {str(e)}")

def get_supabase_client() -> Client:
    """
    Get the Supabase client instance.
    
    Returns:
        Client: The Supabase client instance.
    """
    if not supabase:
        error_msg = "Supabase client not initialized. Check environment variables."
        logger.error(error_msg)
        raise Exception(error_msg)
        
    # Test connection - no longer using with_retry here
    try:
        # Attempt a simple query to verify connection
        logger.debug("Testing Supabase connection within get_supabase_client...")
        # Just fetch the count of events as a simple test
        def test_connection_direct(): # Renamed to avoid conflict if with_retry was imported
            return supabase.table('events').select('id', count='exact').limit(1).execute()
            
        response = test_connection_direct() # Direct call
        logger.info(f"Supabase connection test (within get_supabase_client) succeeded: {response.count} events found")
    except Exception as e:
        logger.error(f"Supabase connection test (within get_supabase_client) failed: {str(e)}")
        logger.error(traceback.format_exc())
        # Still return the client so calling code can handle specific errors
    
    return supabase 