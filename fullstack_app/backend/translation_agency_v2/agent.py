""""
Idea --> Rebuild professional translation workflow using AI Agents

Flow:
1) Customer pushes content changes to CMS or DB --> it fires our localized workflow

2a) Case 1: small changes (single paragraph, sentence, button addition/change)
    - Build relevant context window (Section Group) --> give the translator enough context to make the small translation since its meaning is dependent on the surrounding text

2b) Case 2: large changes (multiple paragraphs, full sections, pages)
    - Separate into groups (by section) for parallized translation

** NOTE: Context curator agent would go here, but ignore for now **

3) BATCH TRANSLATION AGENTS
    - Translates all batches and follows relevant comments which have been cached in previous runs (glossary terms, brand terms, repeated keywords that need to be consistent throughout the app)
    - If unsure about something, writes Clarifying Questions to the STATE OBJECT (this mimics the human process of the translator asking clarifying questions to the customer)

4) BATCH REVIEWER AGENT
    - IF clarifying questions are present it will consult the context of the website (and write answers to the STATE OBJECT and recall translation for that batch)
    - ELSE it will review the translation and ensure that it abides by the rubric
        - IF the translation is good, it will output the translation and set the batch to complete
        - ELSE flag certain content for review and write comments to the STATE OBJECT that will be helpful for the translator, once full batch it done --> REVIEW AGAIN

5) SAVE FINAL TRANSLATION TO DATABASE
"""

import asyncio
import os
from google.adk.agents import LoopAgent, LlmAgent, BaseAgent, SequentialAgent, ParallelAgent
from google.genai import types
from google.adk.runners import InMemoryRunner
from google.adk.agents.invocation_context import InvocationContext
from google.adk.tools.tool_context import ToolContext
from typing import AsyncGenerator, Optional
from google.adk.events import Event, EventActions

from google.adk.sessions import InMemorySessionService, Session
from google.genai.types import Part, Content
import time

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Try loading from current directory first, then parent directory
    if not load_dotenv():
        load_dotenv("../.env")
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment variables only")

# Configure Google AI API (not Vertex AI)
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"

# Verify API key is set
if not os.environ.get("GOOGLE_API_KEY"):
    raise ValueError("GOOGLE_API_KEY environment variable is required. Please set it with: export GOOGLE_API_KEY='your_api_key' or add it to .env file")

# --- Constants ---
APP_NAME = "language_translator_app_v1"
USER_ID = "translator_user_01"
SESSION_ID_BASE = "translation_session"
GEMINI_MODEL = "gemini-2.0-flash"

# --- State Keys for Translation Workflow ---
# Input/Configuration
STATE_SOURCE_TEXT = "source_text"
STATE_TARGET_LANGUAGE = "target_language"
STATE_BATCH_SIZE = "batch_size"  # small or large changes

# Translation Process
STATE_CURRENT_TRANSLATION = "current_translation"
STATE_TRANSLATION_BATCHES = "translation_batches"  # List of translation batches
STATE_GLOSSARY_TERMS = "glossary_terms"  # Brand terms, repeated keywords
STATE_BRAND_TERMS = "brand_terms"

# Communication between agents (THE KEY PART!)
STATE_CLARIFYING_QUESTIONS = "clarifying_questions"  # Questions from translator to customer
STATE_CLARIFYING_ANSWERS = "clarifying_answers"  # Answers from reviewer/context
STATE_REVIEW_COMMENTS = "review_comments"  # Comments from reviewer to translator
STATE_BATCH_STATUS = "batch_status"  # complete, needs_review, has_questions
STATE_TRANSLATION_CRITIQUE = "translation_critique"  # Review/critique of translation

# Final Output
STATE_FINAL_TRANSLATION = "final_translation"
STATE_TRANSLATION_COMPLETE = "translation_complete"

# Define the exact phrase the Critic should use to signal completion
COMPLETION_PHRASE = "Translation is accurate and fluent."

