#!/usr/bin/env python3
"""
FastAPI backend for translation service using Google ADK agent.
Updated to dynamically pad requests to match the static agent's structure.
"""
import os
import sys
import uuid
import logging
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

# Import the pre-built agent and its configuration from agent.py
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, parent_dir)

from translation_agency_v2.agent import root_agent, APP_NAME as AGENT_APP_NAME, content_batches

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title="Dynamic Content Translation API",
    description="Uses a statically-defined, content-agnostic ADK agent to translate dynamically provided web content.",
    version="2.2.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Models ---
class SectionContent(BaseModel):
    type: str
    value: str


class PageSection(BaseModel):
    section_id: str
    title: str
    content: List[SectionContent]


class MultiSectionTranslationRequest(BaseModel):
    sections: List[PageSection]
    target_language: str = "Spanish"


class MultiSectionTranslationResponse(BaseModel):
    translated_sections: List[PageSection]
    target_language: str
    session_id: str
    total_sections: int


# --- Global Services & Constants ---
session_service = InMemorySessionService()
APP_NAME = AGENT_APP_NAME
# Get the number of groups the agent was built to expect
if callable(content_batches):
    actual_batches = content_batches()
    NUM_EXPECTED_AGENT_GROUPS = len(actual_batches)
else:
    NUM_EXPECTED_AGENT_GROUPS = len(content_batches)


# --- Helper Function ---
def parse_translation_output(data: Any) -> List[str]:
    """Safely parses various possible agent outputs into a list of strings."""
    if not data:
        return []

    # Handle Pydantic model with items attribute
    if hasattr(data, 'items') and not callable(getattr(data, 'items')):
        return [item.value for item in data.items]

    # Handle dictionary with 'items' key
    if isinstance(data, dict) and 'items' in data:
        items = data.get('items', [])
        return [item.get('value', '') if isinstance(item, dict) else str(item) for item in items]

    # Handle list directly
    if isinstance(data, list):
        return [str(item.get('value', item)) if isinstance(item, dict) else str(item) for item in data]

    # Handle string representation of JSON
    if isinstance(data, str):
        try:
            import json
            parsed = json.loads(data)
            if isinstance(parsed, dict) and 'items' in parsed:
                return [item.get('value', '') for item in parsed.get('items', [])]
        except (json.JSONDecodeError, AttributeError):
            pass

    # Fallback - return as single string
    return [str(data)]

# --- API Endpoints ---
@app.get("/")
async def root():
    return {"message": "Dynamic Translation API is running"}


