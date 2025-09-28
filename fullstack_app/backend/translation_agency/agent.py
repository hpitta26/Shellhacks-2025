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
GEMINI_MODEL = "gemini-2.5-pro" # FIXED: Updated to correct model name

# --- State Keys ---
STATE_SOURCE_CONTENT = "source_content"
STATE_INPUT_TYPE = "input_type"  # FIXED: Added this state key
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

# Define completion and status phrases
TRANSLATION_COMPLETE = "All translations verified and complete"
NEEDS_CLARIFICATION = "Clarification needed"
NEEDS_REVISION = "Revision needed"

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
    
    # Analyze content to determine change size
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
                    
                    # Check content type
                    content_type = value["type"].lower()
                    if any(indicator in content_type for indicator in small_indicators):
                        small_count += 1
                    elif any(indicator in content_type for indicator in large_indicators):
                        large_count += 1
                    
                    # Check content length (long content = large change)
                    if content_length > 100:  # Long text
                        large_count += 1
                    elif content_length < 50:  # Short text
                        small_count += 1
                        
                elif isinstance(value, dict):
                    analyze_content(value, f"{path}.{key}")
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        analyze_content(item, f"{path}.{key}[{i}]")
    
    analyze_content(content)
    
    # Determine change type
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
    
    print(f"[Change Detection] Type: {change_type}, Items: {total_items}, Small: {small_count}, Large: {large_count}")
    
    return {
        "change_type": change_type,
        "total_items": total_items,
        "small_items": small_count,
        "large_items": large_count,
        "avg_content_length": avg_content_length,
        "workflow_path": f"{change_type}_change_workflow"
    }

def load_translation_cache(tool_context: ToolContext) -> Dict:
    """Loads cached translations and glossary from previous runs"""
    # Simulate loading from previous translation runs
    previous_glossary = {
        # Poker-specific terms
        "poker": {"Spanish": "póker", "French": "poker", "German": "Poker"},
        "grinder": {"Spanish": "jugador dedicado", "French": "joueur acharné", "German": "fleißiger Spieler"},
        "grinders": {"Spanish": "jugadores dedicados", "French": "joueurs acharnés", "German": "fleißige Spieler"},
        "rake": {"Spanish": "comisión", "French": "commission", "German": "Gebühr"},
        "tilt": {"Spanish": "tilt", "French": "tilt", "German": "Tilt"},
        "variance": {"Spanish": "varianza", "French": "variance", "German": "Varianz"},
        "bankroll": {"Spanish": "bankroll", "French": "bankroll", "German": "Bankroll"},
        "fold": {"Spanish": "retirarse", "French": "se coucher", "German": "folden"},
        "bluff": {"Spanish": "farol", "French": "bluff", "German": "Bluff"},
        "all-in": {"Spanish": "all-in", "French": "tapis", "German": "All-in"},
        
        # UI/Website terms
        "login": {"Spanish": "iniciar sesión", "French": "se connecter", "German": "anmelden"},
        "signup": {"Spanish": "registrarse", "French": "s'inscrire", "German": "registrieren"},
        "dashboard": {"Spanish": "panel", "French": "tableau de bord", "German": "Dashboard"},
        "settings": {"Spanish": "configuración", "French": "paramètres", "German": "Einstellungen"},
        "profile": {"Spanish": "perfil", "French": "profil", "German": "Profil"},
        
        # Training terms
        "trainer": {"Spanish": "entrenador", "French": "entraîneur", "German": "Trainer"},
        "simulation": {"Spanish": "simulación", "French": "simulation", "German": "Simulation"},
        "analysis": {"Spanish": "análisis", "French": "analyse", "German": "Analyse"},
        "review": {"Spanish": "revisión", "French": "révision", "German": "Überprüfung"}
    }
    
    # Brand terms that should NEVER be translated
    brand_terms = [
        "Octopi", "Octopi Poker", "The Vault", "Ask George", "Octopi Store",
        "PokerGO", "WSOP", "Triton", "ICM", "GTO", "HUD"
    ]
    
    # Simulated translation cache from previous runs
    translation_cache = {
        "common_phrases": {
            "Welcome": {"Spanish": "Bienvenido", "French": "Bienvenue", "German": "Willkommen"},
            "Get Started": {"Spanish": "Comenzar", "French": "Commencer", "German": "Loslegen"},
            "Learn More": {"Spanish": "Saber Más", "French": "En Savoir Plus", "German": "Mehr Erfahren"},
            "Contact Us": {"Spanish": "Contáctanos", "French": "Nous Contacter", "German": "Kontakt"},
            "About Us": {"Spanish": "Acerca de Nosotros", "French": "À Propos", "German": "Über Uns"}
        }
    }
    
    tool_context.state[STATE_PREVIOUS_GLOSSARY] = previous_glossary
    tool_context.state[STATE_BRAND_TERMS] = brand_terms
    tool_context.state[STATE_TRANSLATION_CACHE] = translation_cache
    tool_context.state[STATE_GLOSSARY] = previous_glossary  # Use as current glossary
    
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
                
                # Determine section group based on key patterns
                if key in ["header", "navigation", "nav", "menu"]:
                    group_name = f"ui_elements_{key}"
                elif key in ["hero", "hero_section", "main", "content"]:
                    group_name = f"content_blocks_{key}"
                elif key in ["footer", "sidebar", "aside"]:
                    group_name = f"secondary_{key}"
                elif "testimonial" in key.lower():
                    group_name = "testimonials"
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
                        # This is a translatable item
                        section_groups[group_name]["items"].append({
                            "key": full_path,
                            "type": value["type"],
                            "content": value["value"],
                            "group": group_name
                        })
                    else:
                        # Recurse deeper
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
            print(f"Created batch {batch_id}: {item['key']} (group: {group_name})")
            batch_id += 1
    
    tool_context.state[STATE_CONTENT_BATCHES] = batches
    
    return {
        "batches_created": len(batches),
        "change_type": change_type,
        "batch_details": [{"id": b["batch_id"], "key": b["key"], "group": b["group"]} for b in batches]
    }