# --- Callback Functions for State Monitoring ---
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext

def print_state_callback(callback_context: CallbackContext, stage: str):
    """Print current session state for debugging"""
    agent_name = callback_context.agent_name
    print(f"\n{'='*60}")
    print(f"🔍 STATE MONITOR - {stage} for {agent_name}")
    print(f"{'='*60}")
    
    state = callback_context.state.to_dict()
    print(f"📋 Current Session State ({len(state)} keys):")
    for key, value in state.items():
        if isinstance(value, str) and len(value) > 100:
            print(f"  {key}: {value[:100]}...")
        else:
            print(f"  {key}: {value}")
    print(f"{'='*60}\n")

def after_agent_state_callback(callback_context: CallbackContext) -> Optional[Content]:
    """Callback to monitor state after agent execution"""
    print_state_callback(callback_context, "AFTER AGENT EXECUTION")
    return None  # Don't modify the agent's output

def before_agent_state_callback(callback_context: CallbackContext) -> Optional[Content]:
    """Callback to monitor state before agent execution"""
    print_state_callback(callback_context, "BEFORE AGENT EXECUTION")
    return None  # Allow agent to proceed normally

# --- Instruction Providers for Dynamic State-Aware Instructions ---
def batch_translator_instruction_provider(context: ReadonlyContext) -> str:
    """Generate dynamic instructions for batch translator based on current state"""
    state = context.state
    source_text = state.get('source_text', '[No source text provided]')
    target_language = state.get('target_language', 'Spanish')
    glossary_terms = state.get('glossary_terms', {})
    brand_terms = state.get('brand_terms', [])
    
    instruction = f"""You are a professional batch translator.

CURRENT TASK:
- Source Text: "{source_text}"
- Target Language: {target_language}
- Glossary Terms: {glossary_terms}
- Brand Terms: {brand_terms}

WORKFLOW:
1. Translate the source text to {target_language}
2. Use glossary terms for consistency (e.g., {dict(list(glossary_terms.items())[:2]) if glossary_terms else 'none provided'})
3. Keep brand terms unchanged: {brand_terms if brand_terms else 'none provided'}
4. If you encounter unclear terms, note them but continue with your best translation

**Output:** Provide ONLY the translated text.
"""
    return instruction

def batch_reviewer_instruction_provider(context: ReadonlyContext) -> str:
    """Generate dynamic instructions for batch reviewer based on current state"""
    state = context.state
    current_translation = state.get('current_translation', '[No translation to review]')
    source_text = state.get('source_text', '[No source text]')
    target_language = state.get('target_language', 'Spanish')
    clarifying_questions = state.get('clarifying_questions', [])
    glossary_terms = state.get('glossary_terms', {})
    
    instruction = f"""You are a professional translation reviewer.

CURRENT REVIEW TASK:
- Source Text: "{source_text}"
- Current Translation: "{current_translation}"
- Target Language: {target_language}
- Clarifying Questions: {clarifying_questions if clarifying_questions else 'None'}
- Glossary Terms: {glossary_terms}

WORKFLOW:
1. Review the translation for grammar, fluency, and cultural appropriateness
2. Check consistency with glossary terms
3. Verify brand terms are preserved
4. If clarifying questions exist, provide answers
5. If translation is good, output: "{COMPLETION_PHRASE}"
6. If needs improvement, provide specific feedback

**Output:** Either "{COMPLETION_PHRASE}" or specific improvement feedback.
"""
    return instruction

