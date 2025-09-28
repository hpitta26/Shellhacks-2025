#!/usr/bin/env python3
"""
Test script to demonstrate the state management workflow
"""
import asyncio
import os
import uuid

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Try loading from current directory first, then parent directory
    if not load_dotenv():
        load_dotenv("../.env")
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment variables only")

from agent import root_agent, APP_NAME
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

# Configure Google AI API (not Vertex AI)
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"

# Verify API key is set
if not os.environ.get("GOOGLE_API_KEY"):
    raise ValueError("GOOGLE_API_KEY environment variable is required. Please set it with: export GOOGLE_API_KEY='your_api_key' or add it to .env file")

async def test_translation_workflow():
    """Test the complete translation workflow with state management"""
    
    print("🚀 Starting Translation Workflow Test")
    print("="*60)
    
    # Setup session and runner
    session_service = InMemorySessionService()
    
    SESSION_ID = str(uuid.uuid4())
    USER_ID = "test_user_123"
    
    # Create session with initial state
    initial_state = {
        "source_text": "Embrace your inner octopus and proudly wear the exclusive Octopi merch. Elegant and comfortable, it is made for grinders like you.",
        "target_language": "Portuguese",
        "batch_size": "small",
        "glossary_terms": {
            "grinders": "pessoas dedicadas",  # Established translation
            "Octopi": "Octopi"  # Brand name - keep as is
        },
        "brand_terms": ["Octopi"],
        "batch_status": "pending"
    }
    
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
        state=initial_state
    )
    
    print(f"✅ Session created with ID: {session.id}")
    print(f"📋 Initial State Keys: {list(session.state.keys())}")
    
    # Create runner
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    # Create user query
    user_query = Content(
        role="user",
        parts=[Part(text="Please translate the source text to Portuguese following the professional workflow.")]
    )
    
    print("\n🔄 Running Translation Workflow...")
    print("="*60)
    
    # Run the workflow
    final_response = None
    async for event in runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=user_query):
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text
            print(f"\n🎯 FINAL RESPONSE: {final_response}")
    
    # Get final session state
    final_session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )
    
    print("\n" + "="*60)
    print("📊 FINAL SESSION STATE ANALYSIS")
    print("="*60)
    
    if final_session:
        print(f"📋 Total State Keys: {len(final_session.state)}")
        for key, value in final_session.state.items():
            if isinstance(value, str) and len(value) > 100:
                print(f"  {key}: {value[:100]}...")
            else:
                print(f"  {key}: {value}")
        
        # Check if state communication worked
        print("\n🔍 STATE COMMUNICATION ANALYSIS:")
        print("-" * 40)
        
        if "current_translation" in final_session.state:
            print("✅ Translation saved to state")
        else:
            print("❌ Translation NOT saved to state")
            
        if "clarifying_questions" in final_session.state:
            print("✅ Clarifying questions mechanism available")
        else:
            print("⚠️  No clarifying questions found")
            
        if "batch_status" in final_session.state:
            print(f"✅ Batch status tracked: {final_session.state.get('batch_status')}")
        else:
            print("❌ Batch status NOT tracked")
            
        if "review_comments" in final_session.state:
            print("✅ Review comments mechanism available")
        else:
            print("⚠️  No review comments found")
    else:
        print("❌ Error: Could not retrieve final session state")
    
    print("\n" + "="*60)
    print("🏁 Translation Workflow Test Complete")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_translation_workflow())