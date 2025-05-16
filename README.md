# AI Calendar

An intelligent calendar application that uses AI to manage your events through natural conversation. Create, delete, and reschedule events using simple chat interactions.

## Features

- 🗣️ Natural language event creation
- 📅 Interactive calendar view
- 🔄 Event rescheduling
- 🗑️ Event deletion
- 🐱 Clean, minimal UI with Apple-inspired design

## Tech Stack

### Frontend
- React
- React Big Calendar
- CSS3 with modern styling

### Backend
- Flask (Python)
- OpenAI API (GPT-4o-mini)
- RESTful API design

## Setup and Installation

### Prerequisites
- Node.js (v14+)
- Python 3.9+
- OpenAI API key

### Backend Setup
1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Create a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

5. Start the backend server:
   ```
   python app.py
   ```
   The server will run on http://localhost:8000

### Frontend Setup
1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the development server:
   ```
   npm start
   ```
   The app will open in your browser at http://localhost:3000

## Usage

1. **Create an event**: Type a message like "Schedule a meeting with Alex tomorrow at 2pm"
2. **Reschedule an event**: Type "Reschedule my meeting with Alex to Friday at 3pm"
3. **Delete an event**: Use one of these phrases:
   - "Delete my meeting with Alex"
   - "Delete the meeting on Friday morning"
   - "Cancel my 2pm meeting tomorrow"
   - "Remove the coffee meeting with Bocheng"

For deletion to work properly, include specific details about the event such as:
- The event title
- The person involved
- The date/time of the meeting
- Any other unique identifiers

4. **View event details**: Click on any event in the calendar

### Example Interactions

```
User: "Schedule a meeting with Bocheng tomorrow at 8am"
AI: "I've scheduled your meeting with Bocheng for tomorrow at 8 AM."

User: "Reschedule this meeting to Sunday at 10 o'clock and only have 30 mins"
AI: "The meeting has been rescheduled to Sunday at 10:00 AM for 30 minutes."

User: "Delete the meeting with Bocheng on Sunday"
AI: "The meeting with Bocheng on Sunday has been deleted."
```

## Project Structure

```
AI-Calendar/
├── backend/             # Flask backend
│   ├── api/             # API modules
│   │   └── chatgpt.py   # OpenAI integration
│   └── app.py           # Main Flask application
├── frontend/            # React frontend
│   ├── public/          # Static files
│   └── src/             # Source code
│       ├── components/  # React components
│       └── index.js     # Entry point
└── README.md            # Project documentation
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Open a pull request

## License

MIT
