#!/usr/bin/env python3
"""
A script to verify the environment setup before starting the application.
"""

import os
import sys
import subprocess
import re

def check_python_version():
    """Check if Python version is compatible"""
    print(f"Python version: {sys.version}")
    if sys.version_info < (3, 8):
        print("❌ Python version 3.8 or higher is required")
        return False
    else:
        print("✅ Python version is compatible")
        return True

def check_node_version():
    """Check if Node.js is installed and version is compatible"""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"Node.js version: {version}")
            match = re.search(r'v(\d+)\.', version)
            if match and int(match.group(1)) >= 14:
                print("✅ Node.js version is compatible")
                return True
            else:
                print("❌ Node.js version 14 or higher is required")
                return False
        else:
            print("❌ Node.js not found")
            return False
    except FileNotFoundError:
        print("❌ Node.js not found")
        return False

def check_backend_directory():
    """Check if backend directory exists and has necessary files"""
    if os.path.isdir('backend'):
        print("✅ Backend directory exists")
        app_py = os.path.isfile('backend/app.py')
        chatgpt_py = os.path.isfile('backend/api/chatgpt.py')
        requirements = os.path.isfile('backend/requirements.txt')
        env_file = os.path.isfile('backend/.env')
        
        if app_py and chatgpt_py and requirements:
            print("✅ Backend core files exist")
            if not env_file:
                print("⚠️ Backend .env file not found - API key may not be configured")
            return True
        else:
            missing = []
            if not app_py: missing.append("app.py")
            if not chatgpt_py: missing.append("api/chatgpt.py")
            if not requirements: missing.append("requirements.txt")
            print(f"❌ Missing backend files: {', '.join(missing)}")
            return False
    else:
        print("❌ Backend directory not found")
        return False

def check_frontend_directory():
    """Check if frontend directory exists and has necessary files"""
    if os.path.isdir('frontend'):
        print("✅ Frontend directory exists")
        package_json = os.path.isfile('frontend/package.json')
        app_js = os.path.isfile('frontend/src/App.js')
        
        if package_json and app_js:
            print("✅ Frontend core files exist")
            return True
        else:
            missing = []
            if not package_json: missing.append("package.json")
            if not app_js: missing.append("src/App.js")
            print(f"❌ Missing frontend files: {', '.join(missing)}")
            return False
    else:
        print("❌ Frontend directory not found")
        return False

def check_openai_api_key():
    """Check if OpenAI API key is configured"""
    # Check in environment variables first
    api_key = os.environ.get('OPENAI_API_KEY')
    
    if not api_key:
        # Check in .env file
        if os.path.isfile('backend/.env'):
            with open('backend/.env', 'r') as f:
                for line in f:
                    if line.startswith('OPENAI_API_KEY='):
                        key = line.split('=', 1)[1].strip()
                        if key and not key.startswith('your_'):
                            print("✅ OpenAI API key is configured in .env file")
                            return True
        
        print("❌ OpenAI API key is not configured")
        print("  - Add your API key to backend/.env file")
        print("  - Format: OPENAI_API_KEY=sk-your-key-here")
        return False
    else:
        print("✅ OpenAI API key is configured in environment variables")
        return True

def check_port_availability():
    """Check if ports 8000 and 3001 are available"""
    import socket
    
    ports_to_check = [8000, 3001]
    all_available = True
    
    for port in ports_to_check:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('127.0.0.1', port))
            print(f"✅ Port {port} is available")
        except socket.error:
            print(f"❌ Port {port} is in use")
            if port == 8000:
                print("  - This port is needed for the backend server")
                print("  - Try stopping other services or changing the port in backend/app.py")
            elif port == 3001:
                print("  - This port is typically used for the React development server")
                print("  - React will try to use another port if this one is busy")
            all_available = False
        finally:
            sock.close()
    
    return all_available

def main():
    """Run all checks and report status"""
    print("Verifying AI Calendar environment setup...\n")
    
    # Run all checks
    python_ok = check_python_version()
    node_ok = check_node_version()
    backend_ok = check_backend_directory()
    frontend_ok = check_frontend_directory()
    api_key_ok = check_openai_api_key()
    ports_ok = check_port_availability()
    
    print("\nSummary:")
    print(f"Python: {'✅' if python_ok else '❌'}")
    print(f"Node.js: {'✅' if node_ok else '❌'}")
    print(f"Backend files: {'✅' if backend_ok else '❌'}")
    print(f"Frontend files: {'✅' if frontend_ok else '❌'}")
    print(f"OpenAI API key: {'✅' if api_key_ok else '❌'}")
    print(f"Ports available: {'✅' if ports_ok else '⚠️'}")
    
    if all([python_ok, node_ok, backend_ok, frontend_ok, api_key_ok, ports_ok]):
        print("\n✅ All checks passed! You can start the application with:")
        print("  ./start-servers.sh")
        return 0
    else:
        print("\n⚠️ Some checks failed. Please fix the issues above before starting the application.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 