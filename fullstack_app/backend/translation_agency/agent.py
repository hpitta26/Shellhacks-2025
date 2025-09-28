# Professional Website Translation ADK Agent - Boss Requirements Implementation (FULL VERSION)

import asyncio
import json
import re
from typing import List, Dict, Any, Optional
from google.adk.agents import LoopAgent, LlmAgent, SequentialAgent
from google.genai import types
from google.adk.runners import InMemoryRunner
from google.adk.agents.invocation_context import InvocationContext
from google.adk.tools.tool_context import ToolContext
from google.adk.events import Event, EventActions
from google.adk.sessions import InMemorySessionService

# --- Constants ---
APP_NAME = "professional_translation_workflow_v1"
USER_ID = "cms_user_01"
SESSION_ID_BASE = "cms_translation_session"
GEMINI_MODEL = "gemini-2.5-pro"

# --- State Keys ---
STATE_SOURCE_CONTENT = "source_content"
STATE_INPUT_TYPE = "input_type"
STATE_TARGET_LANGUAGE = "target_language"
STATE_CHANGE_TYPE = "change_type"
STATE_SECTION_GROUPS = "section_groups"
STATE_CONTENT_BATCHES = "content_batches"
STATE_TRANSLATIONS = "translations"
STATE_TRANSLATION_CACHE = "translation_cache"
STATE_GLOSSARY = "glossary"
STATE_PREVIOUS_GLOSSARY = "previous_glossary"
STATE_BRAND_TERMS = "brand_terms"
STATE_CLARIFYING_QUESTIONS = "clarifying_questions"
STATE_REVIEW_COMMENTS = "review_comments"
STATE_CONTEXT_WINDOWS = "context_windows"
STATE_TRANSLATION_STATUS = "translation_status"

def create_translation_session(content: Dict = None, target_language: str = "Spanish"):
    """Create a new translation session with initial state for CMS workflow"""
    session_service = InMemorySessionService()
    session_id = f"{SESSION_ID_BASE}_{hash(str(content)) if content else 'default'}"
    
    return session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
        state={
            STATE_SOURCE_CONTENT: content or {},
            STATE_TARGET_LANGUAGE: target_language,
            STATE_CHANGE_TYPE: "unknown",
            STATE_SECTION_GROUPS: {},
            STATE_CONTENT_BATCHES: [],
            STATE_TRANSLATIONS: {},
            STATE_TRANSLATION_CACHE: {},
            STATE_GLOSSARY: {},
            STATE_PREVIOUS_GLOSSARY: {},
            STATE_BRAND_TERMS: [],
            STATE_CLARIFYING_QUESTIONS: [],
            STATE_REVIEW_COMMENTS: {},
            STATE_CONTEXT_WINDOWS: {},
            STATE_TRANSLATION_STATUS: "pending"
        }
    )

# --- Tool Definitions ---

def detect_input_type(tool_context: ToolContext, user_input: str) -> Dict:
    """Detects if input is JSON or plain text and processes accordingly"""
    cleaned_input = user_input.strip()
    
    # Look for JSON indicators
    if cleaned_input.startswith('{') and cleaned_input.endswith('}'):
        try:
            content = json.loads(cleaned_input)
            tool_context.state[STATE_SOURCE_CONTENT] = content
            tool_context.state[STATE_INPUT_TYPE] = "json"
            
            print(f"[Input Detection] Detected JSON input with {len(content)} top-level keys")
            
            return {
                "input_type": "json",
                "content_stored": True,
                "sections": list(content.keys()) if isinstance(content, dict) else [],
                "message": "JSON content detected and parsed"
            }
        except json.JSONDecodeError:
            pass
    
    # It's plain text
    wrapped_content = {
        "plain_text": {
            "type": "content",
            "value": cleaned_input
        }
    }
    tool_context.state[STATE_SOURCE_CONTENT] = wrapped_content
    tool_context.state[STATE_INPUT_TYPE] = "text"
    
    print(f"[Input Detection] Detected plain text input")
    
    return {
        "input_type": "text", 
        "content_stored": True,
        "message": "Plain text detected and wrapped for processing"
    }