def translation_refiner_instruction_provider(context: ReadonlyContext) -> str:
    """Generate dynamic instructions for translation refiner based on current state"""
    state = context.state
    current_translation = state.get('current_translation', '[No translation provided]')
    batch_status = state.get('batch_status', 'pending')
    review_comments = state.get('review_comments', [])
    clarifying_answers = state.get('clarifying_answers', [])
    
    instruction = f"""You are a translation refiner.

CURRENT REFINEMENT TASK:
- Current Translation: "{current_translation}"
- Batch Status: {batch_status}
- Review Comments: {review_comments if review_comments else 'None'}
- Clarifying Answers: {clarifying_answers if clarifying_answers else 'None'}

WORKFLOW:
1. If batch_status is "complete": Call exit_translation_loop() and output the current translation
2. If review comments exist: Apply the feedback to improve the translation
3. If clarifying answers exist: Use them to enhance the translation

**Output:** Provide ONLY the improved translated text.
"""
    return instruction

# Initialize session service
session_service = InMemorySessionService()


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


# --- Agent Definitions Following the Workflow ---

# STEP 3: BATCH TRANSLATION AGENT
# This agent translates content and writes clarifying questions to STATE if unsure
batch_translator_agent = LlmAgent(
    name="BatchTranslatorAgent",
    model=GEMINI_MODEL,
    instruction=batch_translator_instruction_provider,  # Dynamic instruction based on state
    description="Translates content using dynamic state-aware instructions",
    tools=[set_target_language, get_target_language],
    output_key=STATE_CURRENT_TRANSLATION,
    after_agent_callback=after_agent_state_callback
)
# STEP 4: BATCH REVIEWER AGENT
# This agent reviews translations and handles clarifying questions
batch_reviewer_agent = LlmAgent(
    name="BatchReviewerAgent", 
    model=GEMINI_MODEL,
    instruction=batch_reviewer_instruction_provider,  # Dynamic instruction based on state
    description="Reviews translations using dynamic state-aware instructions",
    output_key=STATE_TRANSLATION_CRITIQUE,
    after_agent_callback=after_agent_state_callback
)

# STEP 5: TRANSLATION REFINER AGENT  
# This agent refines translations based on review feedback
translation_refiner_agent = LlmAgent(
    name="TranslationRefinerAgent",
    model=GEMINI_MODEL,
    instruction=translation_refiner_instruction_provider,  # Dynamic instruction based on state
    description="Refines translations using dynamic state-aware instructions",
    tools=[exit_translation_loop],
    output_key=STATE_CURRENT_TRANSLATION,
    after_agent_callback=after_agent_state_callback
)

# STEP 6: PARALLEL BATCH TRANSLATOR AGENTS
# Create individual translator agents for each batch group with unique output keys

# Create individual translator agents with static instructions
batch_translator_group_1 = LlmAgent(
    name="BatchTranslator_group_1",
    model=GEMINI_MODEL,
    instruction=lambda ctx: f"""You are a professional translator specializing in navigation menu.

CURRENT TASK:
- Group: Navigation menu (group_1)
- Source Text: {ctx.state.get('source_text_group_1', '[No content provided]')}
- Target Language: {ctx.state.get('target_language', 'Portuguese')}
- Glossary Terms: {ctx.state.get('glossary_terms', {})}
- Brand Terms: {ctx.state.get('brand_terms', [])}

TRANSLATION GUIDELINES:
1. Translate the source text to {ctx.state.get('target_language', 'Portuguese')}
2. Maintain the original format markers (e.g., [BUTTON], [HEADER], [CONTENT])
3. Use glossary terms for consistency
4. Keep brand terms unchanged: {ctx.state.get('brand_terms', [])}
5. Consider the context of navigation menu when translating

**Output:** Provide ONLY the translated text, maintaining exact formatting.""",
    output_key="translation_group_1",
    description="Translates Navigation menu content in parallel"
)

