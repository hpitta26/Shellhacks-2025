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
def set_target_language(tool_context: ToolContext, language: str):
    """Sets the target language for translation."""
    print(f"  [Tool Call] Setting target language to: {language}")
    tool_context.session.state["target_language"] = language
    return {"status": "success", "language_set": language}

def exit_translation_loop(tool_context: ToolContext):
    """Call this function ONLY when the translation critique indicates no further improvements are needed."""
    print(f"  [Tool Call] exit_translation_loop triggered by {tool_context.agent_name}")
    tool_context.actions.escalate = True
    return {}

# --- Agent Definitions ---

# STEP 1: Initial Translator Agent with language detection
initial_translator_agent = LlmAgent(
    name="InitialTranslatorAgent",
    model=GEMINI_MODEL,
    include_contents='default',
    instruction="""You are a professional translator and localizer with language detection capabilities.

    Your task:
    1.  **Detect Language:** First, check if the user specified a target language in their message.
        - Look for phrases like "to French", "in German", "to Japanese", etc.
        - If a language is specified, call the `set_target_language` tool with that language.
        - If no language is specified, call `set_target_language` with "Spanish" as the default.

    2.  **Translate and Localize:** After setting the language, translate the English text to the target language. You MUST also adjust formats and units to be culturally and regionally appropriate.
        * **Dates:** Convert `MM/DD/YYYY` to `DD/MM/YYYY`.
        * **Measurements:** Convert imperial units to metric.
            * miles -> kilometers (km)
            * pounds (lbs) -> kilograms (kg)
            * feet -> meters (m)
        * **Temperature:** Convert Fahrenheit (°F) to Celsius (°C).

    3.  **Output:** Output ONLY the final, translated, and localized text. Do not include original values, explanations, or commentary.

    Example Workflow 1 (Language specified):
    User: "The package weighs 10 pounds and must be delivered 50 miles by 12/31/2024 to French"
    You:
    1) Call set_target_language("French")
    2) Output: "Le colis pèse 4.54 kg et doit être livré à 80.47 km d'ici le 31/12/2024."

    Example Workflow 2 (No language specified):
    User: "The package weighs 10 pounds and must be delivered 50 miles by 12/31/2024."
    You:
    1) Call set_target_language("Spanish")
    2) Output: "El paquete pesa 4.54 kg y debe ser entregado a 80.47 km para el 31/12/2024."
    """,
    description="Detects target language, then performs translation and localization of units and formats.",
    tools=[set_target_language],
    output_key=STATE_CURRENT_TRANSLATION
)

# STEP 2a: Translation Critic Agent (now language-aware)
translation_critic_agent = LlmAgent(
    name="TranslationCriticAgent",
    model=GEMINI_MODEL,
    include_contents='default',
    instruction=f"""You are a multilingual translation quality reviewer.

    Review the translation that was just produced. The target language was set in the previous step.
    
    Evaluate for:
    1. Accuracy - Is the English meaning preserved in Spanish?
    2. Grammar - Is the Spanish grammatically correct?
    3. Fluency - Does it sound natural in Spanish?
    4. Localization - Have dates (to DD/MM/YYYY) in applicable countries, measurements (miles to km, pounds to kg) in countries with metric system, and temperatures (Fahrenheit to Celsius) been correctly converted for a Spanish-speaking audience?

    IF there are issues:
    - Output specific corrections relevant to the target language
    - Output specific corrections relating to the conversion of measurements(e.g., "Change '160 km' to '160.93 km'" or "Date format should be DD/MM/YYYY")
    - Be concise and specific
    
    IF the translation is good and all conversions are good:
    - Output EXACTLY: {COMPLETION_PHRASE}
    - Nothing else""",
    description="Reviews translation quality for any language.",
    output_key=STATE_TRANSLATION_CRITIQUE
)

# STEP 2b: Translation Refiner Agent (language-aware)
translation_refiner_agent = LlmAgent(
    name="TranslationRefinerAgent",
    model=GEMINI_MODEL,
    include_contents='default',
    instruction=f"""You are a multilingual translation refiner.

    Review the critique provided.
    
    IF the critique says EXACTLY "{COMPLETION_PHRASE}":
    - Call the exit_translation_loop function
    - Do not output any text
    
    ELSE:
    - Apply the suggested corrections to improve the translation
    - Maintain the same target language that was used initially
    - Output ONLY the refined translation text
    - No explanations""",
    description="Refines translation based on critique or exits.",
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
    description="Translates English text to any language (default Spanish) with iterative quality refinement."
)

# Make agent available for ADK discovery
__all__ = ["root_agent"]