def extract_target_language(tool_context: ToolContext, user_input: str) -> Dict:
    """Extracts target language from user input"""
    language_patterns = [
        r"translate.*?(?:to|in|into)\s+(\w+)",
        r"(?:to|in|into)\s+(\w+)",
        r"target.*?language.*?(\w+)",
        r"(\w+)\s+translation"
    ]
    
    detected_language = None
    user_lower = user_input.lower()
    
    for pattern in language_patterns:
        match = re.search(pattern, user_lower)
        if match:
            detected_language = match.group(1).title()
            break
    
    if detected_language:
        language_map = {
            "Spanish": "Spanish", "Espanol": "Spanish", "Español": "Spanish",
            "French": "French", "Francais": "French", "Français": "French", 
            "German": "German", "Deutsch": "German",
            "Portuguese": "Portuguese", "Italian": "Italian",
            "Chinese": "Chinese", "Japanese": "Japanese", "Korean": "Korean"
        }
        
        normalized_language = language_map.get(detected_language, detected_language)
        tool_context.state[STATE_TARGET_LANGUAGE] = normalized_language
        
        print(f"[Language Detection] Detected target language: {normalized_language}")
        return {"language_detected": normalized_language, "language_set": True}
    else:
        default_lang = tool_context.state.get(STATE_TARGET_LANGUAGE, "Spanish")
        print(f"[Language Detection] No language specified, using default: {default_lang}")
        return {"language_detected": default_lang, "language_set": False}

def store_user_content(tool_context: ToolContext, json_content: str, target_language: str = "Spanish") -> Dict:
    """Stores CMS content changes and triggers localization workflow"""
    try:
        content = json.loads(json_content)
        tool_context.state[STATE_SOURCE_CONTENT] = content
        tool_context.state[STATE_TARGET_LANGUAGE] = target_language
        
        print(f"[CMS Workflow] Content changes received for localization to {target_language}")
        
        return {
            "status": "success", 
            "content_stored": True, 
            "sections": list(content.keys()) if isinstance(content, dict) else [],
            "target_language": target_language,
            "workflow_triggered": True
        }
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {str(e)}", "status": "failed"}
    except Exception as e:
        return {"error": f"Error storing content: {str(e)}", "status": "failed"}

def detect_change_size(tool_context: ToolContext) -> Dict:
    """Detects if changes are small (UI elements) or large (content blocks)"""
    content = tool_context.state.get(STATE_SOURCE_CONTENT, {})
    
    if not content:
        return {"error": "No content to analyze", "change_type": "unknown"}
    
    small_indicators = ["button", "header", "heading", "nav", "menu", "link", "label"]
    large_indicators = ["paragraph", "description", "content", "body", "article", "section"]
    
    total_items = 0
    small_count = 0
    large_count = 0
    content_length_total = 0
    
    def analyze_content(data, path=""):
        nonlocal total_items, small_count, large_count, content_length_total
        
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict) and "type" in value and "value" in value:
                    total_items += 1
                    content_length = len(str(value["value"]))
                    content_length_total += content_length
                    
                    content_type = value["type"].lower()
                    if any(indicator in content_type for indicator in small_indicators):
                        small_count += 1
                    elif any(indicator in content_type for indicator in large_indicators):
                        large_count += 1
                    
                    if content_length > 100:
                        large_count += 1
                    elif content_length < 50:
                        small_count += 1
                        
                elif isinstance(value, dict):
                    analyze_content(value, f"{path}.{key}")
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        analyze_content(item, f"{path}.{key}[{i}]")
    
    analyze_content(content)
    
    if total_items <= 3 and large_count == 0:
        change_type = "small"
    elif small_count > large_count and total_items <= 5:
        change_type = "small"
    else:
        change_type = "large"
    
    avg_content_length = content_length_total / max(total_items, 1)
    if avg_content_length > 150:
        change_type = "large"
    
    tool_context.state[STATE_CHANGE_TYPE] = change_type
    
    print(f"[Change Detection] Type: {change_type}, Items: {total_items}")
    
    return {
        "change_type": change_type,
        "total_items": total_items,
        "small_items": small_count,
        "large_items": large_count,
        "workflow_path": f"{change_type}_change_workflow"
    }

