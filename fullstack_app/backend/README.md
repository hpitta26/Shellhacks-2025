# Translation API Backend

FastAPI backend service that provides translation capabilities using Google ADK agent with iterative refinement.

## Features

- 🌐 RESTful API for text translation
- 🔄 Iterative translation refinement using ADK agents
- 🎯 Support for multiple target languages
- 📊 Request/response validation with Pydantic
- 🔍 Interactive API documentation
- ⚡ Fast async processing

## API Endpoints

### `POST /translate`
Translate text from English to any target language.

**Request Body:**
```json
{
  "source_text": "Hello, how are you?",
  "target_language": "Spanish"
}
```

**Response:**
```json
{
  "original_text": "Hello, how are you?",
  "translated_text": "Hola, ¿cómo estás?",
  "target_language": "Spanish",
  "session_id": "translation_abc12345"
}
```

### `GET /health`
Health check endpoint for monitoring.

### `GET /`
Simple status endpoint.

## Running the Server

### Prerequisites
Make sure you have the virtual environment activated and all dependencies installed:

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies (if not already done)
pip install -r requirements.txt
```

### Start the Server

```bash
# From the project root
cd backend
python run.py
```

The server will start at `http://localhost:8080`

### Interactive Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

## Testing

Run the test script to verify the API works:

```bash
# Make sure the server is running first, then in another terminal:
python backend/test_api.py
```

## Supported Languages

The API supports translation to many languages including:
- Spanish
- French  
- German
- Italian
- Portuguese
- Chinese (Mandarin)
- Japanese
- Korean
- Arabic
- Russian
- Hindi
- Dutch
- Swedish
- Polish
- Turkish

## How It Works

1. **Request Processing**: API receives translation request with source text and target language
2. **Session Creation**: Creates a unique session with initial state for the ADK agent
3. **Agent Execution**: Runs the translation pipeline:
   - Initial translation
   - Quality critique
   - Iterative refinement (up to 5 iterations)
4. **Response**: Returns the final refined translation

## Architecture

```
FastAPI Backend → ADK Agent Pipeline → Gemini 2.0 Flash Model
     ↓              ↓                     ↓
Request Validation  Translation Workflow  LLM Processing
Session Management  Quality Assurance     Response Generation
```

The backend integrates seamlessly with the ADK translation agent defined in `translation_agency/agent.py`.
