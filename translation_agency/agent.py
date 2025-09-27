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
        "source_text": "On 09/27/2025, the new regulations will take effect. All packages over 5 pounds must be shipped via a special carrier. The required storage temperature is 68 degrees Fahrenheit, and the maximum shipping distance is 100 miles.",
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

    CRITICAL INSTRUCTIONS:
    1.  **Translate to Spanish:** Your primary goal is to translate the meaning accurately.
    2.  **Localize and Convert:** You MUST also adjust formats and units for a non-US audience.
        * **Dates:** Convert `MM/DD/YYYY` to `DD/MM/YYYY`.
        * **Measurements:** Convert imperial units to metric.
            * miles -> kilometers (km)
            * pounds (lbs) -> kilograms (kg)
            * feet -> meters (m)
        * **Temperature:** Convert Fahrenheit (°F) to Celsius (°C).
    3.  **Output ONLY the final Spanish text.** Do not include original values, explanations, or commentary.

    Example:
    Input: "The package weighs 10 pounds and must be delivered 50 miles by 12/31/2024."
    Output: "El paquete pesa 4.54 kg y debe ser entregado a 80.47 km para el 31/12/2024."

    Remember: ALWAYS Spanish, ONLY the localized translation.""",
    description="Performs initial translation from English to Spanish, including localization of units and formats.",
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
    4. Localization - Have dates (to DD/MM/YYYY) in applicable countries, measurements (miles to km, pounds to kg) in countries with metric system, and temperatures (Fahrenheit to Celsius) been correctly converted for a Spanish-speaking audience?


    IF there are issues (translation or conversion errors):
    - Output specific corrections (e.g., "Change '160 km' to '160.93 km'" or "Date format should be DD/MM/YYYY")
    - Be concise and specific
    
    IF the Spanish translation and all conversions are good:
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