def build_context_window(tool_context: ToolContext, batch_id: int) -> Dict:
    """Builds enhanced context window based on change type and section groups"""
    batches = tool_context.state.get(STATE_CONTENT_BATCHES, [])
    change_type = tool_context.state.get(STATE_CHANGE_TYPE, "unknown")
    
    target_batch = None
    for batch in batches:
        if batch["batch_id"] == batch_id:
            target_batch = batch
            break
    
    if not target_batch:
        available_ids = [b["batch_id"] for b in batches]
        return {"error": f"Batch {batch_id} not found. Available: {available_ids}"}
    
    # Enhanced context based on change type
    context = {
        "target": target_batch,
        "change_type": change_type,
        "group_context": [],
        "related_translations": {},
        "context_priority": target_batch.get("context_priority", "medium")
    }
    
    # For small changes, provide extensive context from the same group
    if change_type == "small":
        # Include all items from the same group for context
        target_group = target_batch["group"]
        for batch in batches:
            if batch["group"] == target_group and batch["batch_id"] != batch_id:
                context["group_context"].append({
                    "key": batch["key"],
                    "content": batch["content"],
                    "type": batch["type"],
                    "relationship": "same_group"
                })
    else:
        # For large changes, include related items and cross-group context
        target_group_type = target_batch["group_type"]
        for batch in batches:
            if batch["group_type"] == target_group_type and batch["batch_id"] != batch_id:
                context["group_context"].append({
                    "key": batch["key"],
                    "content": batch["content"],
                    "type": batch["type"],
                    "relationship": "same_type"
                })
    
    # Include existing translations for consistency
    translations = tool_context.state.get(STATE_TRANSLATIONS, {})
    for batch in batches:
        if batch["batch_id"] in translations:
            context["related_translations"][batch["key"]] = translations[batch["batch_id"]]
    
    # Store context window
    context_windows = tool_context.state.get(STATE_CONTEXT_WINDOWS, {})
    context_windows[batch_id] = context
    tool_context.state[STATE_CONTEXT_WINDOWS] = context_windows
    
    return {
        "context_built": True,
        "batch_id": batch_id,
        "change_type": change_type,
        "context_items": len(context["group_context"]),
        "related_translations": len(context["related_translations"])
    }