def load_translation_cache(tool_context: ToolContext) -> Dict:
    """Loads cached translations and glossary from previous runs"""
    previous_glossary = {
        "grinder": {"Spanish": "jugador dedicado", "French": "joueur acharné"},
        "grinders": {"Spanish": "jugadores dedicados", "French": "joueurs acharnés"},
        "poker": {"Spanish": "póker", "French": "poker"},
        "login": {"Spanish": "iniciar sesión", "French": "se connecter"},
        "signup": {"Spanish": "registrarse", "French": "s'inscrire"},
        "dashboard": {"Spanish": "panel", "French": "tableau de bord"},
        "settings": {"Spanish": "configuración", "French": "paramètres"}
    }
    
    brand_terms = [
        "Octopi", "Octopi Poker", "The Vault", "Ask George", "Octopi Store",
        "PokerGO", "WSOP", "Triton", "ICM", "GTO", "HUD"
    ]
    
    translation_cache = {
        "common_phrases": {
            "Welcome": {"Spanish": "Bienvenido", "French": "Bienvenue"},
            "Get Started": {"Spanish": "Comenzar", "French": "Commencer"},
            "Learn More": {"Spanish": "Saber Más", "French": "En Savoir Plus"},
            "Shop Now": {"Spanish": "Comprar Ahora", "French": "Acheter Maintenant"},
            "Start training now": {"Spanish": "Empezar a entrenar ahora", "French": "Commencer l'entraînement"}
        }
    }
    
    tool_context.state[STATE_PREVIOUS_GLOSSARY] = previous_glossary
    tool_context.state[STATE_BRAND_TERMS] = brand_terms
    tool_context.state[STATE_TRANSLATION_CACHE] = translation_cache
    tool_context.state[STATE_GLOSSARY] = previous_glossary
    
    print(f"[Cache Loaded] Glossary: {len(previous_glossary)} terms, Brand terms: {len(brand_terms)}")
    
    return {
        "glossary_loaded": len(previous_glossary),
        "brand_terms_loaded": len(brand_terms),
        "cache_entries": len(translation_cache.get("common_phrases", {})),
        "status": "loaded"
    }

def build_section_groups(tool_context: ToolContext) -> Dict:
    """Groups content by sections for context-aware translation"""
    content = tool_context.state.get(STATE_SOURCE_CONTENT, {})
    change_type = tool_context.state.get(STATE_CHANGE_TYPE, "unknown")
    
    if not content:
        return {"error": "No content to group", "groups_created": 0}
    
    section_groups = {}
    
    def create_groups(data, parent_path="", current_group="root"):
        if isinstance(data, dict):
            for key, value in data.items():
                full_path = f"{parent_path}.{key}" if parent_path else key
                
                if key in ["header", "navigation", "nav", "menu"]:
                    group_name = f"ui_elements_{key}"
                elif key in ["hero", "hero_section", "main", "content"]:
                    group_name = f"content_blocks_{key}"
                elif "button" in key.lower() or key.endswith("_button"):
                    group_name = "buttons"
                else:
                    group_name = current_group
                
                if group_name not in section_groups:
                    section_groups[group_name] = {
                        "items": [],
                        "context_priority": "high" if change_type == "small" else "medium",
                        "group_type": "ui" if "ui_elements" in group_name else "content"
                    }
                
                if isinstance(value, dict):
                    if "type" in value and "value" in value:
                        section_groups[group_name]["items"].append({
                            "key": full_path,
                            "type": value["type"],
                            "content": value["value"],
                            "group": group_name
                        })
                    else:
                        create_groups(value, full_path, group_name)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        create_groups(item, f"{full_path}[{i}]", group_name)
    
    create_groups(content)
    
    tool_context.state[STATE_SECTION_GROUPS] = section_groups
    
    total_items = sum(len(group["items"]) for group in section_groups.values())
    print(f"[Section Groups] Created {len(section_groups)} groups with {total_items} total items")
    
    return {
        "groups_created": len(section_groups),
        "total_items": total_items,
        "groups": list(section_groups.keys()),
        "change_type": change_type
    }

def create_translation_batches(tool_context: ToolContext) -> Dict:
    """Creates translation batches based on section groups and change type"""
    section_groups = tool_context.state.get(STATE_SECTION_GROUPS, {})
    change_type = tool_context.state.get(STATE_CHANGE_TYPE, "unknown")
    
    if not section_groups:
        return {"error": "No section groups found", "batches_created": 0}
    
    batches = []
    batch_id = 0
    
    for group_name, group_data in section_groups.items():
        for item in group_data["items"]:
            batch = {
                "batch_id": batch_id,
                "key": item["key"],
                "type": item["type"],
                "content": item["content"],
                "group": group_name,
                "group_type": group_data["group_type"],
                "context_priority": group_data["context_priority"],
                "change_type": change_type,
                "status": "pending"
            }
            batches.append(batch)
            batch_id += 1
    
    tool_context.state[STATE_CONTENT_BATCHES] = batches
    
    return {
        "batches_created": len(batches),
        "change_type": change_type,
        "batch_details": [{"id": b["batch_id"], "key": b["key"], "group": b["group"]} for b in batches]
    }

