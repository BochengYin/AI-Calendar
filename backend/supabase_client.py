import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    print("Warning: Supabase credentials not found in environment variables.")
    supabase = None
else:
    supabase: Client = create_client(supabase_url, supabase_key)

def get_supabase_client() -> Client:
    """
    Get the Supabase client instance.
    
    Returns:
        Client: The Supabase client instance.
    """
    if not supabase:
        raise Exception("Supabase client not initialized. Check environment variables.")
    return supabase 