def check_brand_terms(tool_context: ToolContext, text: str) -> Dict:
    """Checks if text contains brand terms that should never be translated"""
    brand_terms = tool_context.state.get(STATE_BRAND_TERMS, [])
    
    found_terms = []
    text_lower = text.lower()
    
    for term in brand_terms:
        if term.lower() in text_lower:
            found_terms.append(term)
    
    return {
        "contains_brand_terms": len(found_terms) > 0,
        "found_terms": found_terms,
        "original_text": text
    }

def validate_translation(tool_context: ToolContext, batch_id: int, translated_text: str) -> Dict:
    """Validates that brand terms were preserved in translation for a specific batch"""
    # Get the original text for this batch
    batches = tool_context.state.get(STATE_CONTENT_BATCHES, [])
    original_text = None
    for batch in batches:
        if batch["batch_id"] == batch_id:
            original_text = batch["content"]
            break
    
    if not original_text:
        return {"error": f"Batch {batch_id} not found", "is_valid": False}
    
    brand_terms = tool_context.state.get(STATE_BRAND_TERMS, [])
    violations = []
    
    for term in brand_terms:
        if term.lower() in original_text.lower():
            # Brand term exists in original, check if it's preserved in translation
            if term.lower() not in translated_text.lower():
                violations.append({
                    "term": term,
                    "issue": "brand_term_missing",
                    "original": original_text,
                    "translation": translated_text
                })
    
    is_valid = len(violations) == 0
    
    return {
        "is_valid": is_valid,
        "violations": violations,
        "brand_terms_preserved": is_valid,
        "batch_id": batch_id
    }

def add_clarifying_question(tool_context: ToolContext, batch_id: int, question: str, question_type: str = "general") -> Dict:
    """Adds clarifying question - mimics human translator asking customer for clarification"""
    questions = tool_context.state.get(STATE_CLARIFYING_QUESTIONS, [])
    
    question_entry = {
        "batch_id": batch_id,
        "question": question,
        "question_type": question_type,  # "context", "brand", "technical", "tone"
        "status": "pending",
        "answer": None,
        "priority": "high" if question_type in ["brand", "technical"] else "medium"
    }
    
    questions.append(question_entry)
    tool_context.state[STATE_CLARIFYING_QUESTIONS] = questions
    
    print(f"[Clarifying Question] Batch {batch_id}: {question}")
    
    return {
        "question_added": True,
        "batch_id": batch_id,
        "question_type": question_type,
        "question": question,
        "total_pending": len([q for q in questions if q["status"] == "pending"])
    }

def answer_clarifying_question(tool_context: ToolContext, batch_id: int, answer: str) -> Dict:
    """Reviewer answers clarifying questions by consulting website context"""
    questions = tool_context.state.get(STATE_CLARIFYING_QUESTIONS, [])
    
    for question in questions:
        if question["batch_id"] == batch_id and question["status"] == "pending":
            question["answer"] = answer
            question["status"] = "answered"
            tool_context.state[STATE_CLARIFYING_QUESTIONS] = questions
            
            print(f"[Question Answered] Batch {batch_id}: {answer}")
            
            return {
                "question_answered": True,
                "batch_id": batch_id,
                "answer": answer,
                "remaining_pending": len([q for q in questions if q["status"] == "pending"])
            }
    
    return {"error": f"No pending question found for batch {batch_id}"}