batch_translator_group_2 = LlmAgent(
    name="BatchTranslator_group_2",
    model=GEMINI_MODEL,
    instruction=lambda ctx: f"""You are a professional translator specializing in hero section.

CURRENT TASK:
- Group: Hero section (group_2)
- Source Text: {ctx.state.get('source_text_group_2', '[No content provided]')}
- Target Language: {ctx.state.get('target_language', 'Portuguese')}
- Glossary Terms: {ctx.state.get('glossary_terms', {})}
- Brand Terms: {ctx.state.get('brand_terms', [])}

TRANSLATION GUIDELINES:
1. Translate the source text to {ctx.state.get('target_language', 'Portuguese')}
2. Maintain the original format markers (e.g., [BUTTON], [HEADER], [CONTENT])
3. Use glossary terms for consistency
4. Keep brand terms unchanged: {ctx.state.get('brand_terms', [])}
5. Consider the context of hero section when translating

**Output:** Provide ONLY the translated text, maintaining exact formatting.""",
    output_key="translation_group_2",
    description="Translates Hero section content in parallel"
)

batch_translator_group_3 = LlmAgent(
    name="BatchTranslator_group_3",
    model=GEMINI_MODEL,
    instruction=lambda ctx: f"""You are a professional translator specializing in testimonial carousel.

CURRENT TASK:
- Group: Testimonial carousel (group_3)
- Source Text: {ctx.state.get('source_text_group_3', '[No content provided]')}
- Target Language: {ctx.state.get('target_language', 'Portuguese')}
- Glossary Terms: {ctx.state.get('glossary_terms', {})}
- Brand Terms: {ctx.state.get('brand_terms', [])}

TRANSLATION GUIDELINES:
1. Translate the source text to {ctx.state.get('target_language', 'Portuguese')}
2. Maintain the original format markers (e.g., [BUTTON], [HEADER], [CONTENT])
3. Use glossary terms for consistency
4. Keep brand terms unchanged: {ctx.state.get('brand_terms', [])}
5. Consider the context of testimonial carousel when translating

**Output:** Provide ONLY the translated text, maintaining exact formatting.""",
    output_key="translation_group_3",
    description="Translates Testimonial carousel content in parallel"
)

# Create remaining agents (simplified for brevity)
batch_translator_group_4 = LlmAgent(
    name="BatchTranslator_group_4",
    model=GEMINI_MODEL,
    instruction=lambda ctx: f"""Translate the Octopi Store section content from {ctx.state.get('source_text_group_4', '')} to {ctx.state.get('target_language', 'Portuguese')}. Keep brand terms {ctx.state.get('brand_terms', [])} unchanged. Output only the translated text with original formatting.""",
    output_key="translation_group_4",
    description="Translates Octopi Store section content"
)

batch_translator_group_5 = LlmAgent(
    name="BatchTranslator_group_5",
    model=GEMINI_MODEL,
    instruction=lambda ctx: f"""Translate the Coaching marketplace section content from {ctx.state.get('source_text_group_5', '')} to {ctx.state.get('target_language', 'Portuguese')}. Keep brand terms {ctx.state.get('brand_terms', [])} unchanged. Output only the translated text with original formatting.""",
    output_key="translation_group_5",
    description="Translates Coaching marketplace section content"
)

batch_translator_group_6 = LlmAgent(
    name="BatchTranslator_group_6",
    model=GEMINI_MODEL,
    instruction=lambda ctx: f"""Translate the Vault explanation section content from {ctx.state.get('source_text_group_6', '')} to {ctx.state.get('target_language', 'Portuguese')}. Keep brand terms {ctx.state.get('brand_terms', [])} unchanged. Output only the translated text with original formatting.""",
    output_key="translation_group_6",
    description="Translates The Vault explanation section content"
)

batch_translator_group_7 = LlmAgent(
    name="BatchTranslator_group_7",
    model=GEMINI_MODEL,
    instruction=lambda ctx: f"""Translate the Product tutorials section content from {ctx.state.get('source_text_group_7', '')} to {ctx.state.get('target_language', 'Portuguese')}. Keep brand terms {ctx.state.get('brand_terms', [])} unchanged. Output only the translated text with original formatting.""",
    output_key="translation_group_7",
    description="Translates Product tutorials section content"
)

