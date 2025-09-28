"""
FastAPI backend for translation service using Google ADK agent
Updated to support multi-section page translation using v2 agent
"""
import asyncio
import uuid
import os
import json
from typing import Optional, Dict, Any, List
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

# Import the v2 translation agent
import sys
import os
# Add the parent directory to find translation_agency_v2
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from translation_agency_v2.agent import root_agent, APP_NAME as AGENT_APP_NAME

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Translation API",
    description="AI-powered translation service using Google ADK agent v2",
    version="2.0.0",
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
class SectionContent(BaseModel):
    type: str  # header, content, button
    value: str

class PageSection(BaseModel):
    section_id: str
    title: str
    display_title: Optional[str] = None  # Add display_title
    content: List[SectionContent]

class MultiSectionTranslationRequest(BaseModel):
    sections: List[PageSection]
    target_language: str = "Spanish"

class TranslatedSection(BaseModel):
    section_id: str
    title: str
    display_title: Optional[str] = None  # Add translated display_title
    content: List[SectionContent]
    
class MultiSectionTranslationResponse(BaseModel):
    translated_sections: List[TranslatedSection]
    target_language: str
    session_id: str
    total_sections: int

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
APP_NAME = AGENT_APP_NAME  # Use the same app name as your agent

@app.on_event("startup")
async def startup_event():
    logger.info("Multi-Section Translation API starting up...")
    logger.info("Using Translation Agency V2 agent")
    logger.info("Translation API ready!")

@app.get("/")
async def root():
    """Root endpoint - API status"""
    return {"message": "Multi-Section Translation API v2 is running", "status": "healthy"}