def save_translation(tool_context: ToolContext, batch_id: int, translation: str) -> Dict:
    """Saves translation (validation should be done separately before calling this)"""
    
    # Get the original text for this batch
    batches = tool_context.state.get(STATE_CONTENT_BATCHES, [])
    original_text = None
    for batch in batches:
        if batch["batch_id"] == batch_id:
            original_text = batch["content"]
            break
    
    if not original_text:
        return {"error": f"Batch {batch_id} not found"}
    
    # Save translation
    translations = tool_context.state.get(STATE_TRANSLATIONS, {})
    translations[batch_id] = translation
    tool_context.state[STATE_TRANSLATIONS] = translations
    
    # Update batch status
    for batch in batches:
        if batch["batch_id"] == batch_id:
            batch["status"] = "translated"
            break
    tool_context.state[STATE_CONTENT_BATCHES] = batches
    
    print(f"[Translation Saved] Batch {batch_id}")
    
    return {
        "translation_saved": True, 
        "batch_id": batch_id
    }
def add_review_comment(tool_context: ToolContext, batch_id: int, comment: str, comment_type: str = "general") -> Dict:
    """Adds review comment for translator to improve translation"""
    comments = tool_context.state.get(STATE_REVIEW_COMMENTS, {})
    if batch_id not in comments:
        comments[batch_id] = []
    
    comment_entry = {
        "comment": comment,
        "comment_type": comment_type,  # "accuracy", "fluency", "consistency", "tone"
        "timestamp": "review_cycle"
    }
    
    comments[batch_id].append(comment_entry)
    tool_context.state[STATE_REVIEW_COMMENTS] = comments
    
    # Mark batch for revision
    batches = tool_context.state.get(STATE_CONTENT_BATCHES, [])
    for batch in batches:
        if batch["batch_id"] == batch_id:
            batch["status"] = "needs_revision"
            break
    tool_context.state[STATE_CONTENT_BATCHES] = batches
    
    return {"comment_added": True, "batch_id": batch_id, "comment_type": comment_type}

def mark_batch_complete(tool_context: ToolContext, batch_id: int) -> Dict:
    """Marks batch as complete after passing review"""
    batches = tool_context.state.get(STATE_CONTENT_BATCHES, [])
    for batch in batches:
        if batch["batch_id"] == batch_id:
            batch["status"] = "complete"
            break
    tool_context.state[STATE_CONTENT_BATCHES] = batches
    return {"batch_complete": True, "batch_id": batch_id}

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

def mock_save_to_database(tool_context: ToolContext) -> Dict:
    """Simulates saving final translations to database (TODO: Implement real DB)"""
    translations = tool_context.state.get(STATE_TRANSLATIONS, {})
    batches = tool_context.state.get(STATE_CONTENT_BATCHES, [])
    target_language = tool_context.state.get(STATE_TARGET_LANGUAGE, "Spanish")
    
    # TODO: Replace with actual database integration
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

def exit_loop(tool_context: ToolContext):
    """Exits the review loop when translations are complete"""
    print(f"[Loop Exit] Translation workflow complete - {tool_context.agent_name}")
    tool_context.actions.escalate = True
    return {}

def detect_input_type(tool_context: ToolContext, user_input: str) -> Dict:
    """Detects if input is JSON or plain text and processes accordingly"""
    try:
        # Try to parse as JSON
        content = json.loads(user_input)
        tool_context.state[STATE_SOURCE_CONTENT] = content
        
        print(f"[Input Detection] Detected JSON input with {len(content)} top-level keys")
        
        return {
            "input_type": "json",
            "content_stored": True,
            "sections": list(content.keys()) if isinstance(content, dict) else [],
            "message": "JSON content detected and parsed"
        }
    except json.JSONDecodeError:
        # It's plain text - wrap it in your expected structure
        wrapped_content = {
            "plain_text": {
                "type": "content",
                "value": user_input
            }
        }
        tool_context.state[STATE_SOURCE_CONTENT] = wrapped_content
        
        print(f"[Input Detection] Detected plain text input")
        
        return {
            "input_type": "text", 
            "content_stored": True,
            "message": "Plain text detected and wrapped for processing"
        }

