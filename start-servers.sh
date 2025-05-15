#!/bin/bash
# Script to start both backend and frontend servers

# Exit on error
set -e

echo "🚀 Starting AI Calendar servers..."

# Check if ports are already in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "Port 8000 is already in use. Stopping the process..."
    pkill -f "python3 app.py" || true
fi

if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
    echo "Port 3000 is already in use. Please close the application using this port."
    exit 1
fi

# Start backend server
echo "🔧 Starting the backend server..."
cd backend
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "⚠️ Python virtual environment not found. Please run setup first."
    exit 1
fi

# Check if requirements are installed
if [ ! -f "requirements.txt" ]; then
    echo "⚠️ requirements.txt not found. Please make sure the backend is set up correctly."
    exit 1
fi

# Run backend server in background
python3 app.py &
BACKEND_PID=$!
echo "✅ Backend server started (PID: $BACKEND_PID)"

# Start frontend server
echo "🔧 Starting the frontend server..."
cd ../frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "⚠️ node_modules not found. Please run npm install in the frontend directory."
    exit 1
fi

# Run frontend server in background
npm start &
FRONTEND_PID=$!
echo "✅ Frontend server started (PID: $FRONTEND_PID)"

echo "🎉 Both servers are now running!"
echo "📊 Backend server: http://localhost:8000"
echo "🖥️ Frontend server: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers"

# Function to handle exit
function cleanup {
    echo "Stopping servers..."
    kill $BACKEND_PID $FRONTEND_PID
    echo "Servers stopped"
    exit 0
}

# Register cleanup function to run on exit
trap cleanup SIGINT SIGTERM

# Wait for both processes to finish
wait 