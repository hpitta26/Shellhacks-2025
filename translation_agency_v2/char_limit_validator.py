#!/usr/bin/env python3
"""
Character Limit Validation for Translation System
=================================================
Validates translation length against UI compatibility requirements using ADK patterns.

Key Features:
- Validates translations against type-specific character limits
- Uses ADK after_agent_callback for seamless integration
- Automatically flags violations and triggers regeneration
"""
import json
from typing import Optional, Dict, Any, List
from google.genai import types
from google.adk.agents.callback_context import CallbackContext
from batch_processor import TranslationBatch


def validate_translation_length(translation_json: Dict[str, Any], batch: TranslationBatch) -> Dict[str, Any]:
    """
    Validate translation lengths against character limits.
    
    Args:
        translation_json: The translated items in JSON format
        batch: The original batch with character limit info
        
    Returns:
        Dictionary with validation results
    """
    if "items" not in translation_json:
        return {"valid": False, "error": "Missing 'items' in translation output"}
    
    translated_items = translation_json["items"]
    original_items = batch.items
    
    if len(translated_items) != len(original_items):
        return {
            "valid": False, 
            "error": f"Item count mismatch: expected {len(original_items)}, got {len(translated_items)}"
        }
    
    violations = []
    
    for i, (translated_item, original_item) in enumerate(zip(translated_items, original_items)):
        if "value" not in translated_item:
            violations.append({
                "item_index": i + 1,
                "item_type": original_item.type,
                "error": "Missing 'value' field in translated item"
            })
            continue
            
        translated_text = translated_item["value"]
        translated_length = len(translated_text)
        character_limit = original_item.get_character_limit()
        original_length = len(original_item.content)
        
        if translated_length > character_limit:
            violations.append({
                "item_index": i + 1,
                "item_type": original_item.type,
                "original_text": original_item.content,
                "translated_text": translated_text,
                "original_length": original_length,
                "translated_length": translated_length,
                "character_limit": character_limit,
                "excess_chars": translated_length - character_limit
            })
    
    if violations:
        return {
            "valid": False,
            "violations": violations,
            "total_violations": len(violations)
        }
    
    return {"valid": True, "message": "All translations within character limits"}


def create_length_validation_callback(batch: TranslationBatch) -> callable:
    """
    Create an after_agent_callback for character limit validation.
    
    Args:
        batch: The translation batch to validate against
        
    Returns:
        Callback function for ADK agent
    """
    def length_validation_callback(callback_context: CallbackContext) -> Optional[types.Content]:
        """
        ADK callback to validate translation lengths and flag violations.
        """
        agent_name = callback_context.agent_name
        current_state = callback_context.state.to_dict()
        
        print(f"\n🔍 [Length Validator] Checking {agent_name} output...")
        
        # Find the translation output for this batch
        # Assuming output_key follows pattern "translation_X"
        translation_key = None
        for key in current_state.keys():
            if key.startswith('translation_') and key in current_state:
                # This is a simple approach - in production you'd want more precise matching
                translation_key = key
                break
        
        if not translation_key:
            print(f"   ⚠️  No translation output found for {agent_name}")
            return None
        
        translation_data = current_state[translation_key]
        
        # Handle both string (JSON) and dict formats
        if isinstance(translation_data, str):
            try:
                translation_json = json.loads(translation_data)
            except json.JSONDecodeError:
                print(f"   ❌ Invalid JSON format in {translation_key}")
                return None
        elif isinstance(translation_data, dict):
            translation_json = translation_data
        else:
            print(f"   ❌ Unexpected data type: {type(translation_data)}")
            return None
        
        # Validate character limits
        validation_result = validate_translation_length(translation_json, batch)
        
        if validation_result["valid"]:
            print(f"   ✅ All translations within character limits")
            return None  # Allow normal execution
        
        # Handle violations
        violations = validation_result.get("violations", [])
        violation_count = len(violations)
        
        print(f"   ❌ {violation_count} character limit violations detected:")
        
        violation_details = []
        for violation in violations:
            print(f"      • Item {violation['item_index']} ({violation['item_type']}): "
                  f"{violation['translated_length']}/{violation['character_limit']} chars "
                  f"(+{violation['excess_chars']} over limit)")
            
            violation_details.append(
                f"- Item {violation['item_index']} ({violation['item_type']}): "
                f"'{violation['translated_text'][:50]}...' is {violation['translated_length']} chars, "
                f"exceeds limit of {violation['character_limit']} by {violation['excess_chars']} chars"
            )
        
        # Set violation flag in state for regeneration agent
        callback_context.state.update({
            f"{translation_key}_length_violations": {
                "violations": violations,
                "total_violations": violation_count,
                "needs_regeneration": True,
                "batch_id": batch.batch_id
            }
        })
        
        # Create feedback message for regeneration
        feedback_message = f"""
CHARACTER LIMIT VIOLATIONS DETECTED for {batch.group_name}:

{chr(10).join(violation_details)}

REQUIREMENTS:
- Headers/Buttons: Original length + 5 characters maximum
- Content: Original length + 20 characters maximum
- Must maintain meaning while staying within limits
- Consider abbreviations, shorter synonyms, or more concise phrasing

Please regenerate translations that exceed the character limits while preserving the original meaning and context.
"""
        
        # Add to regeneration feedback
        current_feedback = callback_context.state.get("regeneration_feedback", "")
        updated_feedback = current_feedback + "\n" + feedback_message
        callback_context.state.update({"regeneration_feedback": updated_feedback})
        
        print(f"   🔄 Flagged for regeneration: {violation_count} violations")
        
        return None  # Don't override the translation, just flag for regeneration
    
    return length_validation_callback


def get_character_limits_summary(batches: List[TranslationBatch]) -> str:
    """
    Get a summary of character limits for all batches.
    
    Args:
        batches: List of translation batches
        
    Returns:
        Formatted summary string
    """
    summary_lines = ["CHARACTER LIMITS SUMMARY:"]
    
    for batch in batches:
        summary_lines.append(f"\n{batch.group_name} ({batch.total_items} items):")
        for i, item in enumerate(batch.items, 1):
            limit = item.get_character_limit()
            summary_lines.append(
                f"  {i}. {item.type}: '{item.content}' → max {limit} chars"
            )
    
    return "\n".join(summary_lines)


# Export key components
__all__ = [
    "validate_translation_length",
    "create_length_validation_callback", 
    "get_character_limits_summary"
]
