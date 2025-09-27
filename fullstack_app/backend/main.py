"""
FastAPI backend for translation service using Google ADK agent
"""
import asyncio
import uuid
import os
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

# Import the translation agent
from translation_agency.agent import root_agent, APP_NAME

# RUN APP --> python -m uvicorn main:app --reload
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
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Pydantic models for request/response validation
class TranslationRequest(BaseModel):
    source_text: str
    target_language: str = "Spanish"

class TranslationResponse(BaseModel):
    original_text: str
    translated_text: str
    target_language: str
    session_id: str

# Initialize session service
session_service = InMemorySessionService()

@app.on_event("startup")
async def startup_event():
    logger.info("Translation API starting up...")
    logger.info(f"Agent loaded: {root_agent.name}")
    logger.info("Translation API ready!")

@app.get("/")
async def root():
    """Root endpoint - API status"""
    return {"message": "Translation API is running", "status": "healthy"}

@app.post("/translate", response_model=TranslationResponse)
async def translate_text(request: TranslationRequest):
    """
    Translate text from English to the specified target language
    using the ADK translation agent with iterative refinement.
    """
    try:
        logger.info(f"Translation request: '{request.source_text}' -> {request.target_language}")
        
        # Generate unique session ID for this translation
        session_id = f"translation_{uuid.uuid4().hex[:8]}"
        user_id = "api_user"
        
        # Create session with initial state
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
            state={
                "source_text": request.source_text,
                "target_language": request.target_language,
                "current_translation": "",
                "translation_critique": ""
            }
        )
        
        # Create runner with the translation agent
        runner = Runner(
            agent=root_agent,
            app_name=APP_NAME,
            session_service=session_service
        )
        
        # Create a user message to trigger the agent
        user_message = Content(parts=[Part(text=f"Please translate this text to {request.target_language}: {request.source_text}")])
        
        # Run the agent
        final_translation = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_message
        ):
            if event.is_final_response():
                final_translation = event.content.parts[0].text if event.content and event.content.parts else ""
                break
        
        # Get the final session state to retrieve the translation
        updated_session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id
        )
        
        # Extract the final translation from session state
        translated_text = updated_session.state.get("current_translation", final_translation)
        
        logger.info(f"Translation completed: '{translated_text}'")
        
        return TranslationResponse(
            original_text=request.source_text,
            translated_text=translated_text,
            target_language=request.target_language,
            session_id=session_id
        )
        
    except Exception as e:
        logger.error(f"Translation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Translation failed: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    return {
        "status": "healthy",
        "service": "translation-api",
        "agent": "ADK Translation Agent",
        "version": "1.0.0"
    }

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Translation API shutting down...")
    # Clean up any resources if needed
    logger.info("Translation API shutdown complete")