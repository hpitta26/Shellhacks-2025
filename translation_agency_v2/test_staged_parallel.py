#!/usr/bin/env python3
"""
Test Content-Agnostic Dynamic Staged Parallel Translation
=========================================================
RECOMMENDED TEST: Fully content-agnostic translation workflow that adapts to any website structure.

This test script imports the core workflow from agent.py and handles:
- Pre-processing: Setting up session state with content
- Execution: Running the content-agnostic workflow
- Post-processing: Converting results to final translated website structure

Usage: python test_staged_parallel.py
"""
import asyncio
import uuid
import json
from datetime import datetime
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

# Import the core workflow from agent.py
from agent import root_agent, content_batches, content_processor, APP_NAME

async def test_staged_parallel():
    """Test the content-agnostic staged parallel translation workflow"""
    
    print("🧪 Testing Content-Agnostic Staged Parallel Translation")
    print("=" * 50)
    
    # Use the imported workflow components
    batches = content_batches
    processor = content_processor
    
    num_batches = len(batches)
    print(f"📦 Processing all {num_batches} batches dynamically:")
    for i, batch in enumerate(batches):
        print(f"   {i+1}. {batch.batch_id}: {batch.group_name} ({batch.total_items} items)")
    
    # Setup session
    session_service = InMemorySessionService()
    session_id = str(uuid.uuid4())
    user_id = "test_user"
    
    # Dynamic initial state based on actual content structure
    brand_terms = processor.get_brand_terms()
    glossary_terms = processor.get_glossary_terms()
    
    initial_state = {
        "target_language": "Portuguese",
        "brand_terms": brand_terms,
        "glossary_terms": glossary_terms,
        "total_batches": num_batches,
        "content_metadata": {
            "total_groups": num_batches,
            "total_items": sum(batch.total_items for batch in batches),
            "group_info": {
                f"group_{i+1}": {
                    "name": batch.group_name,
                    "description": batch.group_description,
                    "items": batch.total_items,
                    "types": list(set(item.type for item in batch.items))
                } for i, batch in enumerate(batches)
            }
        }
    }
    
    # Add source content for each batch
    for i, batch in enumerate(batches):
        initial_state[f"source_text_{i+1}"] = batch.get_formatted_content()
        print(f"   📝 Added {batch.group_name}: {len(batch.get_formatted_content())} chars, {batch.total_items} items")
    
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
        state=initial_state
    )
    print(f"✅ Session created: {session.id}")
    
    # Setup standard runner (no rate limiting with billing enabled)
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    # Run test
    user_query = Content(role="user", parts=[Part(text="Please translate all content batches in staged parallel groups.")])
    
    print("🔄 Running staged parallel translation...")
    
    try:
        async for event in runner.run_async(
            user_id=user_id, 
            session_id=session.id, 
            new_message=user_query
        ):
            if event.is_final_response() and event.content:
                print(f"✅ Stage completed by {event.author}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Check final state
    final_session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session.id
    )
    
    if final_session:
        state = final_session.state if isinstance(final_session.state, dict) else final_session.state.to_dict()
        print(f"\n📊 Final State:")
        translation_keys = [k for k in state.keys() if k.startswith('translation_')]
        print(f"✅ Completed translations: {len(translation_keys)}/{num_batches}")
        for key in sorted(translation_keys):
            value = state[key]
            preview = value[:60] + "..." if len(value) > 60 else value
            print(f"   {key}: {preview}")
        
        # Post-process translations to create proper output structure
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Use the imported processor
        original_content = processor.content_data
        
        # Create translated version - exact copy of original structure
        translated_content = json.loads(json.dumps(original_content))  # Deep copy
        translated_content["website_metadata"]["language"] = "pt"
        translated_content["website_metadata"]["locale"] = "pt-BR"
        
        # First, mark all translatable values as "NOT TRANSLATED"
        for group_key, group_data in translated_content["pages"].items():
            if group_key == "name":
                continue
            if isinstance(group_data, dict):
                for item_key, item_data in group_data.items():
                    if item_key == "meta_data":
                        continue
                    if isinstance(item_data, dict) and "value" in item_data:
                        item_data["value"] = "NOT TRANSLATED"
        
        print(f"\n🔄 Post-processing translations...")
        
        # Parse each structured JSON translation and fill in the values
        for i, batch in enumerate(batches, 1):  # All 9 batches
            translation_key = f"translation_{i}"
            if translation_key in state:
                translation_data = state[translation_key]
                
                # Handle both string (JSON) and dict formats
                if isinstance(translation_data, str):
                    try:
                        translation_json = json.loads(translation_data)
                    except json.JSONDecodeError:
                        print(f"   ⚠️  Batch {i}: Invalid JSON format")
                        continue
                elif isinstance(translation_data, dict):
                    translation_json = translation_data
                else:
                    print(f"   ⚠️  Batch {i}: Unexpected data type: {type(translation_data)}")
                    continue
                
                # Extract items from structured output
                if "items" not in translation_json:
                    print(f"   ⚠️  Batch {i}: Missing 'items' in translation output")
                    continue
                
                # Fill in translated values in the exact original structure
                group_key = f"group_{i}"
                if group_key in translated_content["pages"]:
                    items = translation_json["items"]
                    
                    # Get all translatable keys in this group (excluding meta_data)
                    translatable_keys = [k for k in translated_content["pages"][group_key].keys() 
                                       if k != "meta_data" and isinstance(translated_content["pages"][group_key][k], dict) 
                                       and "value" in translated_content["pages"][group_key][k]]
                    
                    # Fill in each translated value
                    for item_idx, translated_item in enumerate(items):
                        if item_idx < len(translatable_keys):
                            # Use the actual key from the original structure
                            actual_key = translatable_keys[item_idx]
                            # Keep original type, just replace value
                            translated_content["pages"][group_key][actual_key]["value"] = translated_item["value"]
                            print(f"   ✅ {group_key}.{actual_key}: {translated_item['value'][:40]}...")
                        else:
                            print(f"   ⚠️  {group_key}: More translations than available keys (item {item_idx + 1})")
                    
                    print(f"   📊 {group_key}: Filled {len(items)} values into {len(translatable_keys)} keys")
        
        # Save both raw translations and processed structure
        raw_output_file = f"raw_translations_{timestamp}.json"
        processed_output_file = f"translated_website_{timestamp}.json"
        
        # Raw translations
        raw_results = {
            "metadata": {
                "timestamp": timestamp,
                "target_language": "Portuguese",
                "total_batches": num_batches,
                "workflow_type": "dynamic_staged_parallel_test"
            },
            "raw_translations": {key: state[key] for key in sorted(translation_keys)}
        }
        
        with open(raw_output_file, 'w', encoding='utf-8') as f:
            json.dump(raw_results, f, indent=2, ensure_ascii=False)
        
        # Processed structure
        with open(processed_output_file, 'w', encoding='utf-8') as f:
            json.dump(translated_content, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Files saved:")
        print(f"   📄 Raw translations: {raw_output_file}")
        print(f"   🌐 Processed website: {processed_output_file}")
        print(f"   📊 Structure matches original with translated values")

if __name__ == "__main__":
    asyncio.run(test_staged_parallel())
