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
        "source_text": "",
        "target_language": "Spanish",  # Default to Spanish
        "current_translation": "",
        "translation_critique": ""
    }
)


# --- Tool Definitions ---
def set_target_language(tool_context: ToolContext, language: str):
    """Sets the target language for translation."""
    print(f"  [Tool Call] Setting target language to: {language}")
    # Access state through tool_context.state, not tool_context.session.state
    tool_context.state["target_language"] = language
    return {"status": "success", "language_set": language}


def get_target_language(tool_context: ToolContext):
    """Gets the current target language."""
    # Access state through tool_context.state
    lang = tool_context.state.get("target_language", "Spanish")
    return {"current_language": lang}


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
    instruction="""You are a professional translator with language detection and measurement localizing capabilities.

    Your task is a two-step process:
    1.  **Detect Language:** Check the user's last most sent message for a language directive (e.g., "to French", "in German").
        - If a language is specified, call `set_target_language` with that language.
        - If no language is specified, call `get_target_language` to use the currently set language.

    2.  **Translate and Localize:** After determining the language, translate the user's text. You MUST also convert formats and units for a non-US audience.
        * **Dates:** Convert `MM/DD/YYYY` to `DD/MM/YYYY`.
        * **Measurements:** Convert imperial units to metric.
            * miles -> kilometers (km)
            * pounds (lbs) -> kilograms (kg)
            * feet -> meters (m)
        * **Temperature:** Convert Fahrenheit (°F) to Celsius (°C).

    3.  **Output:** Output ONLY the final, translated, and localized text. Do not include original values, explanations, or commentary.

    Examples:
    User: "Hello" → Check language, translate to current/default, output: "Hola"
    User: "Hello in French" → Set to French, output: "Bonjour"
    User: "Weather is nice to German" → Set to German, output: "Das Wetter ist schön",
    description="Detects target language and performs initial translation.",
    tools=[set_target_language, get_target_language],
    output_key=STATE_CURRENT_TRANSLATION

    **Example Workflow:**
    User: "The package weighs 10 pounds and must be delivered 50 miles by 12/31/2024 to French"
    You:
    1) Call set_target_language("French")
    2) Output: "Le colis pèse 4.54 kg et doit être livré à 80.47 km d'ici le 31/12/2024."
"""
)
# STEP 2a: Translation Critic Agent
translation_critic_agent = LlmAgent(
    name="TranslationCriticAgent",
    model=GEMINI_MODEL,
    include_contents='default',
    instruction=f"""You are a multilingual translation quality reviewer.

    Look at the current translation that was just produced.
    Based on the conversation context, determine what language it's supposed to be in.

    Evaluate the translation for:
    1. Grammar - Is it grammatically correct in that language?
    2. Fluency - Does it sound natural in that language?

    IF there are issues:
    - Be concise and specific
    - Go into detail what the issue is.
    - Explain what grammatical or fluency errors were broken and what they rules are.

    IF the translation looks good:
    - Output EXACTLY: {COMPLETION_PHRASE}
    - Nothing else""",
    description="Reviews translation quality.",
    output_key=STATE_TRANSLATION_CRITIQUE
)

# STEP 2b: Translation Refiner Agent
translation_refiner_agent = LlmAgent(
    name="TranslationRefinerAgent",
    model=GEMINI_MODEL,
    include_contents='default',
    instruction=f"""You are a multilingual translation refiner.

    Look at the critique that was just provided.

    IF the critique says EXACTLY "{COMPLETION_PHRASE}":
    - Call exit_translation_loop function
    - Do not output any text

    ELSE:
    - If there are grammatical or fluency issues mentioned in the critique use the explanation to fix them.
    - Apply the other suggested corrections
    - Output ONLY the improved translation
    - Keep the same target language as the previous translation
    - No explanations, just the refined translation text""",
    description="Refines translation based on critique.",
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