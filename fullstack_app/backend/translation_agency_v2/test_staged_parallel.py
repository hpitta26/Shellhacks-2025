#!/usr/bin/env python3
"""
Test Dynamic Staged Parallel Translation
=========================================
RECOMMENDED TEST: Tests the core staged parallel functionality with ALL batches dynamically.
Automatically detects the number of groups and creates the appropriate parallel structure.
Processes batches in groups of 3 to manage API rate limits effectively.

Usage: python test_staged_parallel.py
"""
import asyncio
import os
import uuid
import json
from typing import Dict, List
from pydantic import BaseModel, Field
from batch_processor import ContentBatchProcessor
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

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

# Define Pydantic schema for structured translation output
class TranslationItem(BaseModel):
    value: str = Field(description="The translated text value")

class TranslationOutput(BaseModel):
    items: List[TranslationItem] = Field(description="List of translated values in order")

async def test_staged_parallel():
    """Test staged parallel translation approach"""
    
    print("🧪 Testing Staged Parallel Translation")
    print("=" * 50)
    
    # Create batch processor and get batches
    processor = ContentBatchProcessor("website_content.json")
    processor.load_content()
    batches = processor.create_batches()
    
    num_batches = len(batches)
    agents_per_group = 3  # Process 3 batches in parallel per group to manage API limits
    num_parallel_groups = (num_batches + agents_per_group - 1) // agents_per_group  # Ceiling division
    
    print(f"📦 Processing all {num_batches} batches in {num_parallel_groups} staged parallel groups:")
    for i, batch in enumerate(batches):
        print(f"   {i+1}. {batch.batch_id}: {batch.group_name} ({batch.total_items} items)")
    
    # Dynamically create agents for all batches
    all_agents = []
    for i in range(num_batches):
        agent = LlmAgent(
            name=f"BatchTranslator_{i+1}",
            model="gemini-2.0-flash",
            instruction=lambda ctx, idx=i+1: f"""You are a professional translator. Translate ALL content items to Portuguese.

Source content to translate:
{ctx.state.get(f'source_text_{idx}', '')}

CRITICAL RULES:
1. Keep brand terms unchanged: Octopi, George, Vault, Trainer
2. Extract ONLY the text after format markers [BUTTON], [HEADER], [CONTENT] - DO NOT include the markers
3. Translate EVERY SINGLE item in the input - do not skip any
4. Return JSON with ALL translated values in order

Example input: "[BUTTON] The Vault\\n[BUTTON] My Hands\\n[CONTENT] Welcome"
Example output: {{"items": [{{"value": "O Vault"}}, {{"value": "Minhas Mãos"}}, {{"value": "Bem-vindo"}}]}}""",
            output_schema=TranslationOutput,
            output_key=f"translation_{i+1}"
        )
        all_agents.append(agent)
    
    # Group agents into parallel groups (3 agents per group)
    parallel_groups = []
    for group_idx in range(num_parallel_groups):
        start_idx = group_idx * agents_per_group
        end_idx = min(start_idx + agents_per_group, num_batches)
        group_agents = all_agents[start_idx:end_idx]
        
        parallel_group = ParallelAgent(
            name=f"ParallelGroup{group_idx+1}",
            sub_agents=group_agents,
            description=f"Translates batches {start_idx+1}-{end_idx} in parallel"
        )
        parallel_groups.append(parallel_group)
        print(f"   🔄 Group {group_idx+1}: Batches {start_idx+1}-{end_idx} ({len(group_agents)} agents)")
    
    # Create staged sequential agent with all parallel groups
    staged_agent = SequentialAgent(
        name="DynamicStagedParallelAgent",
        sub_agents=parallel_groups,
        description=f"Processes {num_batches} batches in {num_parallel_groups} staged parallel groups"
    )
    
    # Setup session
    session_service = InMemorySessionService()
    session_id = str(uuid.uuid4())
    user_id = "test_user"
    
    # Initial state with content for 6 batches
    initial_state = {
        "target_language": "Portuguese",
        "brand_terms": processor.get_brand_terms()
    }
    
    for i in range(num_batches):
        batch = batches[i]
        initial_state[f"source_text_{i+1}"] = batch.get_formatted_content()  # Full content, no truncation
    
    session = await session_service.create_session(
        app_name="dynamic_staged_parallel_app",
        user_id=user_id,
        session_id=session_id,
        state=initial_state
    )
    print(f"✅ Session created: {session.id}")
    
    # Setup standard runner (no rate limiting with billing enabled)
    runner = Runner(
        agent=staged_agent,
        app_name="dynamic_staged_parallel_app",
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
        app_name="dynamic_staged_parallel_app",
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
        
        # Load original structure
        processor = ContentBatchProcessor("website_content.json")
        processor.load_content()
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
