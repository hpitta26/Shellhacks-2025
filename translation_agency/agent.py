# Language Translator ADK Agent - Translates from English to any language with iterative refinement

import asyncio
import os
from google.adk.agents import LoopAgent, LlmAgent, BaseAgent, SequentialAgent
from google.genai import types
from google.adk.runners import InMemoryRunner
from google.adk.agents.invocation_context import InvocationContext
from google.adk.tools.tool_context import ToolContext
from typing import AsyncGenerator, Optional
from google.adk.events import Event, EventActions

from google.adk.sessions import InMemorySessionService, Session
from google.genai.types import Part, Content
import time

# --- Constants ---
APP_NAME = "language_translator_app_v1"
USER_ID = "translator_user_01"
SESSION_ID_BASE = "translation_session"
GEMINI_MODEL = "gemini-2.0-flash"

# --- State Keys ---
STATE_SOURCE_TEXT = "source_text"
STATE_TARGET_LANGUAGE = "target_language"
STATE_CURRENT_TRANSLATION = "current_translation"
STATE_TRANSLATION_CRITIQUE = "translation_critique"

# Define the exact phrase the Critic should use to signal completion
COMPLETION_PHRASE = "Translation is accurate and fluent."

# Initialize session with example text to translate
session_service = InMemorySessionService()
session = session_service.create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID_BASE,
    state={
        "source_text": "The internet has revolutionized how we communicate, learn, and work. It connects billions of people worldwide instantly.",
        "target_language": "Spanish",  # Default to Spanish
        "current_translation": "",
        "translation_critique": ""
    }
)

# --- Tool Definition ---
def exit_translation_loop(tool_context: ToolContext):
    """Call this function ONLY when the translation critique indicates no further improvements are needed."""
    print(f"  [Tool Call] exit_translation_loop triggered by {tool_context.agent_name}")
    tool_context.actions.escalate = True
    return {}

# --- Agent Definitions ---

# STEP 1: Initial Translator Agent
initial_translator_agent = LlmAgent(
    name="InitialTranslatorAgent",
    model=GEMINI_MODEL,
    include_contents='default',  # Use 'default' instead of 'all'
    instruction="""You are a professional translator. 

    CRITICAL INSTRUCTION: You must ALWAYS translate to Spanish. Do not translate to any other language unless explicitly instructed.
    
    When you receive English text:
    1. Translate it directly to Spanish
    2. Output ONLY the Spanish translation
    3. Do NOT add any explanations, quotes, or commentary
    4. Do NOT translate to French, German, or any other language
    
    Example:
    Input: "Hello world"
    Output: Hola mundo
    
    Remember: ALWAYS Spanish, ONLY the translation.""",
    description="Performs initial translation from English to Spanish.",
    output_key=STATE_CURRENT_TRANSLATION
)

# STEP 2a: Translation Critic Agent
translation_critic_agent = LlmAgent(
    name="TranslationCriticAgent",
    model=GEMINI_MODEL,
    include_contents='default',
    instruction=f"""You are a Spanish translation quality reviewer.

    Review the Spanish translation that was just produced.
    
    Evaluate for:
    1. Accuracy - Is the English meaning preserved in Spanish?
    2. Grammar - Is the Spanish grammatically correct?
    3. Fluency - Does it sound natural in Spanish?

    IF there are issues:
    - Output specific corrections (e.g., "Change 'palabra' to 'término'")
    - Be concise and specific
    
    IF the Spanish translation is good:
    - Output EXACTLY: {COMPLETION_PHRASE}
    - Nothing else""",
    description="Reviews Spanish translation quality.",
    output_key=STATE_TRANSLATION_CRITIQUE
)

# STEP 2b: Translation Refiner Agent
translation_refiner_agent = LlmAgent(
    name="TranslationRefinerAgent",
    model=GEMINI_MODEL,
    include_contents='default',
    instruction=f"""You are a Spanish translation refiner.

    Review the critique provided.
    
    IF the critique says EXACTLY "{COMPLETION_PHRASE}":
    - Call the exit_translation_loop function
    - Do not output any text
    
    ELSE:
    - Apply the suggested corrections to improve the Spanish translation
    - Output ONLY the refined Spanish translation text
    - No explanations""",
    description="Refines Spanish translation based on critique or exits.",
    tools=[exit_translation_loop],
    output_key=STATE_CURRENT_TRANSLATION
)

# STEP 2: Translation Refinement Loop
translation_refinement_loop = LoopAgent(
    name="TranslationRefinementLoop",
    sub_agents=[
        translation_critic_agent,
        translation_refiner_agent,
    ],
    max_iterations=5
)

# STEP 3: Overall Translation Pipeline
root_agent = SequentialAgent(
    name="IterativeTranslationPipeline",
    sub_agents=[
        initial_translator_agent,
        translation_refinement_loop
    ],
    description="Translates English text to Spanish with iterative quality refinement."
)

# Make agent available for ADK discovery
__all__ = ["root_agent"]