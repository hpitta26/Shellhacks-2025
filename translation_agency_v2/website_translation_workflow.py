#!/usr/bin/env python3
"""
Website Translation Workflow
Integrates batch processor with translation agents for complete website translation
"""
import asyncio
import os
import uuid
import json
from typing import Dict, List, Any
from batch_processor import ContentBatchProcessor, TranslationBatch
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
    raise ValueError("GOOGLE_API_KEY environment variable is required")

class WebsiteTranslationWorkflow:
    """Manages the complete website translation workflow"""
    
    def __init__(self, content_file: str = "website_content.json"):
        self.content_file = content_file
        self.processor = ContentBatchProcessor(content_file)
        self.session_service = InMemorySessionService()
        self.runner = None
        self.translation_results = {}
        
    async def setup_runner(self):
        """Initialize the ADK runner"""
        self.runner = Runner(
            agent=root_agent,
            app_name=APP_NAME,
            session_service=self.session_service
        )
        print("✅ Translation runner initialized")
    
    async def translate_website(self, target_language: str = "Portuguese") -> Dict[str, Any]:
        """
        Translate entire website content
        
        Content is batched by groups to maintain contextual meaning and coherence.
        Each group contains related content that should be translated together.
        
        Args:
            target_language: Target language for translation
            
        Returns:
            Dictionary with translation results for each batch
        """
        print(f"🌐 Starting website translation to {target_language}")
        print(f"📦 Using group-based batching to maintain contextual meaning")
        
        # Setup runner if not already done
        if not self.runner:
            await self.setup_runner()
        
        # Load content and create batches by group
        self.processor.load_content()
        batches = self.processor.create_batches()
        
        print(f"\n📊 Created {len(batches)} translation batches")
        
        # Get global glossary and brand terms
        glossary_terms = self.processor.get_glossary_terms()
        brand_terms = self.processor.get_brand_terms()
        
        # Process each batch
        results = {
            "target_language": target_language,
            "batch_strategy": batch_strategy,
            "total_batches": len(batches),
            "glossary_terms": glossary_terms,
            "brand_terms": brand_terms,
            "batch_results": []
        }
        
        for i, batch in enumerate(batches, 1):
            print(f"\n🔄 Processing Batch {i}/{len(batches)}: {batch.batch_id}")
            print(f"   Group: {batch.group_name}")
            print(f"   Items: {batch.total_items}")
            
            try:
                batch_result = await self._translate_batch(batch, target_language, 
                                                         glossary_terms, brand_terms)
                results["batch_results"].append(batch_result)
                print(f"✅ Batch {i} completed successfully")
                
            except Exception as e:
                print(f"❌ Batch {i} failed: {str(e)}")
                batch_result = {
                    "batch_id": batch.batch_id,
                    "status": "error",
                    "error": str(e),
                    "items": []
                }
                results["batch_results"].append(batch_result)
        
        # Save results
        await self._save_results(results)
        
        return results
    
    async def _translate_batch(self, batch: TranslationBatch, target_language: str,
                             glossary_terms: Dict[str, str], brand_terms: List[str]) -> Dict[str, Any]:
        """Translate a single batch using the translation workflow"""
        
        # Create session for this batch
        session_id = str(uuid.uuid4())
        user_id = f"batch_user_{batch.batch_id}"
        
        # Prepare batch content for translation
        batch_content = self._format_batch_for_translation(batch)
        
        # Create session with batch-specific state
        session = await self.session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
            state={
                "source_text": batch_content,
                "target_language": target_language,
                "batch_size": "small" if batch.total_items <= 3 else "large",
                "glossary_terms": glossary_terms,
                "brand_terms": brand_terms,
                "batch_status": "pending",
                "batch_context": batch.get_batch_context(),
                "batch_id": batch.batch_id
            }
        )
        
        print(f"   📋 Session created: {session.id}")
        
        # Create user query for translation
        user_query = Content(
            role="user",
            parts=[Part(text=f"Please translate this {batch.group_name} content to {target_language} following the professional workflow.")]
        )
        
        # Run translation workflow
        final_response = None
        async for event in self.runner.run_async(user_id=user_id, session_id=session_id, new_message=user_query):
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text
        
        # Get final session state
        final_session = await self.session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id
        )
        
        # Parse translation results
        translated_items = self._parse_translation_results(batch, final_response, final_session)
        
        return {
            "batch_id": batch.batch_id,
            "group_name": batch.group_name,
            "status": "completed",
            "original_items": batch.total_items,
            "translated_items": len(translated_items),
            "final_translation": final_response,
            "session_state": final_session.state if final_session else {},
            "items": translated_items
        }
    
    def _format_batch_for_translation(self, batch: TranslationBatch) -> str:
        """Format batch content for translation prompt"""
        formatted_content = f"Content Group: {batch.group_name}\n"
        formatted_content += f"Context: {batch.group_description}\n\n"
        
        for item in batch.items:
            formatted_content += f"[{item.type.upper()}] {item.content}\n"
        
        return formatted_content
    
    def _parse_translation_results(self, batch: TranslationBatch, translation: str, 
                                 final_session) -> List[Dict[str, Any]]:
        """Parse translation results back to individual items"""
        # For now, return the full translation
        # In a more sophisticated version, you could parse individual items
        translated_items = []
        
        for i, item in enumerate(batch.items):
            translated_items.append({
                "original_id": item.id,
                "type": item.type,
                "original_content": item.content,
                "translated_content": f"[Translated] {item.content}",  # Placeholder
                "context": item.context
            })
        
        return translated_items
    
    async def _save_results(self, results: Dict[str, Any]):
        """Save translation results to file"""
        output_file = f"translation_results_{results['target_language'].lower()}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to {output_file}")
    
    def get_translation_summary(self, results: Dict[str, Any]) -> str:
        """Generate a summary of translation results"""
        total_batches = results['total_batches']
        completed_batches = sum(1 for batch in results['batch_results'] if batch['status'] == 'completed')
        failed_batches = total_batches - completed_batches
        
        summary = f"""
🌐 Website Translation Summary
================================
Target Language: {results['target_language']}
Batch Strategy: {results['batch_strategy']}

📊 Results:
- Total Batches: {total_batches}
- Completed: {completed_batches}
- Failed: {failed_batches}
- Success Rate: {(completed_batches/total_batches)*100:.1f}%

📚 Translation Assets:
- Glossary Terms: {len(results['glossary_terms'])}
- Brand Terms: {len(results['brand_terms'])}
"""
        return summary

# Example usage
async def main():
    """Example of running the complete website translation workflow"""
    
    # Initialize workflow
    workflow = WebsiteTranslationWorkflow()
    
    # Test batch processor first
    print("🧪 Testing batch processor...")
    processor = ContentBatchProcessor("website_content.json")
    processor.load_content()
    batches = processor.create_batches()
    
    print(f"✅ Created {len(batches)} batches")
    for batch in batches:
        print(f"   📦 {batch.batch_id}: {batch.total_items} items")
    
    # Uncomment to run full translation (requires API key)
    # print("\n🌐 Running translation workflow...")
    # results = await workflow.translate_website("Portuguese")
    # print(workflow.get_translation_summary(results))

if __name__ == "__main__":
    asyncio.run(main())
