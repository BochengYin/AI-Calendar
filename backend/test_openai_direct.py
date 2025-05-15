#!/usr/bin/env python3
"""
Direct OpenAI API test script.
This bypasses Flask and tests OpenAI directly.
"""
import os
import sys
import json
from dotenv import load_dotenv
import httpx
from openai import OpenAI

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

print(f"API key found: {'Yes' if api_key else 'No'}")
if api_key:
    print(f"API key length: {len(api_key)}")
    print(f"API key format: {api_key[:4]}...{api_key[-4:]}")

# Clear any proxy settings
for env_var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
    if env_var in os.environ:
        print(f"Removing {env_var} from environment")
        del os.environ[env_var]

def test_openai():
    if not api_key:
        print("No API key found. Please set OPENAI_API_KEY in your .env file.")
        return False
    
    try:
        print("Creating custom HTTP client...")
        http_client = httpx.Client(
            timeout=60.0,
            follow_redirects=True,
        )
        
        print("Initializing OpenAI client...")
        client = OpenAI(
            api_key=api_key,
            http_client=http_client,
        )
        
        print("Making API request to OpenAI...")
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello in one word."}
            ],
            max_tokens=10
        )
        
        result = completion.choices[0].message.content
        print(f"API call successful. Response: {result}")
        return True
    except Exception as e:
        print(f"Error testing OpenAI API: {e}")
        return False

if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    success = test_openai()
    sys.exit(0 if success else 1) 