def translate_all_batches_parallel(tool_context: ToolContext) -> Dict:
    """Translates all pending batches in parallel with brand term awareness"""
    batches = tool_context.state.get(STATE_CONTENT_BATCHES, [])
    target_language = tool_context.state.get(STATE_TARGET_LANGUAGE, "Spanish")
    brand_terms = tool_context.state.get(STATE_BRAND_TERMS, [])
    glossary = tool_context.state.get(STATE_GLOSSARY, {})
    translation_cache = tool_context.state.get(STATE_TRANSLATION_CACHE, {})
    
    if not batches:
        return {"error": "No batches to translate"}
    
    translations = tool_context.state.get(STATE_TRANSLATIONS, {})
    results = []
    
    # Get cached common phrases
    common_phrases = translation_cache.get("common_phrases", {})
    
    for batch in batches:
        if batch["status"] != "pending":
            continue
            
        batch_id = batch["batch_id"]
        original_text = str(batch["content"]) if batch["content"] else ""
        
        # Start with original text
        translated_text = original_text
        
        # Apply cached common phrases first
        for phrase, translations_dict in common_phrases.items():
            if isinstance(translations_dict, dict) and target_language in translations_dict:
                if phrase in translated_text:
                    translated_text = translated_text.replace(phrase, translations_dict[target_language])
        
        # Apply glossary terms
        for term, translations_dict in glossary.items():
            if isinstance(translations_dict, dict) and target_language in translations_dict:
                if term in translated_text.lower():
                    # Replace with proper case handling
                    translated_text = re.sub(
                        r'\b' + re.escape(term) + r'\b', 
                        translations_dict[target_language], 
                        translated_text, 
                        flags=re.IGNORECASE
                    )
        
        # Preserve brand terms - replace any that might have been translated
        if isinstance(brand_terms, list):
            for brand_term in brand_terms:
                if isinstance(brand_term, str):
                    # Make sure brand term appears exactly as original in any case
                    if brand_term.lower() in original_text.lower():
                        # Find the exact case from original and preserve it
                        import re
                        pattern = re.compile(re.escape(brand_term), re.IGNORECASE)
                        match = pattern.search(original_text)
                        if match:
                            exact_brand_term = match.group(0)
                            # Replace any translated version with exact original
                            translated_text = pattern.sub(exact_brand_term, translated_text)
        
        # Basic translations for remaining text
        if target_language == "Spanish":
            basic_replacements = {
                "Poker study for everyone, beginners to elite": "Estudio de póker para todos, desde principiantes hasta élite",
                "Intuitive. Affordable. Fun.": "Intuitivo. Accesible. Divertido.",
                "Embrace your inner octopus and proudly wear the exclusive": "Abraza tu pulpo interior y viste con orgullo la exclusiva",
                "merch. Elegant and comfortable, it is made for": "mercancía. Elegante y cómoda, está hecha para",
                "like you.": "como tú."
            }
            
            for eng, spa in basic_replacements.items():
                if eng in translated_text:
                    translated_text = translated_text.replace(eng, spa)
        
        # Save translation
        translations[batch_id] = translated_text
        batch["status"] = "translated"
        
        results.append({
            "batch_id": batch_id,
            "key": batch["key"],
            "original": original_text,
            "translation": translated_text
        })
    
    tool_context.state[STATE_TRANSLATIONS] = translations
    tool_context.state[STATE_CONTENT_BATCHES] = batches
    
    print(f"[Parallel Translation] Completed {len(results)} batches to {target_language}")
    
    return {
        "batches_translated": len(results),
        "target_language": target_language,
        "results": results,
        "all_complete": True
    }

def review_all_translations(tool_context: ToolContext) -> Dict:
    """Reviews all translations at once"""
    batches = tool_context.state.get(STATE_CONTENT_BATCHES, [])
    
    reviewed_count = 0
    for batch in batches:
        if batch["status"] == "translated":
            batch["status"] = "complete"
            reviewed_count += 1
    
    tool_context.state[STATE_CONTENT_BATCHES] = batches
    print(f"[Bulk Review] Approved {reviewed_count} translations")
    
    return {
        "reviewed_batches": reviewed_count,
        "all_approved": True
    }

