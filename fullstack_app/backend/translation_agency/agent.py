# Professional Website Translation ADK Agent - Handles batch translation with context and review cycles

import asyncio
import json
from typing import List, Dict, Any, Optional
from google.adk.agents import LoopAgent, LlmAgent, BaseAgent, SequentialAgent, ParallelAgent
from google.genai import types
from google.adk.runners import InMemoryRunner
from google.adk.agents.invocation_context import InvocationContext
from google.adk.tools.tool_context import ToolContext
from google.adk.events import Event, EventActions
from google.adk.sessions import InMemorySessionService, Session
from google.genai.types import Part, Content

# --- Constants ---
APP_NAME = "professional_translation_app_v2"
USER_ID = "translator_user_01"
SESSION_ID_BASE = "website_translation_session"
GEMINI_MODEL = "gemini-2.0-flash"

# --- State Keys ---
STATE_SOURCE_CONTENT = "source_content"
STATE_TARGET_LANGUAGE = "target_language"
STATE_CONTENT_BATCHES = "content_batches"
STATE_TRANSLATIONS = "translations"
STATE_GLOSSARY = "glossary"
STATE_BRAND_TERMS = "brand_terms"
STATE_CLARIFYING_QUESTIONS = "clarifying_questions"
STATE_REVIEW_COMMENTS = "review_comments"
STATE_CONTEXT_WINDOW = "context_window"
STATE_TRANSLATION_STATUS = "translation_status"

# Define completion and status phrases
TRANSLATION_COMPLETE = "All translations verified and complete"
NEEDS_CLARIFICATION = "Clarification needed"
NEEDS_REVISION = "Revision needed"

# Initialize session service
session_service = InMemorySessionService()

def create_translation_session(content: Dict, target_language: str = "Spanish"):
    """Create a new translation session with initial state"""
    return session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=f"{SESSION_ID_BASE}_{id(content)}",
        state={
            "source_content": content,
            "target_language": target_language,
            "content_batches": [],
            "translations": {},
            "glossary": {},
            "brand_terms": [],
            "clarifying_questions": [],
            "review_comments": {},
            "context_window": {},
            "translation_status": "pending"
        }
    )

# --- Tool Definitions ---

def segment_content(tool_context: ToolContext) -> Dict:
    """Segments website content into appropriate batches for translation"""
    content = tool_context.state.get("source_content", {})
    
    batches = []
    batch_id = 0
    
    # Process content structure (assuming JSON structure like localization_example.json)
    def process_section(section_data, parent_key="", context_keys=[]):
        nonlocal batch_id
        
        for key, value in section_data.items():
            full_key = f"{parent_key}.{key}" if parent_key else key
            
            if isinstance(value, dict):
                if "type" in value and "value" in value:
                    # This is a translatable item
                    batch = {
                        "batch_id": batch_id,
                        "key": full_key,
                        "type": value["type"],
                        "content": value["value"],
                        "context_keys": context_keys.copy(),
                        "status": "pending"
                    }
                    batches.append(batch)
                    batch_id += 1
                else:
                    # Nested structure, recurse
                    process_section(value, full_key, context_keys + [full_key])
            elif isinstance(value, list):
                # Handle arrays (like testimonials)
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        process_section(item, f"{full_key}[{i}]", context_keys + [full_key])
    
    if isinstance(content, dict):
        process_section(content)
    
    tool_context.state["content_batches"] = batches
    return {"batches_created": len(batches), "status": "segmented"}

def build_context_window(tool_context: ToolContext, batch_id: int) -> Dict:
    """Builds context window for a specific batch"""
    batches = tool_context.state.get("content_batches", [])
    target_batch = None
    
    for batch in batches:
        if batch["batch_id"] == batch_id:
            target_batch = batch
            break
    
    if not target_batch:
        return {"error": "Batch not found"}
    
    # Get surrounding content for context
    context = {
        "target": target_batch,
        "section_context": [],
        "related_translations": {}
    }
    
    # Find related batches in same section
    for batch in batches:
        if batch["key"].startswith(target_batch["context_keys"][0] if target_batch["context_keys"] else ""):
            if batch["batch_id"] != batch_id:
                context["section_context"].append({
                    "key": batch["key"],
                    "content": batch["content"],
                    "type": batch["type"]
                })
                
                # Include any already translated related content
                if batch["batch_id"] in tool_context.state.get("translations", {}):
                    context["related_translations"][batch["key"]] = tool_context.state["translations"][batch["batch_id"]]
    
    tool_context.state["context_window"][batch_id] = context
    return {"context_built": True, "batch_id": batch_id}