@app.post("/translate-sections", response_model=MultiSectionTranslationResponse)
async def translate_sections(request: MultiSectionTranslationRequest):
    session_id = f"padded_{uuid.uuid4().hex[:8]}"
    user_id = "api_user_padded"
    logger.info(f"=== TRANSLATION REQUEST START ===")
    logger.info(f"Request sections: {len(request.sections)}")
    logger.info(f"Agent expects: {NUM_EXPECTED_AGENT_GROUPS}")
    logger.info(f"Target language: {request.target_language}")

    try:
        # 1. Prepare Padded Initial State - ADD MORE LOGGING
        initial_state = {
            "target_language": request.target_language,
            "glossary_terms": {"wildlife": "vida silvestre"},
            "brand_terms": ["WildGuard Conservation"]
        }

        for i in range(1, NUM_EXPECTED_AGENT_GROUPS + 1):
            state_key = f"source_text_{i}"
            if i <= len(request.sections):
                section = request.sections[i - 1]
                content_text = "\n".join(f"[{item.type.upper()}] {item.value}" for item in section.content)
                initial_state[state_key] = content_text
                logger.info(f"✅ {state_key}: {len(content_text)} chars - {content_text[:100]}...")
            else:
                initial_state[state_key] = ""
                logger.info(f"📝 {state_key}: PADDED WITH EMPTY STRING")

        # 2. Log the complete initial state
        logger.info(f"=== INITIAL STATE SUMMARY ===")
        for key, value in initial_state.items():
            if key.startswith('source_text_'):
                logger.info(f"{key}: {len(str(value)) if value else 0} characters")

        # 3. Create session with detailed logging
        logger.info(f"Creating session: app={APP_NAME}, user={user_id}, session={session_id}")
        await session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id, state=initial_state
        )

        # 4. Run agent with exception handling
        runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)
        user_message = Content(parts=[Part(text=f"Translate all sections to {request.target_language}.")])

        logger.info(f"=== STARTING AGENT EXECUTION ===")
        event_count = 0
        try:
            async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=user_message):
                event_count += 1
                logger.info(f"Event {event_count}: {type(event).__name__}")
                if hasattr(event, 'agent_name'):
                    logger.info(f"  Agent: {event.agent_name}")
                if hasattr(event, 'output_key'):
                    logger.info(f"  Output key: {event.output_key}")
                if event.is_final_response():
                    logger.info(f"Final response received after {event_count} events")
                    break
        except Exception as agent_error:
            logger.error(f"AGENT EXECUTION ERROR: {agent_error}", exc_info=True)
            raise

        # 5. Get final session state with detailed logging
        logger.info(f"=== RETRIEVING FINAL SESSION STATE ===")
        final_session = await session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)

        if not final_session:
            logger.error("No final session found!")
            raise HTTPException(status_code=500, detail="Session not found after translation")

        state_dict = final_session.state if final_session else {}
        if hasattr(state_dict, 'to_dict'):
            state_dict = state_dict.to_dict()

        # 6. Log all available state keys
        logger.info(f"=== FINAL STATE KEYS ===")
        for key in state_dict.keys():
            logger.info(f"State key: {key}")

        # 7. Check each translation result
        logger.info(f"=== TRANSLATION RESULTS CHECK ===")
        for i in range(1, NUM_EXPECTED_AGENT_GROUPS + 1):
            translation_key = f"translation_{i}"
            if translation_key in state_dict:
                result = state_dict[translation_key]
                logger.info(f"✅ {translation_key}: {type(result)} - {str(result)[:200]}...")
            else:
                logger.warning(f"❌ {translation_key}: NOT FOUND IN STATE")

        # Rest of your existing response construction code...
        reconstructed_sections = []
        for i, section in enumerate(request.sections, 1):
            new_section = section.copy(deep=True)
            translation_key = f"translation_{i}"
            translation_data = state_dict.get(translation_key)

            logger.info(f"=== PROCESSING SECTION {i} ===")
            logger.info(f"Original section: {section.section_id}")
            logger.info(f"Looking for key: {translation_key}")

            if translation_data:
                logger.info(f"Found translation data: {type(translation_data)}")
                translated_values = parse_translation_output(translation_data)
                logger.info(f"Parsed {len(translated_values)} translated values")

                for j, content_item in enumerate(new_section.content):
                    if j < len(translated_values):
                        old_value = content_item.value
                        content_item.value = translated_values[j]
                        logger.info(f"  Item {j}: '{old_value[:50]}...' -> '{translated_values[j][:50]}...'")
                    else:
                        content_item.value = "[Translation Missing]"
                        logger.warning(f"  Item {j}: NO TRANSLATION AVAILABLE")
            else:
                logger.error(f"❌ No translation found for {translation_key}")
                # Mark all content as missing translation
                for content_item in new_section.content:
                    content_item.value = f"[Translation Failed for {translation_key}]"

            reconstructed_sections.append(new_section)

        logger.info(f"=== TRANSLATION COMPLETE ===")
        logger.info(f"Reconstructed {len(reconstructed_sections)} sections")

        return MultiSectionTranslationResponse(
            translated_sections=reconstructed_sections,
            target_language=request.target_language,
            session_id=session_id,
            total_sections=len(reconstructed_sections)
        )

    except Exception as e:
        logger.error(f"❌ TRANSLATION FAILED: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Translation failed: {e}")