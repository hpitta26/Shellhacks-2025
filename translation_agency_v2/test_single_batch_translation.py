#!/usr/bin/env python3
"""
Test Single Batch Translation
Tests the complete translation workflow with one batch
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

async def test_single_batch_translation():
    """Test translation of a single batch"""
    
    print("🚀 Testing Single Batch Translation")
    print("=" * 50)
    
    # Create batch processor and get first batch
    processor = ContentBatchProcessor("website_content.json")
    processor.load_content()
    batches = processor.create_batches()
    
    # Use the first batch (Navigation menu)
    test_batch = batches[0]
    print(f"📦 Testing batch: {test_batch.batch_id}")
    print(f"   Group: {test_batch.group_name}")
    print(f"   Items: {test_batch.total_items}")
    print(f"   Content: {test_batch.get_formatted_content()}")
    
    # Setup session
    session_service = InMemorySessionService()
    session_id = str(uuid.uuid4())
    user_id = "test_user"
    
    # Initial state for translation
    initial_state = {
        "source_text": test_batch.get_formatted_content(),
        "target_language": "Portuguese",
        "batch_size": "small" if test_batch.total_items <= 5 else "large",
        "glossary_terms": processor.get_glossary_terms(),
        "brand_terms": processor.get_brand_terms(),
        "batch_status": "pending",
        "batch_context": test_batch.get_batch_context()
    }
    
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
        state=initial_state
    )
    print(f"✅ Session created: {session.id}")
    
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
            Part(text=f"Please translate the {test_batch.group_name} content into Portuguese.")
        ]
    )
    
    print(f"\n🔄 Running translation workflow...")
    print("-" * 30)
    
    final_translation = ""
    try:
        async for event in runner.run_async(user_id=user_id, session_id=session.id, new_message=user_query):
            if event.is_final_response() and event.content and event.content.parts:
                final_translation = event.content.parts[0].text
                print(f"🎯 Translation Result: {final_translation}")
    except Exception as e:
        print(f"❌ Error during translation: {e}")
        return
    
    # Get final session state
    final_session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session.id
    )
    
    print(f"\n📊 Final Session State:")
    if final_session:
        state_dict = final_session.state if isinstance(final_session.state, dict) else final_session.state.to_dict()
        for key, value in state_dict.items():
            if isinstance(value, str) and len(value) > 100:
                print(f"   {key}: {value[:100]}...")
            else:
                print(f"   {key}: {value}")
    
    print(f"\n🏁 Single Batch Translation Test Complete!")
    return final_translation

if __name__ == "__main__":
    asyncio.run(test_single_batch_translation())
