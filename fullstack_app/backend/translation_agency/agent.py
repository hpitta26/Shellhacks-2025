# Professional Website Translation ADK Agent - Enhanced with Batch Processing

import asyncio
import json
import re
from typing import List, Dict, Any, Optional, AsyncGenerator
from google.adk.agents import LoopAgent, LlmAgent, BaseAgent, SequentialAgent
from google.genai import types
from google.adk.runners import InMemoryRunner
from google.adk.agents.invocation_context import InvocationContext
from google.adk.tools.tool_context import ToolContext
from google.adk.events import Event
from google.adk.sessions import InMemorySessionService
from google.adk.agents.callback_context import CallbackContext
import google.generativeai as genai

# --- Constants ---
APP_NAME = "enhanced_translation_workflow"
USER_ID = "cms_user_01"
SESSION_ID_BASE = "cms_translation_session"
GEMINI_MODEL = "gemini-2.5-flash"

# --- State Keys ---
STATE_SOURCE_CONTENT = "source_content"
STATE_INPUT_TYPE = "input_type"
STATE_TARGET_LANGUAGE = "target_language"
STATE_CHANGE_TYPE = "change_type"
STATE_TRANSLATIONS = "translations"
STATE_GLOSSARY = "glossary"
STATE_BRAND_TERMS = "brand_terms"
STATE_WORKFLOW_PATH = "workflow_path"
STATE_FINAL_OUTPUT = "final_output"

# --- New State Keys for Batch Processing ---
STATE_CONTENT_BATCHES = "content_batches"
STATE_CLARIFYING_QUESTIONS = "clarifying_questions"
STATE_BATCH_FEEDBACK = "batch_feedback"
STATE_CURRENT_BATCH = "current_batch"
STATE_COMPLETED_BATCHES = "completed_batches"
STATE_REVISION_NEEDED = "revision_needed"

def create_translation_session(content: Dict = None, target_language: str = "Spanish"):
    """Create a new translation session with enhanced state for batch processing"""
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
            STATE_TRANSLATIONS: {},
            STATE_GLOSSARY: {},
            STATE_BRAND_TERMS: [],
            STATE_WORKFLOW_PATH: "unknown",
            STATE_FINAL_OUTPUT: None,
            # New batch processing state
            STATE_CONTENT_BATCHES: {},
            STATE_CLARIFYING_QUESTIONS: [],
            STATE_BATCH_FEEDBACK: {},
            STATE_CURRENT_BATCH: None,
            STATE_COMPLETED_BATCHES: [],
            STATE_REVISION_NEEDED: False
        }
    )

# --- Existing Tool Functions (Fixed) ---

def analyze_and_route_content(tool_context: ToolContext, user_input: str) -> Dict:
    """Combined input analysis and smart routing - reduces agent switches"""
    cleaned_input = user_input.strip()
    
    # Detect input type and parse content
    if cleaned_input.startswith('{') and cleaned_input.endswith('}'):
        try:
            content = json.loads(cleaned_input)
            tool_context.state[STATE_SOURCE_CONTENT] = content
            tool_context.state[STATE_INPUT_TYPE] = "json"
            total_items = count_translatable_items(content)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON format"}
    else:
        # Plain text
        content = {"plain_text": {"type": "content", "value": cleaned_input}}
        tool_context.state[STATE_SOURCE_CONTENT] = content
        tool_context.state[STATE_INPUT_TYPE] = "text"
        total_items = 1
    
    # Extract target language
    target_language = extract_language_from_input(user_input)
    tool_context.state[STATE_TARGET_LANGUAGE] = target_language
    
    # Smart routing based on content size
    if total_items <= 5:
        change_type = "small"
        workflow_path = "fast_track"
    else:
        change_type = "large" 
        workflow_path = "batch_pipeline"
    
    tool_context.state[STATE_CHANGE_TYPE] = change_type
    tool_context.state[STATE_WORKFLOW_PATH] = workflow_path
    
    # Load glossary and brand terms
    load_translation_resources(tool_context)
    
    print(f"[Smart Router] {workflow_path} workflow for {total_items} items to {target_language}")
    
    return {
        "input_type": tool_context.state[STATE_INPUT_TYPE],
        "target_language": target_language,
        "change_type": change_type,
        "workflow_path": workflow_path,
        "total_items": total_items,
        "ready_for_translation": True
    }

def count_translatable_items(content: Dict) -> int:
    """Count items that need translation"""
    count = 0
    def traverse(obj):
        nonlocal count
        if isinstance(obj, dict):
            if "type" in obj and "value" in obj:
                count += 1
            else:
                for value in obj.values():
                    traverse(value)
        elif isinstance(obj, list):
            for item in obj:
                traverse(item)
    traverse(content)
    return count

