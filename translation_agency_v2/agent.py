# !/usr/bin/env python3
"""
Content-Agnostic Translation Workflow
====================================
Core agent workflow that dynamically adapts to any website structure.
- Automatically detects content groups and creates context-aware agents
- Generates specialized instructions based on content type and context
- Dynamically scales to any number of groups and content types
- Processes batches in optimal parallel groups for efficiency


FEATURES:
- Content-aware agent instructions (navigation, headers, content, buttons)
- Dynamic brand term and glossary integration
- Adaptive parallel grouping based on content relationships
- Fully content-agnostic and scalable
"""
import os
from typing import Dict, List
from pydantic import BaseModel, Field
from .batch_processor import ContentBatchProcessor
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent

# Load environment variables
try:
    from dotenv import load_dotenv

    if not load_dotenv():
        load_dotenv("../.env")
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment variables only")

# Configure Google AI API
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"

# Verify API key is set
if not os.environ.get("GOOGLE_API_KEY"):
    raise ValueError("GOOGLE_API_KEY environment variable is required")

# Constants
GEMINI_MODEL = "gemini-2.0-flash"
APP_NAME = "content_agnostic_translation_app"


# Define Pydantic schema for structured translation output
class TranslationItem(BaseModel):
    value: str = Field(description="The translated text value")


class TranslationOutput(BaseModel):
    items: List[TranslationItem] = Field(description="List of translated values in order")