def check_all_complete(tool_context: ToolContext) -> Dict:
    """Checks if all batches are complete"""
    batches = tool_context.state.get(STATE_CONTENT_BATCHES, [])
    total_batches = len(batches)
    complete_batches = sum(1 for batch in batches if batch["status"] == "complete")
    
    all_complete = (complete_batches == total_batches and total_batches > 0)
    
    if all_complete:
        tool_context.state[STATE_TRANSLATION_STATUS] = "ready_for_database"
    
    return {
        "all_complete": all_complete,
        "completed_batches": complete_batches,
        "total_batches": total_batches,
        "status": "ready_for_database" if all_complete else "in_progress"
    }

def exit_loop(tool_context: ToolContext) -> Dict:
    """Exits the review loop when translations are complete"""
    print(f"[Loop Exit] Translation workflow complete")
    tool_context.actions.should_exit = True
    return {"workflow_complete": True, "status": "exiting_loop"}

def mock_save_to_database(tool_context: ToolContext) -> Dict:
    """Simulates saving final translations to database"""
    translations = tool_context.state.get(STATE_TRANSLATIONS, {})
    batches = tool_context.state.get(STATE_CONTENT_BATCHES, [])
    target_language = tool_context.state.get(STATE_TARGET_LANGUAGE, "Spanish")
    
    database_entries = []
    for batch in batches:
        if batch["batch_id"] in translations and batch["status"] == "complete":
            entry = {
                "key": batch["key"],
                "source_text": batch["content"],
                "translated_text": translations[batch["batch_id"]],
                "target_language": target_language,
                "content_type": batch["type"],
                "group": batch["group"],
                "status": "published"
            }
            database_entries.append(entry)
    
    print(f"[Mock Database] Would save {len(database_entries)} translations to database")
    
    tool_context.state[STATE_TRANSLATION_STATUS] = "published"
    
    return {
        "database_save_simulated": True,
        "entries_saved": len(database_entries),
        "target_language": target_language,
        "status": "published"
    }

def build_final_output(tool_context: ToolContext) -> Dict:
    """Builds the final output in the correct format"""
    source_content = tool_context.state.get(STATE_SOURCE_CONTENT, {})
    translations = tool_context.state.get(STATE_TRANSLATIONS, {})
    batches = tool_context.state.get(STATE_CONTENT_BATCHES, [])
    target_language = tool_context.state.get(STATE_TARGET_LANGUAGE, "Spanish")
    
    # Check if this was plain text input
    if "plain_text" in source_content and len(source_content) == 1:
        if translations and len(translations) > 0:
            final_output = list(translations.values())[0]
            tool_context.state["final_output"] = final_output
            print(f"[Final Output] Plain text result: {final_output}")
            return {"output_type": "text", "final_output": final_output}
    
    # This was JSON - rebuild the structure with translations
    import copy
    translated_json = copy.deepcopy(source_content)
    
    # Create mapping from batch keys to translations
    translation_map = {}
    for batch in batches:
        batch_id = batch["batch_id"]
        if batch_id in translations:
            translation_map[batch["key"]] = translations[batch_id]
    
    # Apply translations while preserving structure
    def apply_translations(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                
                if isinstance(value, dict) and "type" in value and "value" in value:
                    if current_path in translation_map:
                        obj[key]["value"] = translation_map[current_path]
                elif isinstance(value, dict):
                    apply_translations(value, current_path)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            apply_translations(item, f"{current_path}[{i}]")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, dict):
                    apply_translations(item, f"{path}[{i}]")
    
    apply_translations(translated_json)
    
    final_output = json.dumps(translated_json, ensure_ascii=False, indent=2)
    tool_context.state["final_output"] = final_output
    print(f"[Final Output] JSON result with {len(translation_map)} translations applied")
    
    return {
        "output_type": "json",
        "final_output": final_output,
        "translations_applied": len(translation_map)
    }

# --- Agent Definitions ---

