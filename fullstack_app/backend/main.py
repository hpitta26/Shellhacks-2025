"""
FastAPI backend for translation service using Google ADK agent
"""
import asyncio
import json
import uuid
import os
from typing import Optional, List
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

class SectionItem(BaseModel):
    type: str
    value: str

class Section(BaseModel):
    section_id: str
    title: str
    content: List[SectionItem]

class SectionsTranslationRequest(BaseModel):
    sections: List[Section]
    target_language: str = "Spanish"

class SectionsTranslationResponse(BaseModel):
    translated_sections: List[Section]
    target_language: str
    total_sections: int

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


@app.post("/translate-sections", response_model=SectionsTranslationResponse)
async def translate_sections(request: SectionsTranslationRequest):
    try:
        logger.info(f"Sections translation request: {len(request.sections)} sections -> {request.target_language}")

        session_id = f"sections_{uuid.uuid4().hex[:8]}"
        user_id = "api_user"

        translated_sections = []

        for section in request.sections:
            translated_content = []

            for item in section.content:
                if item.type in ['header', 'content', 'button']:
                    # Existing translation logic for simple items
                    translated_text = await translate_single_item(item.value, request.target_language, session_id,
                                                                  user_id)
                    translated_content.append(SectionItem(type=item.type, value=translated_text))

                elif item.type == 'dual_box':
                    # Handle dual_box with nested JSON
                    try:
                        box_data = json.loads(item.value)

                        # Translate left box
                        if 'left' in box_data:
                            box_data['left']['title'] = await translate_single_item(
                                box_data['left']['title'], request.target_language, session_id, user_id
                            )
                            box_data['left']['content'] = await translate_single_item(
                                box_data['left']['content'], request.target_language, session_id, user_id
                            )

                        # Translate right box
                        if 'right' in box_data:
                            box_data['right']['title'] = await translate_single_item(
                                box_data['right']['title'], request.target_language, session_id, user_id
                            )
                            box_data['right']['content'] = await translate_single_item(
                                box_data['right']['content'], request.target_language, session_id, user_id
                            )

                        # Convert back to JSON string
                        translated_json = json.dumps(box_data)
                        translated_content.append(SectionItem(type=item.type, value=translated_json))

                    except json.JSONDecodeError:
                        # If JSON parsing fails, keep original
                        translated_content.append(item)

                else:
                    # For any other unknown types, keep original
                    translated_content.append(item)

            translated_sections.append(Section(
                section_id=section.section_id,
                title=section.title,
                content=translated_content
            ))

        return SectionsTranslationResponse(
            translated_sections=translated_sections,
            target_language=request.target_language,
            total_sections=len(translated_sections)
        )

    except Exception as e:
        logger.error(f"Sections translation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sections translation failed: {str(e)}")


# Helper function to translate a single text item
async def translate_single_item(text: str, target_language: str, base_session_id: str, user_id: str) -> str:
    item_session_id = f"{base_session_id}_{uuid.uuid4().hex[:4]}"

    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=item_session_id,
        state={
            "source_text": text,
            "target_language": target_language,
            "current_translation": "",
            "translation_critique": ""
        }
    )

    runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)
    user_message = Content(parts=[Part(text=f"Translate to {target_language}: {text}")])

    translated_text = ""
    async for event in runner.run_async(user_id=user_id, session_id=item_session_id, new_message=user_message):
        if event.is_final_response():
            translated_text = event.content.parts[0].text if event.content and event.content.parts else text
            break

    updated_session = await session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=item_session_id)
    return updated_session.state.get("current_translation", translated_text)

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