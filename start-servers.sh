#!/bin/bash
# Script to start both backend and frontend servers

# Exit on error
set -e

echo "🚀 Starting AI Calendar servers..."

# Check if ports are already in use
if lsof -Pi :12345 -sTCP:LISTEN -t >/dev/null ; then
    echo "Port 12345 is already in use. Stopping the process..."
    pkill -f "python3 app.py" || true
fi

if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
    echo "Port 3000 is already in use. Stopping the process..."
    # Attempt to kill the process using port 3000
    # This is a common way to find and kill the process on macOS/Linux
    lsof -t -i:3000 | xargs kill -9 || true
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

# Run backend server in background with port 12345
PORT=12345 python3 app.py &
BACKEND_PID=$!
echo "✅ Backend server started on port 12345 (PID: $BACKEND_PID)"

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
echo "📊 Backend server: http://localhost:12345"
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