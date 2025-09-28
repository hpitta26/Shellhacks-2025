"""
FastAPI backend for translation service using Google ADK agent
"""
import asyncio
import json
import uuid
import os
import sys
import tempfile
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

# Add project root to Python path so we can import translation_agency_v2
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.append(project_root)

# Import the v2 translation workflow with correct content file path
from translation_agency_v2.agent import create_content_agnostic_workflow, APP_NAME

# Create the workflow with the correct path to website_content.json
content_file_path = os.path.join(project_root, 'translation_agency_v2', 'website_content.json')
root_agent, content_batches, content_processor = create_content_agnostic_workflow(content_file_path)

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
    display_title: str  # Include display_title from file 2
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

def convert_frontend_to_v2_format(frontend_sections):
    """Convert frontend section format to v2 agent format"""
    pages = {}
    
    for i, section in enumerate(frontend_sections, 1):
        group_key = f"group_{i}"
        
        # Access Pydantic model attributes directly (not with .get())
        display_title = getattr(section, 'display_title', None)
        title = getattr(section, 'title', None)
        meta_data = display_title or title or f"Section {i}"
        
        group_data = {
            "meta_data": meta_data
        }
        
        # Convert content items to v2 format
        for j, content_item in enumerate(section.content, 1):
            item_key = f"item_{j}"
            group_data[item_key] = {
                "type": content_item.type,
                "value": content_item.value
            }
        
        pages[group_key] = group_data
    
    return {
        "website_metadata": {
            "site_name": "Demo Website",
            "language": "en",
            "locale": "en-US",
            "version": "1.0.0"
        },
        "pages": pages
    }

def convert_v2_to_frontend_format(v2_state, original_sections):
    """Convert v2 agent results back to frontend format"""
    translated_sections = []
    
    for i, original_section in enumerate(original_sections):
        # Look for translation results in v2 state
        translation_key = f"translation_{i+1}"
        if translation_key in v2_state:
            translation_data = v2_state[translation_key]
            
            # Parse the v2 translation results
            if isinstance(translation_data, str):
                try:
                    translation_json = json.loads(translation_data)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse translation {i+1}, using original")
                    translation_json = {"items": []}
            else:
                translation_json = translation_data
            
            # Convert back to frontend format
            translated_content = []
            items = translation_json.get("items", [])
            
            for j, original_content in enumerate(original_section.content):
                if j < len(items):
                    # Use translated value
                    translated_content.append(SectionItem(
                        type=original_content.type,
                        value=items[j]["value"]
                    ))
                else:
                    # Fallback to original if translation missing
                    translated_content.append(original_content)
            
            translated_sections.append(Section(
                section_id=original_section.section_id,
                title=original_section.title,
                display_title=original_section.display_title,
                content=translated_content
            ))
        else:
            # No translation found, return original
            translated_sections.append(original_section)
    
    return translated_sections
def create_v2_session_state(v2_content, target_language):
    """Create proper session state for v2 agent"""
    from translation_agency_v2.batch_processor import ContentBatchProcessor
    
    # Create a temporary content file (in memory)
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(v2_content, f, indent=2)
        temp_file = f.name
    
    try:
        # Use the batch processor to create proper state
        processor = ContentBatchProcessor(temp_file)
        processor.load_content()
        batches = processor.create_batches()
        
        # Create initial state like the v2 agent expects
        initial_state = {
            "target_language": target_language,
            "brand_terms": processor.get_brand_terms(),
            "glossary_terms": processor.get_glossary_terms(),
            "total_batches": len(batches),
        }
        
        # Add source content for each batch
        for i, batch in enumerate(batches):
            initial_state[f"source_text_{i+1}"] = batch.get_formatted_content()
            
        return initial_state
        
    finally:
        # Clean up temp file
        os.unlink(temp_file)

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

# Helper function to translate a single text item (from file 1)
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

@app.post("/translate-sections", response_model=SectionsTranslationResponse)
async def translate_sections(request: SectionsTranslationRequest):
    """
    Translate multiple website sections using the v2 batch translation agent
    """
    try:
        logger.info(f"V2 Sections translation request: {len(request.sections)} sections -> {request.target_language}")
        
        session_id = f"v2_sections_{uuid.uuid4().hex[:8]}"
        user_id = "api_user"
        
        # Convert frontend format to v2 format
        v2_content = convert_frontend_to_v2_format(request.sections)
        logger.info(f"Converted to v2 format: {len(v2_content['pages'])} groups")
        
        # Create proper session state for v2 agent
        initial_state = create_v2_session_state(v2_content, request.target_language)
        
        # Create session
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
            state=initial_state
        )
        
        logger.info(f"✅ V2 Session created: {session.id}")
        
        # Create runner with the v2 translation agent
        runner = Runner(
            agent=root_agent,
            app_name=APP_NAME,
            session_service=session_service
        )
        
        # Create user message to trigger v2 workflow
        user_message = Content(parts=[Part(text=f"Please translate all content batches to {request.target_language}")])
        
        logger.info("🔄 Running V2 batch translation workflow...")
        
        # Run the v2 agent workflow
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_message
        ):
            if event.is_final_response() and event.content:
                logger.info(f"✅ V2 Stage completed by {event.author}")
        
        # Get final session state with translations
        final_session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id
        )
        
        if final_session:
            state = final_session.state if isinstance(final_session.state, dict) else final_session.state.to_dict()
            
            # Check what translations we got
            translation_keys = [k for k in state.keys() if k.startswith('translation_')]
            logger.info(f"📊 V2 Completed translations: {len(translation_keys)}/{len(request.sections)}")
            
            # Convert v2 results back to frontend format
            translated_sections = convert_v2_to_frontend_format(state, request.sections)
            
            logger.info(f"✅ V2 Translation completed: {len(translated_sections)} sections")
            
            return SectionsTranslationResponse(
                translated_sections=translated_sections,
                target_language=request.target_language,
                total_sections=len(translated_sections)
            )
        else:
            logger.error("❌ Failed to retrieve final session")
            raise HTTPException(status_code=500, detail="Failed to retrieve translation results")
        
    except Exception as e:
        logger.error(f"❌ V2 Sections translation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"V2 Sections translation failed: {str(e)}"
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