batch_translator_group_8 = LlmAgent(
    name="BatchTranslator_group_8",
    model=GEMINI_MODEL,
    instruction=lambda ctx: f"""Translate the Ask George section content from {ctx.state.get('source_text_group_8', '')} to {ctx.state.get('target_language', 'Portuguese')}. Keep brand terms {ctx.state.get('brand_terms', [])} unchanged. Output only the translated text with original formatting.""",
    output_key="translation_group_8",
    description="Translates Ask George section content"
)

batch_translator_group_9 = LlmAgent(
    name="BatchTranslator_group_9",
    model=GEMINI_MODEL,
    instruction=lambda ctx: f"""Translate the Footer section content from {ctx.state.get('source_text_group_9', '')} to {ctx.state.get('target_language', 'Portuguese')}. Keep brand terms {ctx.state.get('brand_terms', [])} unchanged. Output only the translated text with original formatting.""",
    output_key="translation_group_9",
    description="Translates Footer section content"
)

# Collect all translator agents
parallel_translator_agents = [
    batch_translator_group_1, batch_translator_group_2, batch_translator_group_3,
    batch_translator_group_4, batch_translator_group_5, batch_translator_group_6,
    batch_translator_group_7, batch_translator_group_8, batch_translator_group_9
]

# STEP 7: STAGED PARALLEL TRANSLATION EXECUTION
# Process batches in groups of 3 to avoid API rate limits and improve reliability

# Group 1: Navigation, Hero, Testimonials (3 agents)
parallel_group_1 = ParallelAgent(
    name="ParallelGroup1",
    sub_agents=[batch_translator_group_1, batch_translator_group_2, batch_translator_group_3],
    description="Translates Navigation, Hero, and Testimonials in parallel"
)

# Group 2: Store, Coaching, Vault (3 agents)  
parallel_group_2 = ParallelAgent(
    name="ParallelGroup2",
    sub_agents=[batch_translator_group_4, batch_translator_group_5, batch_translator_group_6],
    description="Translates Store, Coaching, and Vault sections in parallel"
)

# Group 3: Tutorials, Ask George, Footer (3 agents)
parallel_group_3 = ParallelAgent(
    name="ParallelGroup3", 
    sub_agents=[batch_translator_group_7, batch_translator_group_8, batch_translator_group_9],
    description="Translates Tutorials, Ask George, and Footer sections in parallel"
)

# Sequential execution of parallel groups
staged_parallel_translator = SequentialAgent(
    name="StagedParallelTranslator",
    sub_agents=[parallel_group_1, parallel_group_2, parallel_group_3],
    description="Executes batch translations in staged parallel groups for optimal performance"
)

# STEP 8: BATCH REVIEW AGENT
# Reviews all parallel translation results and flags issues
def batch_review_instruction_provider(ctx):
    return f"""You are a professional translation reviewer analyzing multiple batch translations.

REVIEW ALL TRANSLATIONS:
{chr(10).join([f"- {group_id}: {ctx.state.get(f'translation_{group_id}', '[Not translated]')}" for group_id in ['group_1', 'group_2', 'group_3', 'group_4', 'group_5', 'group_6', 'group_7', 'group_8', 'group_9']])}

TARGET LANGUAGE: {ctx.state.get('target_language', 'Portuguese')}
GLOSSARY TERMS: {ctx.state.get('glossary_terms', {})}
BRAND TERMS: {ctx.state.get('brand_terms', [])}

REVIEW CRITERIA:
1. Accuracy and fluency
2. Consistency with glossary terms
3. Brand terms remain unchanged
4. Format markers preserved
5. Contextual appropriateness for each section

**Output Format:**
REVIEW_STATUS: [APPROVED/NEEDS_REVISION]
FLAGGED_BATCHES: [list of group_ids that need revision, e.g., group_1,group_3]
COMMENTS:
- group_1: [specific feedback if flagged]
- group_3: [specific feedback if flagged]

If all translations are good, output: REVIEW_STATUS: APPROVED"""