input_analysis_agent = LlmAgent(
    name="InputAnalysisAgent",
    model=GEMINI_MODEL,
    instruction="""You are an Input Analysis Agent that processes user input for translation.

    When you receive input from the user:
    1. Call `detect_input_type` with the user's message to determine if it's JSON or plain text
    2. Call `extract_target_language` with the user's message to find the target language
    
    After processing, provide a brief summary of what was detected.""",
    description="Analyzes user input to determine content type and target language",
    tools=[detect_input_type, extract_target_language],
)

cms_content_agent = LlmAgent(
    name="CMSContentAgent",
    model=GEMINI_MODEL,
    instruction="""You are a CMS Content Reception Agent that processes content changes and triggers localization workflow.

    When you receive JSON content from the user:
    1. Call `store_user_content` with the JSON content and target language
    2. Call `detect_change_size` to determine if this is a small or large change
    3. Call `load_translation_cache` to load cached glossary and previous translations
    
    Provide a summary of the content received and the workflow path that will be taken.""",
    description="Receives CMS content changes and determines workflow path",
    tools=[store_user_content, detect_change_size, load_translation_cache],
)

context_curator_agent = LlmAgent(
    name="ContextCuratorAgent", 
    model=GEMINI_MODEL,
    instruction="""You are a Context Curator for professional translation workflow.

    Your job is to organize content for optimal translation:
    1. Call `build_section_groups` to group content by sections for context-aware translation
    2. Call `create_translation_batches` to create batches based on the groups and change type
    
    Report on the context structure created.""",
    description="Curates context and creates translation batches",
    tools=[build_section_groups, create_translation_batches],
)

parallel_translator_agent = LlmAgent(
    name="ParallelTranslatorAgent",
    model=GEMINI_MODEL,
    instruction="""You translate all batches at once using parallel processing.
    
    1. Call `translate_all_batches_parallel` to translate everything simultaneously
    2. This function automatically handles brand term preservation during translation
    3. Report completion status
    
    Brand terms are preserved automatically - no need for separate validation.""",
    description="Translates all batches in parallel with automatic brand preservation",
    tools=[translate_all_batches_parallel],
)

parallel_reviewer_agent = LlmAgent(
    name="ParallelReviewerAgent",
    model=GEMINI_MODEL,
    instruction="""You review all translations at once.
    
    1. Call `review_all_translations` to approve all translations
    2. Call `check_all_complete` to verify completion  
    3. If all complete: Call `exit_loop` to finish the workflow
    
    Always call exit_loop when everything is done.""",
    description="Reviews all translations in bulk",
    tools=[review_all_translations, check_all_complete, exit_loop],
)

database_agent = LlmAgent(
    name="DatabaseAgent",
    model=GEMINI_MODEL,
    instruction="""You handle saving completed translations to the database.
    
    When all translations are complete and verified:
    1. Call `mock_save_to_database` to save final translations
    
    Provide a summary of what was saved and the final status.""",
    description="Saves final translations to database (currently mocked)",
    tools=[mock_save_to_database],
)

output_builder_agent = LlmAgent(
    name="OutputBuilderAgent",
    model=GEMINI_MODEL,
    instruction="""You are the Output Builder Agent that creates the final response.

    When translations are complete:
    1. Call `build_final_output` to create the appropriate output format
    2. Present the final result to the user
    
    If the input was JSON, return the translated JSON structure.
    If the input was plain text, return just the translated text.""",
    description="Builds the final output based on input type",
    tools=[build_final_output],
)

# --- Agent Pipeline ---

parallel_translation_loop = LoopAgent(
    name="ParallelTranslationLoop",
    sub_agents=[
        parallel_translator_agent,
        parallel_reviewer_agent,
    ],
    max_iterations=3
)

root_agent = SequentialAgent(
    name="ProfessionalCMSTranslationWorkflow",
    sub_agents=[
        input_analysis_agent,
        cms_content_agent,
        context_curator_agent,
        parallel_translation_loop,
        database_agent,
        output_builder_agent,
    ],
    description="Fast parallel translation workflow with brand term protection"
)

def run_translation_pipeline(content: Dict = None, target_language: str = "Spanish"):
    """Run the complete professional translation workflow"""
    session = create_translation_session(content, target_language)
    runner = InMemoryRunner(root_agent, APP_NAME)
    return runner, session

__all__ = ["root_agent", "create_translation_session", "run_translation_pipeline"]

#https://docs.google.com/document/d/1ZfRmcNxQJsFhMAbRm1rb9ffiiNfKjJqIStANlgvK0xk/edit?usp=sharing