def load_glossary(tool_context: ToolContext) -> Dict:
    """Loads glossary and brand terms from previous translations"""
    # In production, this would load from a database
    # For now, we'll use some example terms
    glossary = {
        "Octopi Poker": "Octopi Poker",  # Brand name - don't translate
        "The Vault": "The Vault",  # Product name - keep as is
        "grinders": {"Spanish": "jugadores dedicados", "French": "joueurs acharnés"},
        "ICM": "ICM",  # Technical term - keep as is
        "GTO": "GTO",  # Technical term - keep as is
    }
    
    brand_terms = ["Octopi", "Octopi Poker", "The Vault", "Ask George", "Octopi Store"]
    
    tool_context.state["glossary"] = glossary
    tool_context.state["brand_terms"] = brand_terms
    
    return {"glossary_loaded": len(glossary), "brand_terms_loaded": len(brand_terms)}

def add_clarifying_question(tool_context: ToolContext, batch_id: int, question: str) -> Dict:
    """Adds a clarifying question for a specific batch"""
    questions = tool_context.state.get("clarifying_questions", [])
    questions.append({
        "batch_id": batch_id,
        "question": question,
        "status": "pending",
        "answer": None
    })
    tool_context.state["clarifying_questions"] = questions
    return {"question_added": True, "batch_id": batch_id}

def answer_clarifying_question(tool_context: ToolContext, batch_id: int, answer: str) -> Dict:
    """Provides answer to a clarifying question"""
    questions = tool_context.state.get("clarifying_questions", [])
    
    for q in questions:
        if q["batch_id"] == batch_id and q["status"] == "pending":
            q["answer"] = answer
            q["status"] = "answered"
            tool_context.state["clarifying_questions"] = questions
            return {"question_answered": True, "batch_id": batch_id}
    
    return {"error": "Question not found or already answered"}

def save_translation(tool_context: ToolContext, batch_id: int, translation: str) -> Dict:
    """Saves a translation for a specific batch"""
    translations = tool_context.state.get("translations", {})
    translations[batch_id] = translation
    tool_context.state["translations"] = translations
    
    # Update batch status
    batches = tool_context.state.get("content_batches", [])
    for batch in batches:
        if batch["batch_id"] == batch_id:
            batch["status"] = "translated"
            break
    tool_context.state["content_batches"] = batches
    
    return {"translation_saved": True, "batch_id": batch_id}

def add_review_comment(tool_context: ToolContext, batch_id: int, comment: str) -> Dict:
    """Adds a review comment for a translation"""
    comments = tool_context.state.get("review_comments", {})
    if batch_id not in comments:
        comments[batch_id] = []
    comments[batch_id].append(comment)
    tool_context.state["review_comments"] = comments
    
    # Mark batch as needing revision
    batches = tool_context.state.get("content_batches", [])
    for batch in batches:
        if batch["batch_id"] == batch_id:
            batch["status"] = "needs_revision"
            break
    tool_context.state["content_batches"] = batches
    
    return {"comment_added": True, "batch_id": batch_id}

def mark_batch_complete(tool_context: ToolContext, batch_id: int) -> Dict:
    """Marks a batch as complete"""
    batches = tool_context.state.get("content_batches", [])
    for batch in batches:
        if batch["batch_id"] == batch_id:
            batch["status"] = "complete"
            break
    tool_context.state["content_batches"] = batches
    return {"batch_complete": True, "batch_id": batch_id}

def check_all_complete(tool_context: ToolContext) -> Dict:
    """Checks if all batches are complete"""
    batches = tool_context.state.get("content_batches", [])
    all_complete = all(batch["status"] == "complete" for batch in batches)
    
    if all_complete:
        tool_context.state["translation_status"] = "complete"
        tool_context.actions.escalate = True
    
    return {"all_complete": all_complete}

# --- Agent Definitions ---

# STEP 1: Content Segmentation Agent
content_segmentation_agent = LlmAgent(
    name="ContentSegmentationAgent",
    model=GEMINI_MODEL,
    include_contents='default',
    instruction="""You are a content segmentation specialist for website localization.

    Your task:
    1. Call `segment_content` to break down the website content into translatable batches
    2. Call `load_glossary` to load brand terms and glossary
    
    After segmentation, output a brief summary of the segmentation results.""",
    description="Segments content and prepares for translation",
    tools=[segment_content, load_glossary],
)

