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

# --- Tool Definitions ---
def set_target_language(tool_context: ToolContext, language: str = "Spanish"):
    """Sets the target language for translation. Default is Spanish."""
    print(f"  [Tool Call] Setting target language to: {language}")
    tool_context.session.state["target_language"] = language
    return {"status": "success", "language_set": language}

def exit_translation_loop(tool_context: ToolContext):
    """Call this function ONLY when the translation critique indicates no further improvements are needed."""
    print(f"  [Tool Call] exit_translation_loop triggered by {tool_context.agent_name}")
    tool_context.actions.escalate = True
    return {}

# --- Agent Definitions ---

# STEP 0: Language Selector Agent (Optional - can be called to change language)
language_selector_agent = LlmAgent(
    name="LanguageSelectorAgent",
    model=GEMINI_MODEL,
    include_contents='none',
    instruction="""You are a language selection assistant.

    Current target language: {{session.state["target_language"]}}
    
    The user wants to translate English text to another language.
    Common languages include: Spanish, French, German, Italian, Portuguese, Chinese (Mandarin), 
    Japanese, Korean, Arabic, Russian, Hindi, Dutch, Swedish, Polish, Turkish.
    
    If no specific language is mentioned, use Spanish as the default.
    
    Call the set_target_language function with the appropriate language.
    
    OUTPUT: After setting the language, confirm by saying only:
    "Target language set to: [language]"
    """,
    description="Sets the target language for translation.",
    tools=[set_target_language]
)

# STEP 1: Initial Translator Agent
initial_translator_agent = LlmAgent(
    name="InitialTranslatorAgent",
    model=GEMINI_MODEL,
    include_contents='none',
    instruction="""You are a translation bot. Your ONLY job is to output translations.

    Source Text (English): {{session.state["source_text"]}}
    Target Language: {{session.state["target_language"]}}

    OUTPUT RULES:
    - Output ONLY the translation in the target language
    - Do NOT add ANY explanations, greetings, or commentary
    - Do NOT use quotation marks around the translation
    - Do NOT say "Here is the translation" or similar phrases
    - JUST output the translated text directly
    
    Example:
    If translating "Hello world" to Spanish, output only: Hola mundo
    
    Now translate the source text to the target language:""",
    description="Performs initial translation from English to the specified target language.",
    output_key=STATE_CURRENT_TRANSLATION
)

# STEP 2a: Translation Critic Agent
translation_critic_agent = LlmAgent(
    name="TranslationCriticAgent",
    model=GEMINI_MODEL,
    include_contents='none',
    instruction=f"""You are a translation validator bot. Analyze the translation quality.

    Original English: {{{{session.state["source_text"]}}}}
    Target Language: {{{{session.state["target_language"]}}}}
    Current Translation: {{{{session.state["current_translation"]}}}}

    EVALUATION RULES:
    Check for:
    1. Accuracy - meaning preserved?
    2. Grammar - correct in target language?
    3. Natural flow - sounds native?

    OUTPUT RULES:
    IF translation needs improvement:
    - Output ONLY specific corrections needed
    - Example: "Change 'X' to 'Y' for better fluency"
    - Do NOT add explanations or greetings
    
    IF translation is good enough:
    - Output EXACTLY: {COMPLETION_PHRASE}
    - Nothing else
    
    Your evaluation:""",
    description="Reviews translation quality and provides specific improvement suggestions or signals completion.",
    output_key=STATE_TRANSLATION_CRITIQUE
)

# STEP 2b: Translation Refiner Agent
translation_refiner_agent = LlmAgent(
    name="TranslationRefinerAgent",
    model=GEMINI_MODEL,
    include_contents='none',
    instruction=f"""You are a translation refiner bot.

    Original English: {{{{session.state["source_text"]}}}}
    Target Language: {{{{session.state["target_language"]}}}}
    Current Translation: {{{{session.state["current_translation"]}}}}
    Critique: {{{{session.state["translation_critique"]}}}}

    DECISION:
    IF critique is EXACTLY "{COMPLETION_PHRASE}":
    - Call exit_translation_loop function
    - Output nothing
    
    ELSE:
    - Apply the corrections mentioned in critique
    - Output ONLY the improved translation
    - No explanations, just the refined translation text
    
    Action:""",
    description="Refines translation based on critique, or exits loop if translation is complete.",
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

# STEP 3: Main Translation Pipeline (without language selector)
main_translation_pipeline = SequentialAgent(
    name="MainTranslationPipeline",
    sub_agents=[
        initial_translator_agent,
        translation_refinement_loop
    ],
    description="Main translation pipeline that translates and refines."
)

# Root agent with optional language selection
root_agent = SequentialAgent(
    name="IterativeTranslationPipeline",
    sub_agents=[
        # Uncomment the line below if you want language selection to run first every time:
        # language_selector_agent,
        main_translation_pipeline
    ],
    description="Translates English text to any language with iterative quality refinement using critic feedback."
)

# Alternative: You could also expose the language_selector_agent as a separate callable agent
# that can be invoked before the main translation pipeline when needed

# Make agent available for ADK discovery
__all__ = ["root_agent"]