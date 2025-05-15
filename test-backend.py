#!/usr/bin/env python3
"""
A simple script to test the backend connectivity.
Run this script to check if the backend is running and responding.
"""

import requests
import sys
import json

BACKEND_URL = "http://127.0.0.1:8000"

def test_health():
    """Test the health endpoint"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend health check successful")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"❌ Backend health check failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - Backend is not running or not accessible")
        return False
    except Exception as e:
        print(f"❌ Error during health check: {e}")
        return False

def test_openai():
    """Test the OpenAI API integration"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/test-openai", timeout=10)
        if response.status_code == 200:
            print("✅ OpenAI API test successful")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"❌ OpenAI API test failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - Backend is not running or not accessible")
        return False
    except Exception as e:
        print(f"❌ Error during OpenAI test: {e}")
        return False

def test_chat():
    """Test the chat endpoint with a simple message"""
    try:
        data = {"message": "Add a test meeting tomorrow at 3pm"}
        response = requests.post(f"{BACKEND_URL}/api/chat", json=data, timeout=10)
        if response.status_code == 200:
            print("✅ Chat endpoint test successful")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return True
        else:
            print(f"❌ Chat endpoint test failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - Backend is not running or not accessible")
        return False
    except Exception as e:
        print(f"❌ Error during chat test: {e}")
        return False

if __name__ == "__main__":
    print("Testing backend connectivity...")
    
    health_success = test_health()
    if not health_success:
        print("\nBackend health check failed. Make sure the backend server is running.")
        print("You can start it with: cd backend && python3 app.py")
        sys.exit(1)
    
    print("\nTesting OpenAI API integration...")
    openai_success = test_openai()
    
    if health_success:
        print("\nTesting chat endpoint...")
        chat_success = test_chat()
    
    if health_success and openai_success and chat_success:
        print("\n✅ All tests passed! The backend is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.") 