# STEP 2: Context Builder Agent
context_builder_agent = LlmAgent(
    name="ContextBuilderAgent",
    model=GEMINI_MODEL,
    include_contents='default',
    instruction="""You are a context builder for translation tasks.
    
    Look at the content batches in the state.
    For each batch that needs translation (status='pending'):
    1. Call `build_context_window` with the batch_id
    
    This ensures translators have proper context for accurate translation.
    
    Output a summary of context windows built.""",
    description="Builds context for each translation batch",
    tools=[build_context_window],
)

# STEP 3: Batch Translator Agent
batch_translator_agent = LlmAgent(
    name="BatchTranslatorAgent",
    model=GEMINI_MODEL,
    include_contents='default',
    instruction="""You are a professional website translator with expertise in localization.
    
    Review the content batches and for each batch with status='pending':
    
    1. Check the context window for that batch
    2. Consider the glossary and brand terms (DO NOT translate brand terms)
    3. Apply these localization rules:
       - Headers: Keep concise and impactful
       - Content: Maintain tone and style appropriate for the target market
       - Buttons: Use action-oriented language common in the target locale
       - Convert measurements, dates, and currency formats as needed
    
    4. If you need clarification about context or meaning:
       - Call `add_clarifying_question` with the batch_id and your question
       - Mark the batch status appropriately
    
    5. If translation is clear:
       - Call `save_translation` with the batch_id and translation
    
    Focus on maintaining consistency across related content using the context window.
    Pay special attention to repeated terms and ensure they're translated consistently.""",
    description="Translates content batches with context awareness",
    tools=[save_translation, add_clarifying_question],
)

# STEP 4: Translation Reviewer Agent
translation_reviewer_agent = LlmAgent(
    name="TranslationReviewerAgent",
    model=GEMINI_MODEL,
    include_contents='default',
    instruction="""You are a senior translation reviewer ensuring quality and consistency.
    
    For each translated batch:
    
    1. First check for any pending clarifying questions:
       - If found, provide contextual answers using `answer_clarifying_question`
       - Trigger re-translation for those batches
    
    2. Review completed translations for:
       - Accuracy: Does it convey the original meaning?
       - Fluency: Does it sound natural in the target language?
       - Consistency: Are terms translated consistently across batches?
       - Localization: Are formats, measurements, and cultural references appropriate?
       - Brand compliance: Are brand terms preserved correctly?
    
    3. For each batch:
       - If translation is good: Call `mark_batch_complete`
       - If needs revision: Call `add_review_comment` with specific feedback
    
    4. After reviewing all batches, call `check_all_complete`
    
    Be thorough but efficient. Focus on substantive issues that affect meaning or user experience.""",
    description="Reviews and validates all translations",
    tools=[answer_clarifying_question, mark_batch_complete, add_review_comment, check_all_complete],
)

# STEP 5: Revision Handler Agent
revision_handler_agent = LlmAgent(
    name="RevisionHandlerAgent",
    model=GEMINI_MODEL,
    include_contents='default',
    instruction="""You are a revision specialist who handles translation corrections.
    
    Look for batches with status='needs_revision':
    
    1. Read the review comments for each batch
    2. Access the original translation and context
    3. Apply the suggested corrections while maintaining:
       - Consistency with other translations
       - Proper use of glossary terms
       - Brand term preservation
    
    4. Save the revised translation using `save_translation`
    5. Update the batch status appropriately
    
    Focus on addressing the specific issues raised in review comments.""",
    description="Handles translation revisions based on review feedback",
    tools=[save_translation],
)

# Translation Loop for iterative refinement
translation_refinement_loop = LoopAgent(
    name="TranslationRefinementLoop",
    sub_agents=[
        batch_translator_agent,
        translation_reviewer_agent,
        revision_handler_agent,
    ],
    max_iterations=3  # Maximum refinement cycles
)

# Main Translation Pipeline
root_agent = SequentialAgent(
    name="ProfessionalWebsiteTranslationPipeline",
    sub_agents=[
        content_segmentation_agent,
        context_builder_agent,
        translation_refinement_loop,
    ],
    description="Professional website translation with batch processing, context awareness, and quality review cycles"
)

# Export the agent
__all__ = ["root_agent", "create_translation_session"]