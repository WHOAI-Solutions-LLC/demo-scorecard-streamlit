# Scorecard Chat Streamlit UI

A simple Streamlit application for testing the backend scorecard chat functionality.

## Features

- **Simple Modal**: Input job title, optional thread ID, and authorization token
- **Chat Interface**: Real-time chat with WhoaAI assistant
- **Scorecard Preview**: Visual representation of scorecard sections
- **WebSocket Integration**: Connects to backend WebSocket endpoint with authorization
- **History Loading**: Load existing conversations using thread ID
- **Loading States**: Disable send button while waiting for response

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. **Configure Environment Variables (Optional):**
   
   Create a `.env` file in the project root to customize the backend URLs:
   ```bash
   # .env file
   WEBSOCKET_URL=ws://localhost:8003/api/v1/scorecard/chat
   API_BASE_URL=http://localhost:8003/api/v1/scorecard
   ```
   
   If no `.env` file is provided, the application will use the default localhost URLs.

3. Make sure your backend server is running on the configured host/port (default: `localhost:8003`)

4. Run the Streamlit application:
```bash
streamlit run app.py
```

## Usage

1. **Modal Page**: 
   - Enter a job title (required)
   - Optionally enter an authorization token for protected endpoints
   - Optionally enter a thread ID to continue an existing conversation
   - Click "Continue to WhoaAI →" to proceed

2. **Chat Page**:
   - Chat with the WhoaAI assistant
   - View scorecard preview on the right side
   - Use "Save Draft" to save progress
   - Click "Complete Scorecard" when finished

## API Endpoints

- **WebSocket**: Configurable via `WEBSOCKET_URL` (default: `ws://localhost:8003/api/v1/scorecard/chat`)
- **History**: Configurable via `API_BASE_URL` (default: `http://localhost:8003/api/v1/scorecard/history/{thread_id}`)

## WebSocket Message Format

```json
{
  "type": "user_message",
  "job_title": "string",
  "content": "string",
  "thread_id": "string (optional)"
}
```

## Authorization

The application supports Bearer token authentication:
- Add your authorization token in the modal page
- Token will be included in both HTTP requests and WebSocket connections
- Format: `Authorization: Bearer <your_token>`

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WEBSOCKET_URL` | WebSocket endpoint for real-time chat | `ws://localhost:8003/api/v1/scorecard/chat` |
| `API_BASE_URL` | Base URL for REST API endpoints | `http://localhost:8003/api/v1/scorecard` |

## File Structure

```
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (create this file)
└── README.md          # This file
``` 