def create_content_agnostic_workflow(content_file_path: str = "website_content.json"):
    """
    Create a fully content-agnostic translation workflow that adapts to any website structure.

    Args:
        content_file_path: Path to the website content JSON file

    Returns:
        tuple: (root_agent, batches, processor) - The main agent and supporting data
    """
    # Create batch processor and get batches
    processor = ContentBatchProcessor(content_file_path)
    processor.load_content()
    batches = processor.create_batches()

    num_batches = len(batches)
    agents_per_group = 3  # Process 3 batches in parallel per group to manage API limits
    num_parallel_groups = (num_batches + agents_per_group - 1) // agents_per_group  # Ceiling division

    print(f"🔧 Creating content-agnostic workflow for {num_batches} content groups")

    # Dynamically create content-aware agents for all batches
    all_agents = []
    brand_terms = processor.get_brand_terms()
    glossary_terms = processor.get_glossary_terms()

    for i, batch in enumerate(batches):
        # Create context-aware instruction based on batch content
        def create_batch_instruction(batch_info, batch_idx):
            return lambda ctx: f"""You are a professional translator specializing in {batch_info.group_name.lower()}.


       CONTEXT: You are translating {batch_info.group_description} content for a wild life website.
       GROUP: {batch_info.group_name} ({batch_info.total_items} items)


       Source content to translate:
       {ctx.state.get(f'source_text_{batch_idx + 1}', '')}




       CRITICAL RULES:
       1. Keep brand terms unchanged: {', '.join(brand_terms)}
      3. Extract ONLY the text after format markers [BUTTON], [HEADER], [CONTENT] - DO NOT include the markers
       4. Translate EVERY SINGLE item in the input - do not skip any
       6. Maintain the tone appropriate for {batch_info.group_name.lower()} content
       7. Return JSON with ALL translated values in order


       CONTENT TYPE GUIDANCE:
       - Navigation items: Keep concise and clear
       - Headers: Maintain impact and clarity
       - Content: Preserve meaning and engagement
       - Buttons: Use action-oriented language


       Example input: "[BUTTON] The Vault\\n[BUTTON] My Hands\\n[CONTENT] Welcome"
       Example output: {{"items": [{{"value": "O Vault"}}, {{"value": "Minhas Mãos"}}, {{"value": "Bem-vindo"}}]}}"""

        agent = LlmAgent(
            name=f"BatchTranslator_{batch.group_id}",
            model=GEMINI_MODEL,
            instruction=create_batch_instruction(batch, i),
            output_schema=TranslationOutput,
            output_key=f"translation_{i + 1}",
            description=f"Translates {batch.group_name} content ({batch.total_items} items)"
        )
        all_agents.append(agent)
        print(f"   ✅ Created agent for {batch.group_name} ({batch.total_items} items)")

    # Group agents into parallel groups (3 agents per group)
    parallel_groups = []
    for group_idx in range(num_parallel_groups):
        start_idx = group_idx * agents_per_group
        end_idx = min(start_idx + agents_per_group, num_batches)
        group_agents = all_agents[start_idx:end_idx]

        # Create descriptive group name based on content
        group_batch_names = [batches[start_idx + i].group_name for i in range(len(group_agents))]
        group_description = f"Translates {', '.join(group_batch_names)} in parallel"

        parallel_group = ParallelAgent(
            name=f"ParallelGroup{group_idx + 1}",
            sub_agents=group_agents,
            description=group_description
        )
        parallel_groups.append(parallel_group)
        print(f"   🔄 Group {group_idx + 1}: {', '.join(group_batch_names)} ({len(group_agents)} agents)")

    # Create the main parallel translator (Step 1)
    staged_parallel_translator = SequentialAgent(
        name="DynamicStagedParallelTranslator",
        sub_agents=parallel_groups,
        description=f"Executes {num_batches} batch translations in {num_parallel_groups} staged parallel groups"
    )

    # STEP 2: DYNAMIC BATCH REVIEW AGENT
    def dynamic_batch_review_instruction(ctx):
        # Get character limits from state
        char_limits_data = {}
        for i in range(num_batches):
            char_limits_data[f"translation_{i + 1}"] = ctx.state.get(f'char_limits_{i + 1}', '')

        # Dynamically build review for all available translations
        translation_keys = [f"translation_{i + 1}" for i in range(num_batches)]
        translations_text = chr(10).join([
            f"- Group {i + 1}: {ctx.state.get(f'translation_{i + 1}', '[Not translated]')}"
            for i in range(num_batches)
        ])

        return f"""You are a professional translation reviewer analyzing {num_batches} batch translations.


REVIEW ALL TRANSLATIONS:
{translations_text}


CHARACTER LIMITS TO CHECK:
{chr(10).join([f"Group {i + 1}: {char_limits_data[f'translation_{i + 1}']}" for i in range(num_batches)])}


TARGET LANGUAGE: {ctx.state.get('target_language', 'Portuguese')}
BRAND TERMS: {', '.join(brand_terms)}


REVIEW CRITERIA:
1. CHARACTER LIMITS: Check if ANY translation exceeds its character limit - if so, flag for revision
2. Accuracy and fluency in target language
3. Brand terms remain unchanged: {', '.join(brand_terms)}
4. Format markers [BUTTON], [HEADER], [CONTENT] are removed from translations


**CRITICAL**: If any translation is too long, immediately flag that group for revision.


**Output Format:**
REVIEW_STATUS: NEEDS_REVISION or APPROVED
FEEDBACK:
- **Group X:** [specific feedback if issues found]


If all translations are good AND within character limits, output: REVIEW_STATUS: APPROVED"""

    dynamic_batch_reviewer = LlmAgent(
        name="DynamicBatchReviewer",
        model=GEMINI_MODEL,
        instruction=dynamic_batch_review_instruction,
        output_key="batch_review_results",
        description=f"Reviews all {num_batches} parallel translations and flags issues"
    )

    # STEP 3: DYNAMIC BATCH REGENERATION AGENT
    def dynamic_batch_regeneration_instruction(ctx):
        return f"""You are a translation regeneration specialist. Based on review feedback, regenerate ONLY the flagged batches.


REVIEW RESULTS: {ctx.state.get('batch_review_results', 'No review available')}
TARGET LANGUAGE: {ctx.state.get('target_language', 'Portuguese')}
GLOSSARY TERMS: {ctx.state.get('glossary_terms', {})}
BRAND TERMS: {ctx.state.get('brand_terms', [])}


INSTRUCTIONS:
1. Parse the review results to identify flagged batches
2. For each flagged batch, regenerate the translation addressing the specific feedback
3. Only regenerate batches that were flagged for revision
4. Keep brand terms unchanged: {', '.join(brand_terms)}
5. Remove format markers [BUTTON], [HEADER], [CONTENT] from output


**Output Format:**
```json
{{
 "batches": [
   {{
     "group_id": 1,
     "items": [
       {{"value": "translated text 1"}},
       {{"value": "translated text 2"}}
     ]
   }}
 ]
}}
```


If no batches were flagged, output: NO_REGENERATION_NEEDED"""

    dynamic_batch_regeneration_agent = LlmAgent(
        name="DynamicBatchRegenerationAgent",
        model=GEMINI_MODEL,
        instruction=dynamic_batch_regeneration_instruction,
        output_key="regenerated_translations",
        description="Regenerates flagged batches with specific feedback"
    )

    # STEP 4: DYNAMIC FINAL REFINEMENT AGENT
    def dynamic_final_refinement_instruction(ctx):
        # Dynamically build final refinement for all translations
        original_translations = chr(10).join([
            f"- group_{i + 1}: {ctx.state.get(f'translation_{i + 1}', '[Not available]')}"
            for i in range(num_batches)
        ])

        return f"""You are the final translation refinement specialist. Produce the final, polished translations.


ORIGINAL TRANSLATIONS:
{original_translations}


REGENERATED TRANSLATIONS: {ctx.state.get('regenerated_translations', 'None')}
REVIEW FEEDBACK: {ctx.state.get('batch_review_results', 'No feedback')}


TASK:
1. For each group, use the regenerated version if available, otherwise use the original
2. Apply final polish and consistency checks across all {num_batches} groups
3. Ensure all translations meet professional standards
4. Maintain consistency in terminology and tone


**Output:** Provide the final translations in this format:
FINAL_TRANSLATIONS:
- group_1: [final translation items]
- group_2: [final translation items]
{chr(10).join([f"- group_{i + 1}: [final translation items]" for i in range(2, num_batches)])}"""

    dynamic_final_refinement_agent = LlmAgent(
        name="DynamicFinalRefinementAgent",
        model=GEMINI_MODEL,
        instruction=dynamic_final_refinement_instruction,
        output_key="final_translations",
        description=f"Produces final polished translations for all {num_batches} groups"
    )

    # STEP 5: COMPLETE CONTENT-AGNOSTIC WORKFLOW
    root_agent = SequentialAgent(
        name="ContentAgnosticTranslationWorkflow",
        sub_agents=[
            staged_parallel_translator,  # Step 1: Translate all batches in staged parallel groups
            dynamic_batch_reviewer,  # Step 2: Review all translations
            dynamic_batch_regeneration_agent,  # Step 3: Regenerate flagged batches
            dynamic_final_refinement_agent  # Step 4: Final refinement and polish
        ],
        description=f"Content-agnostic translation workflow: {num_batches} groups → staged parallel → review → regeneration → refinement"
    )

    print(f"🎯 Content-agnostic workflow created: {num_batches} groups → {num_parallel_groups} parallel stages")
    print("✅ Content-Agnostic Translation Workflow Ready!")
    print(f"   📊 {num_batches} content groups detected")
    print(f"   🔄 {num_parallel_groups} parallel stages created")
    print(f"   🔍 Review and refinement pipeline included")
    print(f"   🎯 Fully dynamic and content-agnostic")

    return root_agent, batches, processor


# Create the main workflow (can be imported by test scripts)
root_agent, content_batches, content_processor = create_content_agnostic_workflow()

# Export key components
__all__ = [
    "root_agent",
    "content_batches",
    "content_processor",
    "create_content_agnostic_workflow",
    "TranslationItem",
    "TranslationOutput",
    "APP_NAME",
    "GEMINI_MODEL"
]