def extract_target_language(tool_context: ToolContext, user_input: str) -> Dict:
    """Extracts target language from user input"""
    # Common patterns for language specification
    language_patterns = [
        r"(?:to|in|into)\s+(\w+(?:\s+\w+)?)",
        r"translate.*?(?:to|in|into)\s+(\w+(?:\s+\w+)?)",
        r"(\w+(?:\s+\w+)?)\s+translation"
    ]
    
    detected_language = None
    for pattern in language_patterns:
        match = re.search(pattern, user_input.lower())
        if match:
            detected_language = match.group(1).title()
            break
    
    if detected_language:
        # Normalize common language names
        language_map = {
            "Spanish": "Spanish", "Espanol": "Spanish", "Español": "Spanish",
            "French": "French", "Francais": "French", "Français": "French",
            "German": "German", "Deutsch": "German",
            "Portuguese": "Portuguese", "Portugues": "Portuguese", "Português": "Portuguese",
            "Italian": "Italian", "Italiano": "Italian",
            "Chinese": "Chinese (Mandarin)", "Mandarin": "Chinese (Mandarin)",
            "Japanese": "Japanese", "Korean": "Korean",
            "Arabic": "Arabic", "Russian": "Russian", "Hindi": "Hindi"
        }
        
        normalized_language = language_map.get(detected_language, detected_language)
        tool_context.state[STATE_TARGET_LANGUAGE] = normalized_language
        
        print(f"[Language Detection] Detected target language: {normalized_language}")
        return {"language_detected": normalized_language, "language_set": True}
    else:
        # Use default
        default_lang = tool_context.state.get(STATE_TARGET_LANGUAGE, "Spanish")
        print(f"[Language Detection] No language specified, using default: {default_lang}")
        return {"language_detected": default_lang, "language_set": False}

def build_final_output(tool_context: ToolContext) -> Dict:
    """Builds the final output in the correct format"""
    source_content = tool_context.state.get(STATE_SOURCE_CONTENT, {})
    translations = tool_context.state.get(STATE_TRANSLATIONS, {})
    batches = tool_context.state.get(STATE_CONTENT_BATCHES, [])
    target_language = tool_context.state.get(STATE_TARGET_LANGUAGE, "Spanish")
    
    # Check if this was plain text input
    if "plain_text" in source_content and len(source_content) == 1:
        # This was plain text - just return the translation
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
                    # This is a translatable item
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

# STEP 0: Input Analysis Agent
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

# STEP 1: CMS Content Reception & Change Detection
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

# STEP 2: Context Curation Agent
context_curator_agent = LlmAgent(
    name="ContextCuratorAgent", 
    model=GEMINI_MODEL,
    instruction="""You are a Context Curator for professional translation workflow.

    Your job is to organize content for optimal translation:
    1. Call `build_section_groups` to group content by sections for context-aware translation
    2. Call `create_translation_batches` to create batches based on the groups and change type
    3. For each batch, call `build_context_window` to create enhanced context
    
    Focus on providing rich context for small changes (UI elements need surrounding context) 
    and efficient grouping for large changes (content blocks can be processed in parallel).
    
    Report on the context structure created.""",
    description="Curates context and creates translation batches",
    tools=[build_section_groups, create_translation_batches, build_context_window],
)

# STEP 3: Batch Translation Agent (Parallel Structure)
batch_translator_agent = LlmAgent(
    name="BatchTranslatorAgent",
    model=GEMINI_MODEL,
    instruction="""You are a Professional Batch Translator following cached glossary and brand guidelines.

    For each pending translation batch:
    
    1. **Brand Term Check**: Call `check_brand_terms` with the source text to identify any brand terms
    2. **Context Analysis**: Review the context window, related translations, and change type  
    3. **Translation Process**:
       - Create translation preserving brand terms EXACTLY as they appear
       - Follow cached glossary terms for consistency
       - If context unclear: Call `add_clarifying_question`
    4. **Validation & Save**: 
       - Call `validate_translation` with batch_id and your translation
       - If validation passes: Call `save_translation` with batch_id and translation
       - If validation fails: Revise translation and try again

    CRITICAL: Brand terms (Octopi, WSOP, etc.) must appear EXACTLY the same in translation.
    Target language is in the state.""",
    description="Translates batches with brand term validation and cached guidelines",
    tools=[check_brand_terms, validate_translation, save_translation, add_clarifying_question],
)

