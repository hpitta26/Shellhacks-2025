#!/usr/bin/env python3
"""
Test Complete Parallel Batch Translation Workflow
=================================================
FULL END-TO-END TEST: Tests the complete workflow with all 9 batches including:
- Staged parallel translation (3 groups of 3 agents each)
- Batch review and flagging
- Regeneration of flagged batches
- Final refinement and polish

WARNING: This test uses significant API calls and may hit rate limits.
For basic testing, use test_staged_parallel.py instead.

Usage: python test_parallel_batch_translation.py
"""
import asyncio
import os
import uuid
from batch_processor import ContentBatchProcessor
from agent import root_agent, APP_NAME
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
    raise ValueError("GOOGLE_API_KEY environment variable is required. Please set it with: export GOOGLE_API_KEY='your_api_key' or add it to .env file")

async def test_parallel_batch_translation():
    """Test the complete parallel batch translation workflow"""
    
    print("🚀 Testing Parallel Batch Translation Workflow")
    print("=" * 60)
    
    # Create batch processor and get all batches
    processor = ContentBatchProcessor("website_content.json")
    processor.load_content()
    batches = processor.create_batches()
    
    print(f"📦 Processing {len(batches)} batches in parallel:")
    for i, batch in enumerate(batches, 1):
        print(f"   {i}. {batch.batch_id}: {batch.group_name} ({batch.total_items} items)")
    
    # Setup session
    session_service = InMemorySessionService()
    session_id = str(uuid.uuid4())
    user_id = "parallel_test_user"
    
    # Prepare initial state with all batch content
    initial_state = {
        "target_language": "Portuguese",
        "glossary_terms": processor.get_glossary_terms(),
        "brand_terms": processor.get_brand_terms(),
        "batch_status": "pending"
    }
    
    # Add source text for each batch group
    for i, batch in enumerate(batches, 1):
        group_id = f"group_{i}"
        initial_state[f"source_text_{group_id}"] = batch.get_formatted_content()
        print(f"   📝 Added source_text_{group_id}: {len(batch.get_formatted_content())} chars")
    
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
        state=initial_state
    )
    print(f"✅ Session created: {session.id}")
    print(f"📊 Initial state keys: {list(session.state.keys())}")
    
    # Setup runner
    runner = Runner(
        agent=root_agent,
        session_service=session_service,
        app_name=APP_NAME,
    )
    
    # Create user query
    user_query = Content(
        role="user",
        parts=[
            Part(text=f"Please translate all website content batches into Portuguese using the parallel workflow.")
        ]
    )
    
    print(f"\n🔄 Running parallel translation workflow...")
    print("-" * 50)
    
    final_response = ""
    try:
        async for event in runner.run_async(user_id=user_id, session_id=session.id, new_message=user_query):
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text
                print(f"\n🎯 Final Response Preview: {final_response[:200]}...")
    except Exception as e:
        print(f"❌ Error during parallel translation: {e}")
        return
    
    # Get final session state
    final_session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session.id
    )
    
    print(f"\n📊 Final Session State Analysis:")
    print("-" * 50)
    if final_session:
        state_dict = final_session.state if isinstance(final_session.state, dict) else final_session.state.to_dict()
        
        # Check parallel translation results
        translation_keys = [key for key in state_dict.keys() if key.startswith('translation_group_')]
        print(f"✅ Parallel translations completed: {len(translation_keys)}/9")
        for key in sorted(translation_keys):
            value = state_dict[key]
            preview = value[:100] + "..." if len(value) > 100 else value
            print(f"   {key}: {preview}")
        
        # Check review results
        if 'batch_review_results' in state_dict:
            print(f"\n📋 Review Results:")
            review = state_dict['batch_review_results']
            print(f"   {review[:200]}...")
        
        # Check regeneration results
        if 'regenerated_translations' in state_dict:
            print(f"\n🔄 Regeneration Results:")
            regen = state_dict['regenerated_translations']
            print(f"   {regen[:200]}...")
        
        # Check final translations
        if 'final_translations' in state_dict:
            print(f"\n🏆 Final Translations:")
            final = state_dict['final_translations']
            print(f"   {final[:300]}...")
        
        print(f"\n📈 Total State Keys: {len(state_dict)}")
        
    # Save translations to file for verification
    if final_session:
        state_dict = final_session.state if isinstance(final_session.state, dict) else final_session.state.to_dict()
        
        # Create output file with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"translation_results_{timestamp}.json"
        
        # Prepare translation results for file output
        translation_results = {
            "metadata": {
                "timestamp": timestamp,
                "target_language": state_dict.get("target_language", "Portuguese"),
                "total_batches": 9,
                "workflow_status": "completed"
            },
            "individual_translations": {},
            "review_results": state_dict.get("batch_review_results", "No review available"),
            "regenerated_translations": state_dict.get("regenerated_translations", "No regeneration needed"),
            "final_translations": state_dict.get("final_translations", "No final translations available")
        }
        
        # Extract individual translations
        for i in range(1, 10):
            key = f"translation_group_{i}"
            if key in state_dict:
                translation_results["individual_translations"][f"group_{i}"] = state_dict[key]
        
        # Save to file
        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(translation_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Translation results saved to: {output_file}")
        print(f"📄 File contains:")
        print(f"   - Individual translations for all 9 groups")
        print(f"   - Review results and feedback")
        print(f"   - Regeneration results")
        print(f"   - Final polished translations")
    
    print(f"\n🏁 Parallel Batch Translation Test Complete!")
    return final_response

if __name__ == "__main__":
    asyncio.run(test_parallel_batch_translation())