@app.post("/translate-sections", response_model=MultiSectionTranslationResponse)
async def translate_sections(request: MultiSectionTranslationRequest):
    """
    Translate multiple page sections using the v2 translation agent
    """
    try:
        logger.info(f"Multi-section translation request: {len(request.sections)} sections -> {request.target_language}")
        
        # Generate unique session ID
        session_id = f"multi_section_{uuid.uuid4().hex[:8]}"
        user_id = "api_user"
        
        # Convert sections to the v2 agent format exactly as it expects
        initial_state = {
            "target_language": request.target_language,
            "glossary_terms": {
                "AI": "Artificial Intelligence",
                "ML": "Machine Learning", 
                "API": "Application Programming Interface",
                "grinders": "dedicated players",
                "GTO": "Game Theory Optimal"
            },
            "brand_terms": ["TechFlow", "TechFlow Solutions", "Octopi", "George"]
        }
        
        # Format content for each section group exactly as your agent expects
        for i, section in enumerate(request.sections, 1):
            group_id = f"group_{i}"
            formatted_content = ""
            
            # Include display_title in the content to be translated
            if section.display_title:
                formatted_content += f"[DISPLAY_TITLE] {section.display_title}\n"
            
            for content_item in section.content:
                formatted_content += f"[{content_item.type.upper()}] {content_item.value}\n"
            initial_state[f"source_text_{group_id}"] = formatted_content.strip()
            
        logger.info(f"Prepared state with keys: {list(initial_state.keys())}")
        logger.info(f"Sample content: {initial_state.get('source_text_group_1', 'N/A')[:100]}...")
        
        # Create session with initial state
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
            state=initial_state
        )
        
        # Create runner with the v2 translation agent
        runner = Runner(
            agent=root_agent,
            app_name=APP_NAME,
            session_service=session_service
        )
        
        # Create user message to trigger the agent
        user_message = Content(parts=[Part(text=f"Please translate all {len(request.sections)} sections to {request.target_language} using the staged parallel workflow.")])
        
        # Run the v2 agent and capture all responses
        final_response = ""
        agent_responses = []
        
        try:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=user_message
            ):
                if event.content and event.content.parts:
                    response_text = event.content.parts[0].text
                    agent_responses.append(response_text)
                    logger.info(f"Agent response from {event.author}: {response_text[:100]}...")
                    
                if event.is_final_response():
                    final_response = event.content.parts[0].text if event.content and event.content.parts else ""
                    logger.info(f"Final response received: {len(final_response)} chars")
                    
        except Exception as e:
            logger.error(f"Error during agent execution: {str(e)}")
            raise
        
        # Get the final session state to retrieve translations
        updated_session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id
        )
        
        # Parse translations from the session state
        translated_sections = []
        state_dict = updated_session.state if isinstance(updated_session.state, dict) else updated_session.state.to_dict()
        
        logger.info(f"Final state keys: {list(state_dict.keys())}")
        
        # Look for translation keys that your agent produces
        translation_keys = [key for key in state_dict.keys() if key.startswith('translation_group_')]
        if not translation_keys:
            # Try alternative key patterns your agent might use
            translation_keys = [key for key in state_dict.keys() if key.startswith('translation_')]
        
        logger.info(f"Found translation keys: {translation_keys}")
        
        for i, original_section in enumerate(request.sections, 1):
            # Try multiple possible key patterns your agent might use
            possible_keys = [
                f"translation_group_{i}",
                f"translation_{i}",
                f"group_{i}_translation",
                f"translated_group_{i}"
            ]
            
            translation_data = None
            used_key = None
            
            for key in possible_keys:
                if key in state_dict:
                    translation_data = state_dict[key]
                    used_key = key
                    break
            
            if translation_data:
                logger.info(f"Found translation for section {i} using key '{used_key}': {str(translation_data)[:100]}...")
                
                # Handle different formats your agent might return
                if isinstance(translation_data, str):
                    try:
                        # Try to parse as JSON first
                        translation_json = json.loads(translation_data)
                        if "items" in translation_json:
                            translated_items = translation_json["items"]
                        else:
                            # If not structured, treat as single text
                            translated_items = [{"value": translation_data}]
                    except json.JSONDecodeError:
                        # Not JSON, treat as plain text - split by lines
                        lines = translation_data.strip().split('\n')
                        translated_items = [{"value": line.strip()} for line in lines if line.strip()]
                        
                elif isinstance(translation_data, dict):
                    if "items" in translation_data:
                        translated_items = translation_data["items"]
                    else:
                        # Convert dict to items
                        translated_items = [{"value": str(translation_data)}]
                        
                elif isinstance(translation_data, list):
                    # Already a list, ensure proper format
                    translated_items = []
                    for item in translation_data:
                        if isinstance(item, dict) and "value" in item:
                            translated_items.append(item)
                        else:
                            translated_items.append({"value": str(item)})
                else:
                    # Fallback for any other type
                    translated_items = [{"value": str(translation_data)}]
                
                # Map back to section content structure
                translated_content = []
                translated_display_title = None
                content_start_index = 0
                
                # Check if first item is a display_title
                if translated_items and original_section.display_title:
                    translated_display_title = translated_items[0]["value"]
                    content_start_index = 1
                
                for j, original_content in enumerate(original_section.content):
                    translated_index = j + content_start_index
                    if translated_index < len(translated_items):
                        translated_content.append(SectionContent(
                            type=original_content.type,
                            value=translated_items[translated_index]["value"]
                        ))
                    else:
                        # If translation has fewer items, repeat the last one or use original
                        if translated_items:
                            translated_content.append(SectionContent(
                                type=original_content.type,
                                value=translated_items[-1]["value"]  # Use last translated item
                            ))
                        else:
                            translated_content.append(SectionContent(
                                type=original_content.type,
                                value=f"[No translation available]"
                            ))
                
                translated_sections.append(TranslatedSection(
                    section_id=original_section.section_id,
                    title=f"{original_section.title} ({request.target_language})",
                    display_title=translated_display_title,
                    content=translated_content
                ))
                
            else:
                # No translation found for this section
                logger.warning(f"No translation found for section {i}. Available keys: {list(state_dict.keys())}")
                
                # Check if there's any final_translations key
                if 'final_translations' in state_dict:
                    final_trans = state_dict['final_translations']
                    logger.info(f"Found final_translations: {str(final_trans)[:200]}...")
                
                translated_sections.append(TranslatedSection(
                    section_id=original_section.section_id,
                    title=f"[No Translation Found] {original_section.title}",
                    content=[SectionContent(type="content", value="No translation available - check agent output")]
                ))
        
        logger.info(f"Multi-section translation completed: {len(translated_sections)} sections")
        
        return MultiSectionTranslationResponse(
            translated_sections=translated_sections,
            target_language=request.target_language,
            session_id=session_id,
            total_sections=len(translated_sections)
        )
        
    except Exception as e:
        logger.error(f"Multi-section translation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Translation failed: {str(e)}"
        )

@app.post("/translate", response_model=TranslationResponse)
async def translate_text(request: TranslationRequest):
    """
    Original single-text translation endpoint (kept for compatibility)
    """
    try:
        logger.info(f"Single translation request: '{request.source_text}' -> {request.target_language}")
        
        # For single text, create a simple section structure
        simple_section = PageSection(
            section_id="single_text",
            title="Single Text Translation",
            content=[SectionContent(type="content", value=request.source_text)]
        )
        
        # Use the multi-section endpoint internally
        multi_request = MultiSectionTranslationRequest(
            sections=[simple_section],
            target_language=request.target_language
        )
        
        multi_response = await translate_sections(multi_request)
        
        # Extract the single translated text
        if multi_response.translated_sections and multi_response.translated_sections[0].content:
            translated_text = multi_response.translated_sections[0].content[0].value
        else:
            translated_text = "Translation failed"
        
        return TranslationResponse(
            original_text=request.source_text,
            translated_text=translated_text,
            target_language=request.target_language,
            session_id=multi_response.session_id
        )
        
    except Exception as e:
        logger.error(f"Single translation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Translation failed: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    return {
        "status": "healthy",
        "service": "multi-section-translation-api",
        "agent": "Translation Agency V2",
        "version": "2.0.0"
    }

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Multi-Section Translation API shutting down...")
    logger.info("Translation API shutdown complete")