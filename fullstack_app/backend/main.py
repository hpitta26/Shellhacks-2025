"""
FastAPI backend for translation service using Google ADK agent
"""
import asyncio
import uuid
import os
import json
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import the translation agent - make sure this matches your agent file
from translation_agency.agent import root_agent, APP_NAME, create_translation_session

# RUN APP --> python -m uvicorn main:app --reload --port 8000
# API DOCS --> http://127.0.0.1:8000/docs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Translation API",
    description="AI-powered translation service using Google ADK agent",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS - Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:5173", 
        "http://localhost:5174",
        "http://localhost:8080"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Pydantic models for request/response validation
class TranslationRequest(BaseModel):
    json_content: str  # Always expect JSON as string
    target_language: str = "Spanish"

class TranslationResponse(BaseModel):
    original_json: dict  # Return original JSON structure
    translated_json: dict  # Return translated JSON structure
    target_language: str
    session_id: str

# Initialize session service
session_service = InMemorySessionService()

@app.on_event("startup")
async def startup_event():
    logger.info("Translation API starting up...")
    logger.info(f"Agent loaded: {root_agent.name}")
    logger.info(f"App name: {APP_NAME}")
    logger.info("Translation API ready!")

@app.get("/")
async def root():
    """Root endpoint - API status"""
    return {"message": "Translation API is running", "status": "healthy"}

@app.post("/translate", response_model=TranslationResponse)
async def translate_json(request: TranslationRequest):
    """
    Translate JSON content using the professional translation pipeline
    with batch processing, context awareness, and quality review.
    """
    try:
        logger.info(f"JSON translation request for language: {request.target_language}")
        
        # Validate JSON
        try:
            original_data = json.loads(request.json_content)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
        
        # Generate unique session ID
        session_id = f"json_translation_{uuid.uuid4().hex[:8]}"
        user_id = "api_user"
        
        # Create session using the agent's session creation function
        session = create_translation_session(original_data, request.target_language)
        
        # Create runner
        runner = Runner(
            agent=root_agent,
            app_name=APP_NAME,
            session_service=session_service
        )
        
        # Create user message with JSON content
        user_message = Content(parts=[Part(text=f"Please translate this JSON content to {request.target_language}: {request.json_content}")])
        
        # Run the agent
        final_response = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.session_id,
            new_message=user_message
        ):
            if event.is_final_response():
                final_response = event.content.parts[0].text if event.content and event.content.parts else ""
                break
        
        # Get the final session state to retrieve translations
        updated_session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session.session_id
        )
        
        # Extract translations from state
        translations = updated_session.state.get("translations", {})
        batches = updated_session.state.get("content_batches", [])
        status = updated_session.state.get("translation_status", "unknown")
        
        # Build translated JSON structure
        translated_data = build_translated_json(original_data, translations, batches)
        
        logger.info(f"JSON translation completed: {len(translations)} items translated")
        
        return TranslationResponse(
            original_json=original_data,
            translated_json=translated_data,
            target_language=request.target_language,
            session_id=session.session_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JSON translation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"JSON translation failed: {str(e)}"
        )

def build_translated_json(original_data: dict, translations: dict, batches: list) -> dict:
    """Build the translated JSON structure preserving the original format"""
    import copy
    
    # Create a deep copy of the original data
    translated_data = copy.deepcopy(original_data)
    
    # Create a mapping from batch keys to translations
    translation_map = {}
    for batch in batches:
        batch_id = batch["batch_id"]
        if batch_id in translations:
            translation_map[batch["key"]] = translations[batch_id]
    
    # Recursively apply translations while preserving structure
    def apply_translations(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                
                if isinstance(value, dict) and "type" in value and "value" in value:
                    # This is a translatable item
                    if current_path in translation_map:
                        obj[key]["value"] = translation_map[current_path]
                elif isinstance(value, dict):
                    apply_translations(value, current_path)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            apply_translations(item, f"{current_path}[{i}]")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, dict):
                    apply_translations(item, f"{path}[{i}]")
    
    apply_translations(translated_data)
    return translated_data

@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    return {
        "status": "healthy",
        "service": "translation-api",
        "agent": "Professional Website Translation Agent",
        "version": "1.0.0",
        "app_name": APP_NAME
    }

@app.get("/supported-languages")
async def get_supported_languages():
    """Get list of supported target languages"""
    return {
        "languages": [
            "Spanish", "French", "German", "Italian", "Portuguese", 
            "Chinese (Mandarin)", "Japanese", "Korean", "Arabic", 
            "Russian", "Hindi", "Dutch", "Swedish", "Polish", "Turkish"
        ]
    }

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Translation API shutting down...")
    # Clean up any resources if needed
    logger.info("Translation API shutdown complete")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)