def extract_language_from_input(user_input: str) -> str:
    """Extract target language from user input"""
    language_patterns = [
        r"translate.*?(?:to|in|into)\s+(\w+)",
        r"(?:to|in|into)\s+(\w+)",
        r"(\w+)\s+translation"
    ]
    
    user_lower = user_input.lower()
    for pattern in language_patterns:
        match = re.search(pattern, user_lower)
        if match:
            detected = match.group(1).title()
            language_map = {
                "Spanish": "Spanish", "Espanol": "Spanish", "Español": "Spanish",
                "French": "French", "Francais": "French", "Français": "French",
                "German": "German", "Portuguese": "Portuguese", "Italian": "Italian"
            }
            return language_map.get(detected, detected)
    
    return "Spanish"  # Default

def load_translation_resources(tool_context: ToolContext):
    """Load glossary and brand terms"""
    glossary = {
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
    
    tool_context.state[STATE_GLOSSARY] = glossary
    tool_context.state[STATE_BRAND_TERMS] = brand_terms

def fast_track_translate(tool_context: ToolContext) -> Dict:
    """Fast translation for small changes - skips complex grouping"""
    content = tool_context.state.get(STATE_SOURCE_CONTENT, {})
    target_language = tool_context.state.get(STATE_TARGET_LANGUAGE, "Spanish")
    glossary = tool_context.state.get(STATE_GLOSSARY, {})
    brand_terms = tool_context.state.get(STATE_BRAND_TERMS, [])
    
    translations = {}
    
    def translate_item(obj, path=""):
        if isinstance(obj, dict):
            if "type" in obj and "value" in obj:
                original_text = str(obj["value"])
                translated_text = apply_translation_rules(original_text, target_language, glossary, brand_terms)
                translations[path] = translated_text
                obj["value"] = translated_text
            else:
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    translate_item(value, current_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                translate_item(item, f"{path}[{i}]")
    
    import copy
    translated_content = copy.deepcopy(content)
    translate_item(translated_content)
    
    tool_context.state[STATE_TRANSLATIONS] = translations
    tool_context.state[STATE_SOURCE_CONTENT] = translated_content
    
    print(f"[Fast Track] Translated {len(translations)} items directly")
    
    return {
        "translation_method": "fast_track",
        "items_translated": len(translations),
        "target_language": target_language,
        "ready_for_output": True
    }

# --- New Batch Processing Tool Functions ---

def organize_content_into_batches(tool_context: ToolContext) -> Dict:
    """Organize content by type for batch processing"""
    content = tool_context.state.get(STATE_SOURCE_CONTENT, {})
    target_language = tool_context.state.get(STATE_TARGET_LANGUAGE, "Spanish")
    
    content_batches = {
        "navigation": [],
        "buttons": [],
        "headers": [],
        "body_text": [],
        "form_labels": [],
        "meta_content": []
    }
    
    def classify_and_batch(obj, path=""):
        if isinstance(obj, dict):
            if "type" in obj and "value" in obj:
                content_type = classify_content_type(obj, path)
                original_length = len(str(obj["value"]))
                max_chars = calculate_max_chars(original_length, target_language)
                
                content_batches[content_type].append({
                    "path": path,
                    "original": str(obj["value"]),
                    "type": obj["type"],
                    "content_category": content_type,
                    "original_length": original_length,
                    "max_chars": max_chars,
                    "translated": None,
                    "status": "pending"
                })
            else:
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    classify_and_batch(value, current_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                classify_and_batch(item, f"{path}[{i}]")
    
    classify_and_batch(content)
    
    # Remove empty batches
    content_batches = {k: v for k, v in content_batches.items() if v}
    
    tool_context.state[STATE_CONTENT_BATCHES] = content_batches
    tool_context.state[STATE_CLARIFYING_QUESTIONS] = []
    tool_context.state[STATE_COMPLETED_BATCHES] = []
    
    total_items = sum(len(batch) for batch in content_batches.values())
    print(f"[Batch Organizer] Organized {total_items} items into {len(content_batches)} content types")
    
    return {
        "batches_created": len(content_batches),
        "total_items": total_items,
        "batch_types": list(content_batches.keys()),
        "ready_for_batch_translation": True
    }

def classify_content_type(content_obj: Dict, path: str) -> str:
    """Classify content type based on object type and path"""
    content_value = str(content_obj.get("value", "")).lower()
    path_lower = path.lower()
    
    # Navigation patterns
    if any(keyword in path_lower for keyword in ["nav", "menu", "link", "breadcrumb"]):
        return "navigation"
    
    # Button patterns
    if any(keyword in path_lower for keyword in ["button", "btn", "cta", "action"]):
        return "buttons"
    
    # Header patterns
    if any(keyword in path_lower for keyword in ["header", "title", "heading", "h1", "h2", "h3"]):
        return "headers"
    
    # Form patterns
    if any(keyword in path_lower for keyword in ["form", "label", "input", "field"]):
        return "form_labels"
    
    # Meta content patterns
    if any(keyword in path_lower for keyword in ["meta", "description", "keywords", "seo"]):
        return "meta_content"
    
    # Default to body text
    return "body_text"

def calculate_max_chars(original_length: int, target_language: str) -> int:
    """Calculate maximum character count based on original length and target language"""
    # Language expansion factors
    expansion_factors = {
        "Spanish": 1.25,
        "French": 1.3,
        "German": 1.4,
        "Portuguese": 1.25,
        "Italian": 1.2
    }
    
    expansion = expansion_factors.get(target_language, 1.3)
    
    # Apply scaling based on original length
    if original_length <= 10:
        max_expansion = 2.0  # Very short text can expand significantly
    elif original_length <= 30:
        max_expansion = expansion + 0.3
    else:
        max_expansion = expansion
    
    return int(original_length * max_expansion)

def translate_content_batch(tool_context: ToolContext) -> Dict:
    """Translate a batch of content with context awareness"""
    content_batches = tool_context.state.get(STATE_CONTENT_BATCHES, {})
    target_language = tool_context.state.get(STATE_TARGET_LANGUAGE, "Spanish")
    glossary = tool_context.state.get(STATE_GLOSSARY, {})
    brand_terms = tool_context.state.get(STATE_BRAND_TERMS, [])
    completed_batches = tool_context.state.get(STATE_COMPLETED_BATCHES, [])
    clarifying_questions = tool_context.state.get(STATE_CLARIFYING_QUESTIONS, [])
    
    # Find next batch to translate
    current_batch_type = None
    for batch_type, batch_items in content_batches.items():
        if batch_type not in completed_batches:
            if any(item["status"] == "pending" for item in batch_items):
                current_batch_type = batch_type
                break
    
    if not current_batch_type:
        return {
            "status": "all_batches_completed",
            "completed_batches": len(completed_batches),
            "ready_for_review": True
        }
    
    current_batch = content_batches[current_batch_type]
    tool_context.state[STATE_CURRENT_BATCH] = current_batch_type
    
    # Translate items in current batch
    translated_items = 0
    questions_generated = 0
    
    for item in current_batch:
        if item["status"] == "pending":
            # Check for ambiguity and generate clarifying questions if needed
            question = check_for_clarification_needed(item, current_batch_type, target_language)
            if question:
                clarifying_questions.append({
                    "batch_type": current_batch_type,
                    "item_path": item["path"],
                    "question": question,
                    "answered": False,
                    "answer": None
                })
                questions_generated += 1
                item["status"] = "needs_clarification"
            else:
                # Translate the item
                translated_text = apply_translation_rules(
                    item["original"], target_language, glossary, brand_terms
                )
                
                # Check character limit
                if len(translated_text) > item["max_chars"]:
                    # Try to get a shorter translation
                    translated_text = get_shorter_translation(
                        item["original"], target_language, item["max_chars"], glossary, brand_terms
                    )
                
                item["translated"] = translated_text
                item["status"] = "translated"
                translated_items += 1
    
    tool_context.state[STATE_CLARIFYING_QUESTIONS] = clarifying_questions
    
    print(f"[Batch Translator] Translated {translated_items} items in {current_batch_type} batch")
    if questions_generated > 0:
        print(f"[Batch Translator] Generated {questions_generated} clarifying questions")
    
    return {
        "batch_type": current_batch_type,
        "items_translated": translated_items,
        "questions_generated": questions_generated,
        "ready_for_review": True
    }

def check_for_clarification_needed(item: Dict, batch_type: str, target_language: str) -> Optional[str]:
    """Check if translation needs clarification"""
    original_text = item["original"].lower()
    
    # Check for ambiguous terms that might need clarification
    ambiguous_patterns = [
        ("play", "Does 'play' refer to gaming action or video playback?"),
        ("run", "Does 'run' mean execute/operate or physical running?"),
        ("bank", "Does 'bank' refer to financial institution or poker bankroll?"),
        ("fold", "Does 'fold' refer to poker action or user interface collapse?"),
        ("table", "Does 'table' refer to poker table or data table?")
    ]
    
    for pattern, question in ambiguous_patterns:
        if pattern in original_text:
            return f"{question} Context: {batch_type} section, text: '{item['original']}'"
    
    # Check for very short technical terms that might be brand-specific
    if len(item["original"]) <= 3 and batch_type in ["buttons", "navigation"]:
        return f"Should '{item['original']}' be translated or kept as-is? It appears in {batch_type} section."
    
    return None

def get_shorter_translation(original: str, target_language: str, max_chars: int, glossary: Dict, brand_terms: List) -> str:
    """Get a shorter translation that fits character limits"""
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        prompt = f"""Translate this text to {target_language} in maximum {max_chars} characters.

Original: {original}
Max characters: {max_chars}
Brand terms to preserve: {', '.join(brand_terms)}

Rules:
1. Must be under {max_chars} characters
2. Preserve meaning
3. Use concise, natural phrasing
4. Don't translate brand terms

Return only the short translation:"""
        
        response = model.generate_content(prompt)
        short_translation = response.text.strip()
        
        # Remove any markdown formatting
        if short_translation.startswith('```'):
            short_translation = short_translation.replace('```', '').strip()
        
        return short_translation[:max_chars]  # Ensure limit
        
    except Exception as e:
        print(f"[Short Translation Error] {e}")
        # Fallback: truncate original translation
        return original[:max_chars]

def review_batch_translation(tool_context: ToolContext) -> Dict:
    """Review translated batch and provide feedback"""
    current_batch_type = tool_context.state.get(STATE_CURRENT_BATCH)
    content_batches = tool_context.state.get(STATE_CONTENT_BATCHES, {})
    clarifying_questions = tool_context.state.get(STATE_CLARIFYING_QUESTIONS, [])
    target_language = tool_context.state.get(STATE_TARGET_LANGUAGE, "Spanish")
    
    if not current_batch_type or current_batch_type not in content_batches:
        return {"error": "No current batch to review"}
    
    current_batch = content_batches[current_batch_type]
    
    # First, handle any unanswered clarifying questions
    unanswered_questions = [q for q in clarifying_questions if not q.get("answered", False)]
    if unanswered_questions:
        # Answer questions using context
        for question in unanswered_questions:
            answer = answer_clarifying_question(question, current_batch_type, tool_context.state)
            question["answer"] = answer
            question["answered"] = True
        
        tool_context.state[STATE_CLARIFYING_QUESTIONS] = clarifying_questions
        tool_context.state[STATE_REVISION_NEEDED] = True
        
        return {
            "status": "questions_answered",
            "questions_resolved": len(unanswered_questions),
            "revision_needed": True
        }
    
    # Review translation quality
    batch_feedback = []
    items_needing_revision = 0
    
    for item in current_batch:
        if item["status"] == "translated":
            feedback = review_translation_item(item, current_batch_type, target_language)
            if feedback:
                batch_feedback.append({
                    "path": item["path"],
                    "issue": feedback,
                    "original": item["original"],
                    "current_translation": item["translated"]
                })
                items_needing_revision += 1
                item["status"] = "needs_revision"
            else:
                item["status"] = "approved"
    
    # Store feedback for revision
    tool_context.state[STATE_BATCH_FEEDBACK] = batch_feedback
    
    if items_needing_revision > 0:
        tool_context.state[STATE_REVISION_NEEDED] = True
        tool_context.state["review_result"] = f"Found {items_needing_revision} items needing revision in {current_batch_type} batch"
    else:
        # Batch is approved
        completed_batches = tool_context.state.get(STATE_COMPLETED_BATCHES, [])
        completed_batches.append(current_batch_type)
        tool_context.state[STATE_COMPLETED_BATCHES] = completed_batches
        tool_context.state[STATE_REVISION_NEEDED] = False
        tool_context.state["review_result"] = "EXIT"
    
    print(f"[Batch Reviewer] Reviewed {current_batch_type} batch: {items_needing_revision} items need revision")
    
    return {
        "batch_type": current_batch_type,
        "items_reviewed": len(current_batch),
        "items_needing_revision": items_needing_revision,
        "revision_needed": items_needing_revision > 0,
        "batch_approved": items_needing_revision == 0
    }

def answer_clarifying_question(question: Dict, batch_type: str, state: Dict) -> str:
    """Answer clarifying question using website context"""
    question_text = question["question"]
    item_path = question["item_path"]
    
    # Use context to answer common questions
    if "play" in question_text.lower():
        if batch_type == "buttons" or "game" in item_path.lower():
            return "Gaming action - translate as game play"
        else:
            return "Video playback - translate as media play"
    
    elif "bank" in question_text.lower():
        if "poker" in str(state).lower():
            return "Poker bankroll - use gambling-specific translation"
        else:
            return "Financial institution - use standard banking term"
    
    elif "table" in question_text.lower():
        if batch_type == "navigation" or "data" in item_path.lower():
            return "Data table - use UI table translation"
        else:
            return "Poker table - use gambling-specific translation"
    
    elif "keep as-is" in question_text.lower():
        return "Translate - maintain consistency with rest of interface"
    
    return "Use context-appropriate translation maintaining brand consistency"

def review_translation_item(item: Dict, batch_type: str, target_language: str) -> Optional[str]:
    """Review individual translation item for quality issues"""
    original = item["original"]
    translated = item["translated"]
    max_chars = item["max_chars"]
    
    # Check character limit
    if len(translated) > max_chars:
        return f"Translation exceeds character limit ({len(translated)}/{max_chars})"
    
    # Check for untranslated brand terms (they should be preserved)
    brand_terms = ["Octopi", "PokerGO", "WSOP", "ICM", "GTO"]
    for brand in brand_terms:
        if brand in original and brand not in translated:
            return f"Brand term '{brand}' was incorrectly translated - should be preserved"
    
    # Check for missing content
    if len(translated.strip()) == 0:
        return "Translation is empty"
    
    # Use Gemini for quality review
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        prompt = f"""Review this translation quality for {batch_type} content:

Original ({len(original)} chars): {original}
Translation ({len(translated)} chars): {translated}
Target: {target_language}
Max chars: {max_chars}

Check for:
1. Meaning accuracy
2. Cultural appropriateness  
3. UI/UX suitability for {batch_type}
4. Natural fluency

If perfect, respond: OK
If issues found, respond with specific problem."""

        response = model.generate_content(prompt)
        result = response.text.strip()
        
        return None if result == "OK" else result
        
    except Exception as e:
        print(f"[Review Error] {e}")
        return None

def revise_batch_translation(tool_context: ToolContext) -> Dict:
    """Revise translations based on reviewer feedback"""
    batch_feedback = tool_context.state.get(STATE_BATCH_FEEDBACK, [])
    content_batches = tool_context.state.get(STATE_CONTENT_BATCHES, {})
    current_batch_type = tool_context.state.get(STATE_CURRENT_BATCH)
    target_language = tool_context.state.get(STATE_TARGET_LANGUAGE, "Spanish")
    glossary = tool_context.state.get(STATE_GLOSSARY, {})
    brand_terms = tool_context.state.get(STATE_BRAND_TERMS, [])
    
    if not batch_feedback:
        return {"status": "no_feedback_to_address"}
    
    current_batch = content_batches.get(current_batch_type, [])
    revisions_made = 0
    
    # Address each feedback item
    for feedback_item in batch_feedback:
        item_path = feedback_item["path"]
        issue = feedback_item["issue"]
        
        # Find the item in the batch
        for item in current_batch:
            if item["path"] == item_path and item["status"] == "needs_revision":
                # Create revised translation based on specific feedback
                revised_translation = create_revised_translation(
                    item["original"], 
                    item["translated"],
                    issue,
                    target_language,
                    item["max_chars"],
                    glossary,
                    brand_terms
                )
                
                item["translated"] = revised_translation
                item["status"] = "revised"
                revisions_made += 1
                break
    
    # Clear feedback after addressing
    tool_context.state[STATE_BATCH_FEEDBACK] = []
    tool_context.state[STATE_REVISION_NEEDED] = False
    
    print(f"[Batch Reviser] Made {revisions_made} revisions to {current_batch_type} batch")
    
    return {
        "revisions_made": revisions_made,
        "batch_type": current_batch_type,
        "ready_for_re_review": True
    }

def create_revised_translation(original: str, current_translation: str, issue: str, target_language: str, max_chars: int, glossary: Dict, brand_terms: List) -> str:
    """Create revised translation addressing specific issue"""
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        brand_terms_str = ", ".join(brand_terms)
        
        prompt = f"""Fix this translation based on the specific issue:

Original: {original}
Current translation: {current_translation}
Issue to fix: {issue}
Target language: {target_language}
Max characters: {max_chars}
Brand terms to preserve: {brand_terms_str}

Rules:
1. Address the specific issue mentioned
2. Stay under {max_chars} characters
3. Preserve brand terms exactly
4. Maintain natural fluency

Return only the corrected translation:"""

        response = model.generate_content(prompt)
        revised_text = response.text.strip()
        
        # Remove markdown formatting
        if revised_text.startswith('```'):
            revised_text = revised_text.replace('```', '').strip()
        
        # Ensure character limit
        if len(revised_text) > max_chars:
            revised_text = revised_text[:max_chars]
        
        return revised_text
        
    except Exception as e:
        print(f"[Revision Error] {e}")
        return current_translation  # Return original if revision fails

def apply_batch_translations_to_content(tool_context: ToolContext) -> Dict:
    """Apply all approved batch translations back to the original content structure"""
    content_batches = tool_context.state.get(STATE_CONTENT_BATCHES, {})
    content = tool_context.state.get(STATE_SOURCE_CONTENT, {})
    
    translations_applied = 0
    
    # Apply translations from all batches
    for batch_type, batch_items in content_batches.items():
        for item in batch_items:
            if item["status"] in ["approved", "revised"] and item["translated"]:
                # Navigate to the item in the content structure and update it
                path_parts = item["path"].split('.')
                current_obj = content
                
                try:
                    # Navigate to the parent object
                    for part in path_parts[:-1]:
                        if '[' in part and ']' in part:
                            # Handle array index
                            key, index = part.split('[')
                            index = int(index.rstrip(']'))
                            current_obj = current_obj[key][index]
                        else:
                            current_obj = current_obj[part]
                    
                    # Update the final value
                    final_key = path_parts[-1]
                    if '[' in final_key and ']' in final_key:
                        key, index = final_key.split('[')
                        index = int(index.rstrip(']'))
                        current_obj[key][index]["value"] = item["translated"]
                    else:
                        current_obj[final_key]["value"] = item["translated"]
                    
                    translations_applied += 1
                    
                except (KeyError, IndexError, ValueError) as e:
                    print(f"[Apply Translations] Error updating path {item['path']}: {e}")
    
    tool_context.state[STATE_SOURCE_CONTENT] = content
    
    print(f"[Apply Translations] Applied {translations_applied} translations to content structure")
    
    return {
        "translations_applied": translations_applied,
        "ready_for_final_output": True
    }

def translate_with_gemini(text: str, target_language: str, glossary: Dict, brand_terms: List) -> str:
    """Use Gemini model to translate text while preserving brand terms - FIXED"""
    try:
        import google.generativeai as genai
        
        model = genai.GenerativeModel(GEMINI_MODEL)
        brand_terms_str = ", ".join(brand_terms) if brand_terms else "None"
        
        # Build glossary context for prompt
        glossary_context = ""
        if glossary and target_language in str(glossary):
            glossary_items = []
            for term, translations in glossary.items():
                if isinstance(translations, dict) and target_language in translations:
                    glossary_items.append(f"'{term}' = '{translations[target_language]}'")
            if glossary_items:
                glossary_context = f"\nUse these specific translations: {'; '.join(glossary_items)}"
        
        # Create translation prompt
        prompt = f"""Translate the following text to {target_language}. 

IMPORTANT RULES:
1. Preserve these brand terms exactly as written: {brand_terms_str}
2. These are proper nouns and should NOT be translated{glossary_context}
3. Maintain the original tone and style
4. Return ONLY the translated text, no explanations, no markdown formatting, no code blocks

Text to translate:
{text}"""
        
        # Generate translation
        response = model.generate_content(prompt)
        translated_text = response.text.strip()
        
        # FIX: Remove markdown code blocks if present
        if translated_text.startswith('```json'):
            translated_text = translated_text.replace('```json', '').replace('```', '').strip()
        elif translated_text.startswith('```'):
            translated_text = translated_text.replace('```', '').strip()
        
        print(f"[Gemini Translation] '{text[:50]}...' -> '{translated_text[:50]}...'")
        return translated_text
        
    except Exception as e:
        print(f"[Translation Error] {str(e)}, falling back to basic translation")
        return fallback_translation(text, target_language)

def apply_translation_rules(text: str, target_language: str, glossary: Dict, brand_terms: List) -> str:
    """Apply translation rules with LLM-based translation and brand term preservation"""
    
    # Step 1: Use Gemini for actual translation
    translated_text = translate_with_gemini(text, target_language, glossary, brand_terms)
    
    # Step 2: Apply glossary terms (in case LLM missed some)
    for term, translations_dict in glossary.items():
        if isinstance(translations_dict, dict) and target_language in translations_dict:
            if term.lower() in translated_text.lower():
                translated_text = re.sub(
                    r'\b' + re.escape(term) + r'\b',
                    translations_dict[target_language],
                    translated_text,
                    flags=re.IGNORECASE
                )
    
    # Step 3: Preserve brand terms (must be last)
    for brand_term in brand_terms:
        if isinstance(brand_term, str) and brand_term.lower() in text.lower():
            # Find exact case from original and preserve it
            pattern = re.compile(re.escape(brand_term), re.IGNORECASE)
            match = pattern.search(text)
            if match:
                exact_brand_term = match.group(0)
                translated_text = pattern.sub(exact_brand_term, translated_text)
    
    return translated_text

def fallback_translation(text: str, target_language: str) -> str:
    """Fallback translation using basic rules"""
    if target_language == "Spanish":
        basic_translations = {
            "Shop Now": "Comprar Ahora",
            "Start Training Now": "Empezar a Entrenar Ahora",
            "Read More": "Leer Más",
            "Login": "Iniciar Sesión",
            "Sign Up": "Registrarse",
            "Dashboard": "Panel",
            "Settings": "Configuración"
        }
        
        translated_text = text
        for eng, spa in basic_translations.items():
            if eng in translated_text:
                translated_text = translated_text.replace(eng, spa)
        return translated_text
    
    return text

def build_final_output(tool_context: ToolContext) -> Dict:
    """Build final output based on input type"""
    input_type = tool_context.state.get(STATE_INPUT_TYPE, "json")
    content = tool_context.state.get(STATE_SOURCE_CONTENT, {})
    
    if input_type == "text" and "plain_text" in content:
        # Return just the translated text
        final_output = content["plain_text"]["value"]
    else:
        # Return translated JSON
        final_output = json.dumps(content, ensure_ascii=False, indent=2)
    
    tool_context.state[STATE_FINAL_OUTPUT] = final_output
    
    print(f"[Final Output] Generated {input_type} output")
    
    return {
        "output_type": input_type,
        "final_output": final_output
    }

# --- Fixed Review System Callbacks ---

def check_for_batch_review_exit(callback_context: CallbackContext):
    """Fixed callback to check if batch reviewer wants to exit the loop"""
    # Access the review result from state instead of events
    review_result = callback_context.state.get('review_result', '').strip()
    
    if review_result == "EXIT":
        callback_context.actions.escalate = True
        callback_context.state["batch_review_approved"] = True
        print("[Batch Review Loop] Batch approved - exiting loop")
    else:
        callback_context.state["batch_feedback_provided"] = review_result
        print(f"[Batch Review Loop] Feedback provided: {review_result[:100]}...")

# --- New Agent Definitions ---

# Smart router (existing, but updated)
smart_router_agent = LlmAgent(
    name="SmartRouterAgent",
    model=GEMINI_MODEL,
    instruction="""You are a Smart Router that efficiently processes translation requests.

    When you receive user input:
    1. Call `analyze_and_route_content` with the user's message
    2. This will detect input type, extract language, determine content size, and load resources
    3. Report the routing decision (fast_track vs batch_pipeline)
    
    This single call replaces multiple analysis steps for efficiency.""",
    description="Analyzes input and routes to appropriate workflow path",
    tools=[analyze_and_route_content],
    output_key="routing_result"
)

# Batch organizer agent
batch_organizer_agent = LlmAgent(
    name="BatchOrganizerAgent",
    model=GEMINI_MODEL,
    instruction="""You organize content into batches by content type for efficient translation.
    
    Call `organize_content_into_batches` to:
    1. Classify content by type (navigation, buttons, headers, body_text, etc.)
    2. Calculate character limits for each item based on target language
    3. Prepare batches for systematic translation
    
    Only used when workflow_path is 'batch_pipeline'.""",
    description="Organizes content into batches by type",
    tools=[organize_content_into_batches],
    output_key="batch_organization"
)

# Fast translator (existing)
fast_translator_agent = LlmAgent(
    name="FastTranslatorAgent", 
    model=GEMINI_MODEL,
    instruction="""You handle fast translation for small content changes (≤5 items).

    For fast track workflows:
    1. Call `fast_track_translate` to translate all items directly
    2. This skips complex grouping and batching for efficiency
    3. Report completion status
    
    Only used when workflow_path is 'fast_track'.""",
    description="Handles direct translation for small changes",
    tools=[fast_track_translate],
    output_key="fast_translation_result"
)

# Batch translation agent
batch_translation_agent = LlmAgent(
    name="BatchTranslationAgent",
    model=GEMINI_MODEL,
    instruction="""You are a professional translator specializing in website content. You translate content in batches organized by content type.

    Process:
    1. Call `translate_content_batch` to translate the next pending batch
    2. Apply glossary terms and preserve brand terms consistently
    3. Generate clarifying questions when encountering ambiguous content
    4. Ensure translations respect character limits for UI elements
    
    You follow professional translation practices:
    - Maintain context awareness within each content type
    - Ask questions rather than guessing at ambiguous meanings
    - Apply appropriate tone for each content category
    - Respect technical and brand terminology""",
    description="Translates content batches with professional quality and context awareness",
    tools=[translate_content_batch],
    output_key="batch_translation_result"
)

# Batch reviewer agent
batch_reviewer_agent = LlmAgent(
    name="BatchReviewerAgent",
    model=GEMINI_MODEL,
    instruction="""You are a translation quality reviewer and project manager. Your role is to ensure translation quality and resolve clarifying questions.

    Process:
    1. Call `review_batch_translation` to review the current batch
    2. Answer any clarifying questions using website context and domain knowledge
    3. Check translation quality against professional criteria:
       - Brand term preservation
       - Glossary consistency
       - Character limit compliance
       - Cultural appropriateness
       - Technical accuracy
    4. Provide specific, actionable feedback for any issues found
    
    You act as both reviewer and domain expert, resolving ambiguities and ensuring professional quality.""",
    description="Reviews batch translations and answers clarifying questions",
    tools=[review_batch_translation],
    output_key="review_result",
    after_agent_callback=check_for_batch_review_exit
)

# Batch revision agent
batch_revision_agent = LlmAgent(
    name="BatchRevisionAgent",
    model=GEMINI_MODEL,
    instruction="""You are a specialized revision agent focused on correcting specific translation issues.

    Process:
    1. Call `revise_batch_translation` to address reviewer feedback
    2. Make targeted corrections based on specific issues identified
    3. Ensure all revisions maintain consistency with approved translations
    
    You are different from the initial translator - you focus specifically on fixing identified problems rather than doing fresh translations.""",
    description="Makes targeted revisions based on reviewer feedback",
    tools=[revise_batch_translation],
    output_key="revision_result"
)

# Content applicator agent
content_applicator_agent = LlmAgent(
    name="ContentApplicationAgent",
    model=GEMINI_MODEL,
    instruction="""Apply all approved batch translations back to the original content structure.
    
    Call `apply_batch_translations_to_content` to:
    1. Take all approved translations from completed batches
    2. Apply them back to the original JSON structure
    3. Prepare for final output generation""",
    description="Applies approved translations back to content structure",
    tools=[apply_batch_translations_to_content],
    output_key="application_result"
)

# Output agent (existing)
output_agent = LlmAgent(
    name="OutputAgent",
    model=GEMINI_MODEL,
    instruction="""You build the final translated output.

    When translation is complete:
    1. Call `build_final_output` to create the appropriate format
    2. Present the final result to the user
    
    Return JSON structure for JSON input, plain text for text input.""",
    description="Builds and presents final translated output",
    tools=[build_final_output],
    output_key="final_output"
)

# --- Updated Conditional Agent ---

class ConditionalTranslationAgent(BaseAgent):
    """Routes to fast or batch translation based on content size"""
    
    def __init__(self):
        # Create sub-agents
        fast_agent = fast_translator_agent
        batch_organizer = batch_organizer_agent
        
        # Pass sub-agents to BaseAgent constructor
        super().__init__(
            name="ConditionalTranslationAgent",
            description="Routes to appropriate translation method based on content size",
            sub_agents=[fast_agent, batch_organizer]
        )
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Custom routing logic based on workflow path in session state"""
        # Get workflow path from session state
        workflow_path = ctx.session.state.get(STATE_WORKFLOW_PATH, "unknown")
        
        # Create event using correct format
        text_part = types.Part(text=f"[Conditional Router] Routing to {workflow_path} workflow")
        content_payload = types.Content(parts=[text_part], role="system")
        status_event = Event(content=content_payload, author=self.name)
        yield status_event
        
        if workflow_path == "fast_track":
            print("[Conditional Router] Using fast track translation")
            # Run the fast translator agent
            async for event in self.sub_agents[0].run_async(ctx):
                yield event
        else:
            print("[Conditional Router] Using batch pipeline - organizing content")
            # Run the batch organizer agent
            async for event in self.sub_agents[1].run_async(ctx):
                yield event

# --- Batch Processing Loop ---

# Sequential agent for batch processing loop
batch_processing_body = SequentialAgent(
    name="BatchProcessingBody",
    sub_agents=[
        batch_translation_agent,
        batch_reviewer_agent,
        batch_revision_agent
    ],
    description="Translates batch, reviews quality, and revises if needed"
)

# Loop agent for processing all batches
batch_processing_loop = LoopAgent(
    name="BatchProcessingLoop",
    sub_agents=[batch_processing_body],
    max_iterations=10,  # Allow processing of multiple batches
    description="Processes all content batches until completion"
)

# --- Final Enhanced Root Agent ---

root_agent = SequentialAgent(
    name="EnhancedWebsiteTranslationWorkflow",
    sub_agents=[
        smart_router_agent,              # 1. Analyze & route
        ConditionalTranslationAgent(),   # 2. Fast track OR batch organize
        batch_processing_loop,           # 3. Batch processing (only runs if batch_pipeline)
        content_applicator_agent,        # 4. Apply translations to content
        output_agent,                    # 5. Build final output
    ],
    description="Enhanced website translation workflow with professional batch processing and quality review"
)

def run_translation_pipeline(content: Dict = None, target_language: str = "Spanish"):
    """Run the enhanced translation workflow"""
    session = create_translation_session(content, target_language)
    runner = InMemoryRunner(root_agent, APP_NAME)
    return runner, session

__all__ = ["root_agent", "create_translation_session", "run_translation_pipeline"]