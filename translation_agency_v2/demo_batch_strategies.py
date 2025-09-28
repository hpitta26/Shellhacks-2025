#!/usr/bin/env python3
"""
Demo: Group-Based Batch Processing
Shows how content is batched by groups to maintain contextual meaning
"""
from batch_processor import ContentBatchProcessor

def demo_batch_processing():
    """Demonstrate group-based batch processing"""
    
    processor = ContentBatchProcessor("website_content.json")
    processor.load_content()
    
    print("🌐 Website Content Batch Processing Demo")
    print("=" * 50)
    
    print(f"\n📦 Batch Strategy: by_group")
    print(f"Description: One batch per content group - maintains contextual meaning and coherence")
    print("-" * 40)
    
    batches = processor.create_batches()
    summary = processor.get_batch_summary()
    
    print(f"Total Batches: {summary['total_batches']}")
    print(f"Total Items: {summary['total_items']}")
    
    print(f"\n📦 Batch Details:")
    for batch_info in summary['batches']:
        print(f"  • {batch_info['batch_id']}: {batch_info['items_count']} items")
        type_counts = ", ".join([f"{count} {type_name}" for type_name, count in batch_info['item_types'].items()])
        print(f"    Types: {type_counts}")
    
    print(f"\n📚 Available Translation Assets:")
    print(f"Glossary Terms: {processor.get_glossary_terms()}")
    print(f"Brand Terms: {processor.get_brand_terms()}")

if __name__ == "__main__":
    demo_batch_processing()