# STEP 4: Batch Reviewer Agent  
batch_reviewer_agent = LlmAgent(
    name="BatchReviewerAgent",
    model=GEMINI_MODEL,
    instruction="""You are a Senior Translation Reviewer with website context knowledge.

    Review workflow:
    
    1. **Answer Clarifying Questions First**: 
       - For pending questions, call `answer_clarifying_question` with contextual answers
       - Use website context and brand guidelines to provide answers
    
    2. **Review Translated Batches**:
       - Check accuracy, fluency, and consistency with glossary
       - Verify brand terms are preserved
       - Ensure appropriate tone for content type
    
    3. **Review Decision**:
       - If translation is good: Call `mark_batch_complete`
       - If needs improvement: Call `add_review_comment` with specific feedback and comment_type
    
    4. **Completion Check**: 
       - Call `check_all_complete` to see if workflow is done
       - If all complete: Call `exit_loop`
    
    Use different iteration limits based on change type:
    - Small changes: Max 2-3 review cycles
    - Large changes: Max 5 review cycles""",
    description="Reviews translations, answers clarifying questions, and manages review cycles",
    tools=[answer_clarifying_question, mark_batch_complete, add_review_comment, check_all_complete, exit_loop],
)

# STEP 5: Revision Handler Agent
revision_handler_agent = LlmAgent(
    name="RevisionHandlerAgent",
    model=GEMINI_MODEL,
    instruction="""You handle translation revisions based on reviewer feedback.
    
    For batches with status='needs_revision':
    1. Read the review comments for specific feedback
    2. Apply the suggested improvements while maintaining glossary consistency
    3. Call `validate_translation` to ensure brand terms are preserved
    4. Call `save_translation` with the improved translation only if validation passes
    
    Focus on addressing reviewer concerns while keeping brand terms and cached glossary consistent.""",
    description="Handles translation revisions based on review feedback",
    tools=[validate_translation, save_translation],
)

# STEP 6: Database Integration Agent (Mock)
database_agent = LlmAgent(
    name="DatabaseAgent",
    model=GEMINI_MODEL,
    instruction="""You handle saving completed translations to the database.
    
    When all translations are complete and verified:
    1. Call `mock_save_to_database` to save final translations
    
    Provide a summary of what was saved and the final status.
    
    Note: This currently simulates database saving. TODO: Implement real database integration.""",
    description="Saves final translations to database (currently mocked)",
    tools=[mock_save_to_database],
)

# STEP 7: Output Builder Agent
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

# Review and revision loop with different iteration limits based on change type
translation_review_loop = LoopAgent(
    name="TranslationReviewLoop",
    sub_agents=[
        batch_translator_agent,
        batch_reviewer_agent, 
        revision_handler_agent,
    ],
    max_iterations=5  # Will be adjusted by reviewer based on change type
)

# Main workflow pipeline
root_agent = SequentialAgent(
    name="ProfessionalCMSTranslationWorkflow",
    sub_agents=[
        input_analysis_agent,        # NEW: Analyze input type and language
        cms_content_agent,           # 1. Receive changes & detect size
        context_curator_agent,       # 2. Build context & create batches  
        translation_review_loop,     # 3. Parallel translation & review cycles
        database_agent,              # 4. Save to database (mocked)
        output_builder_agent,        # 5. Build appropriate output format
    ],
    description="""Professional CMS Translation Workflow that handles both text and JSON:
    
    0. Input Analysis: Detects input type (text/JSON) and target language
    1. Content Reception: Processes content and determines workflow path
    2. Context Curation: Organizes content for translation
    3. Translation & Review: Multi-agent translation with quality assurance
    4. Database Integration: Saves completed translations
    5. Output Building: Returns results in appropriate format
    
    Mimics human professional translation workflow with AI agents."""
)

def run_translation_pipeline(content: Dict = None, target_language: str = "Spanish"):
    """Run the complete professional translation workflow"""
    session = create_translation_session(content, target_language)
    runner = InMemoryRunner(root_agent, APP_NAME)
    return runner, session

# Make available for ADK discovery
__all__ = ["root_agent", "create_translation_session", "run_translation_pipeline"]