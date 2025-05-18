# AI Calendar Backend

This is the backend for the AI Calendar application, which provides an API for chat-based event management using OpenAI's GPT models.

## Environment Variables

The following environment variables are required:

- `OPENAI_API_KEY`: Your OpenAI API key
- `PORT`: (Optional) Port number to run the server on (defaults to 8000)

## Local Development

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Create a `.env` file with your environment variables (see `.env.sample`)

3. Run the server:
   ```
   python app.py
   ```

## Deployment

### Render

This backend is configured for deployment on Render.com:

1. Create a new Web Service
2. Connect your GitHub repository
3. Configure:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
4. Add environment variables:
   - OPENAI_API_KEY

## API Endpoints

### Health Check Endpoint
- `GET /api/health` - Check if the backend is running
  - Returns: `{"status": "ok", "api_key_configured": true, ...}`

### Events Endpoints
- `GET /api/events` - Get all events
- `POST /api/events` - Create a new event
- `PUT /api/events/:id` - Update an event
- `DELETE /api/events/:id` - Delete an event

### Chat Endpoint
- `POST /api/chat` - Send a message to the AI assistant

## Troubleshooting

If the health check is failing:
1. Check that the server is running (`python app.py` or `gunicorn app:app`)
2. Verify the API endpoint URL is correct
3. Check CORS configuration if needed
4. See `RENDER_DEPLOY.md` for specific Render deployment instructions

## API Endpoints

- `GET /api/test-openai`: Test OpenAI API connection 