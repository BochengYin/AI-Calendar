# AI Calendar

An intelligent calendar application that uses AI to manage your events through natural conversation. Create, delete, and reschedule events using simple chat interactions.

## Features

- 🗣️ Natural language event creation
- 📅 Interactive calendar view
- 🔄 Event rescheduling
- 🗑️ Event deletion (soft-delete with cleanup)
- 📝 Optional event description field
- 🐱 Clean, minimal UI with Apple-inspired design

## Tech Stack

### Frontend
- React
- React Big Calendar
- CSS3 with modern styling
- Supabase Authentication

### Backend
- Flask (Python)
- OpenAI API (GPT-4o-mini)
- RESTful API design
- Supabase (PostgreSQL Database)

## Setup and Installation

### Prerequisites
- Node.js (v14+)
- Python 3.9+
- OpenAI API key
- Supabase account (for authentication and database)

### Supabase Setup
See [SUPABASE_SETUP.md](SUPABASE_SETUP.md) for detailed instructions on setting up Supabase.

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

4. Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_api_key_here
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_service_role_key
   ```

5. Start the backend server:
   ```bash
   # Default port is 12345 (matches frontend fallback and start-servers.sh)
   PORT=12345 python app.py
   ```
   The server will run on http://localhost:12345

👉 Alternatively you can start both servers with the helper script at the repo root:
   ```bash
   ./start-servers.sh
   ```
   This spins up the backend on :12345 and the React dev server on :3000 in parallel.

### Frontend Setup
1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Create a `.env.development` file with your Supabase credentials:
   ```
   REACT_APP_API_URL=http://localhost:12345
   REACT_APP_SUPABASE_URL=your_supabase_url
   REACT_APP_SUPABASE_ANON_KEY=your_supabase_anon_key
   ```

4. Start the development server:
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

## Privacy Policy

We take your privacy seriously. This application:

- **Collects minimal data**: Only your email address (for authentication) and calendar events you create
- **No data sharing**: Your personal information is never shared with third parties
- **Third-party services**: We use Supabase (authentication & database) and OpenAI API (AI assistant)
- **Data usage**: Information is used solely for providing calendar services to you
- **Data deletion**: You can delete your account and all associated data at any time

For complete details, visit our [Privacy Policy](/privacy) page in the application.

**By using this application, you agree to our privacy policy. We only use your email for authentication purposes and do not share your data.**

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Open a pull request

## License

MIT

## Documentation

- 📜 High-level architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 🔌 REST API reference: [docs/API.md](docs/API.md)