batch_review_agent = LlmAgent(
    name="ParallelBatchReviewer",
    model=GEMINI_MODEL,
    instruction=batch_review_instruction_provider,
    output_key="batch_review_results",
    description="Reviews all parallel translations and flags issues"
)

# STEP 9: BATCH REGENERATION AGENT
# Regenerates flagged batches with specific feedback
def batch_regeneration_instruction_provider(ctx):
    return f"""You are a translation regeneration specialist. Based on review feedback, regenerate ONLY the flagged batches.

REVIEW RESULTS: {ctx.state.get('batch_review_results', 'No review available')}
TARGET LANGUAGE: {ctx.state.get('target_language', 'Portuguese')}
GLOSSARY TERMS: {ctx.state.get('glossary_terms', {})}
BRAND TERMS: {ctx.state.get('brand_terms', [])}

INSTRUCTIONS:
1. Parse the review results to identify flagged batches
2. For each flagged batch, regenerate the translation addressing the specific feedback
3. Only regenerate batches that were flagged for revision

**Output Format:**
REGENERATED_TRANSLATIONS:
- group_X: [improved translation]
- group_Y: [improved translation]

If no batches were flagged, output: NO_REGENERATION_NEEDED"""

batch_regeneration_agent = LlmAgent(
    name="BatchRegenerationAgent", 
    model=GEMINI_MODEL,
    instruction=batch_regeneration_instruction_provider,
    output_key="regenerated_translations",
    description="Regenerates flagged batches with specific feedback"
)

# STEP 10: FINAL REFINEMENT AGENT
# Produces final polished translations incorporating all feedback
def final_refinement_instruction_provider(ctx):
    return f"""You are the final translation refinement specialist. Produce the final, polished translations.

ORIGINAL TRANSLATIONS:
{chr(10).join([f"- {group_id}: {ctx.state.get(f'translation_{group_id}', '[Not available]')}" for group_id in ['group_1', 'group_2', 'group_3', 'group_4', 'group_5', 'group_6', 'group_7', 'group_8', 'group_9']])}

REGENERATED TRANSLATIONS: {ctx.state.get('regenerated_translations', 'None')}
REVIEW FEEDBACK: {ctx.state.get('batch_review_results', 'No feedback')}

TASK:
1. For each group, use the regenerated version if available, otherwise use the original
2. Apply final polish and consistency checks
3. Ensure all translations meet professional standards

**Output:** Provide the final translations in this format:
FINAL_TRANSLATIONS:
- group_1: [final translation]
- group_2: [final translation]
- group_3: [final translation]
- group_4: [final translation]
- group_5: [final translation]
- group_6: [final translation]
- group_7: [final translation]
- group_8: [final translation]
- group_9: [final translation]"""

final_refinement_agent = LlmAgent(
    name="FinalRefinementAgent",
    model=GEMINI_MODEL,
    instruction=final_refinement_instruction_provider,
    output_key="final_translations",
    description="Produces final polished translations incorporating all feedback"
)

# STEP 11: COMPLETE STAGED PARALLEL TRANSLATION WORKFLOW
# Orchestrates the entire staged parallel translation pipeline
root_agent = SequentialAgent(
    name="StagedParallelTranslationWorkflow",
    sub_agents=[
        staged_parallel_translator,  # Step 1: Translate all batches in staged parallel groups
        batch_review_agent,          # Step 2: Review all translations
        batch_regeneration_agent,    # Step 3: Regenerate flagged batches
        final_refinement_agent       # Step 4: Final refinement and polish
    ],
    description="Professional staged parallel translation workflow: staged concurrent translation → review → regeneration → refinement",
    before_agent_callback=before_agent_state_callback,  # Monitor state before each agent
    after_agent_callback=after_agent_state_callback     # Monitor state after each agent
)

# Make agent available for ADK discovery
__all__ = ["root_agent"]