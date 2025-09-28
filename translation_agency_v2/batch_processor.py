#!/usr/bin/env python3
"""
Batch Processor for Website Content Translation
Programmatically splits website content into translation batches
"""
import json
from typing import List, Dict, Any
from dataclasses import dataclass  
@dataclass
class TranslationItem:
   """Individual item to be translated"""
   id: str
   type: str  # header, content, button
   content: str
   context: str
   group_id: str
   group_name: str
   original_length: int = 0


@dataclass
class TranslationBatch:
   """A batch of items to be translated together"""
   batch_id: str
   group_id: str
   group_name: str
   group_description: str
   items: List[TranslationItem]
   total_items: int
  
   def get_batch_context(self) -> str:
       """Generate context string for the batch"""
       return f"Group: {self.group_name} - {self.group_description}"
  
   def get_source_texts(self) -> List[str]:
       """Get list of source texts to translate"""
       return [item.content for item in self.items]
  
   def get_formatted_content(self) -> str:
       """Get formatted content for translation prompt"""
       formatted_items = []
       for item in self.items:
           formatted_items.append(f"[{item.type.upper()}] {item.content}")
       return "\n".join(formatted_items)


class ContentBatchProcessor:
   """Processes website content into translation batches"""
  
   def __init__(self, content_file_path: str):
       self.content_file_path = content_file_path
       self.content_data = None
       self.batches = []
      
   def load_content(self) -> Dict[str, Any]:
       """Load content from JSON file"""
       with open(self.content_file_path, 'r', encoding='utf-8') as f:
           self.content_data = json.load(f)
       return self.content_data
  
   def create_batches(self) -> List[TranslationBatch]:
       """
       Create translation batches by group
      
       Each group is translated together to maintain contextual meaning
       and coherence within related content.
       """
       if not self.content_data:
           self.load_content()
          
       return self._create_batches_by_group()
  
   def _create_batches_by_group(self) -> List[TranslationBatch]:
       """Create one batch per content group"""
       batches = []
      
       # Navigate through the new structure: pages -> groups
       pages = self.content_data.get('pages', {})
      
       # Iterate through all groups (group_1, group_2, etc.)
       for group_key, group_data in pages.items():
           if group_key == 'name':  # Skip the page name field
               continue
              
           if not isinstance(group_data, dict) or 'meta_data' not in group_data:
               continue
              
           items = []
           group_name = group_data['meta_data']
          
           # Process all items in the group
           for item_key, item_data in group_data.items():
               if item_key == 'meta_data':  # Skip metadata
                   continue
                  
               if isinstance(item_data, dict) and 'type' in item_data and 'value' in item_data:
                  
                   original_length = len(item_data['value'])


                   item = TranslationItem(
                       id=f"{group_key}_{item_key}",
                       type=item_data['type'],
                       content=item_data['value'],
                       context=f"{group_name} - {item_key}",
                       group_id=group_key,
                       group_name=group_name,
                       original_length=original_length
                   )
                   items.append(item)
          
           if items:  # Only create batch if there are items
               batch = TranslationBatch(
                   batch_id=f"batch_{group_key}",
                   group_id=group_key,
                   group_name=group_name,
                   group_description=group_name,
                   items=items,
                   total_items=len(items)
               )
               batches.append(batch)
      
       self.batches = batches
       return batches
  
  
   def get_batch_summary(self) -> Dict[str, Any]:
       """Get summary of created batches"""
       if not self.batches:
           return {"error": "No batches created yet"}
      
       summary = {
           "total_batches": len(self.batches),
           "total_items": sum(batch.total_items for batch in self.batches),
           "batches": []
       }
      
       for batch in self.batches:
           batch_info = {
               "batch_id": batch.batch_id,
               "group_name": batch.group_name,
               "items_count": batch.total_items,
               "item_types": {}
           }
          
           # Count item types in this batch
           for item in batch.items:
               batch_info["item_types"][item.type] = batch_info["item_types"].get(item.type, 0) + 1
          
           summary["batches"].append(batch_info)
      
       return summary
  
   def get_glossary_terms(self) -> Dict[str, str]:
       """Get glossary terms from content metadata"""
       if not self.content_data:
           self.load_content()
       # Return default glossary terms for poker content
       return {
           "grinders": "dedicated players",
           "GTO": "Game Theory Optimal",
           "ICM": "Independent Chip Model",
           "HH": "Hand History",
           "sims": "simulations"
       }
  
   def get_brand_terms(self) -> List[str]:
       """Get brand terms from content metadata"""
       if not self.content_data:
           self.load_content()
       # Return default brand terms for Octopi Poker
       return ["Octopi", "George", "Vault", "Trainer"]


# Example usage and testing
if __name__ == "__main__":
   # Initialize processor
   processor = ContentBatchProcessor("website_content.json")
  
   # Load content
   content = processor.load_content()
   print("✅ Loaded website content")
  
   # Count groups and items from the new structure
   pages = content.get('pages', {})
   total_groups = len([k for k in pages.keys() if k != 'name' and isinstance(pages[k], dict) and 'meta_data' in pages[k]])
   total_items = 0
   for group_key, group_data in pages.items():
       if group_key != 'name' and isinstance(group_data, dict) and 'meta_data' in group_data:
           total_items += len([k for k in group_data.keys() if k != 'meta_data' and isinstance(group_data[k], dict) and 'type' in group_data[k]])
  
   print(f"📊 Total groups: {total_groups}")
   print(f"📊 Total items: {total_items}")
  
   # Create batches by group (maintains contextual meaning)
   print("\n🔄 Creating batches by group...")
   batches = processor.create_batches()
  
   # Display batch summary
   summary = processor.get_batch_summary()
   print(f"\n📋 Batch Summary:")
   print(f"Total Batches: {summary['total_batches']}")
   print(f"Total Items: {summary['total_items']}")
  
   print("\n📦 Batch Details:")
   for i, batch in enumerate(batches, 1):
       print(f"\nBatch {i}: {batch.batch_id}")
       print(f"  Group: {batch.group_name}")
       print(f"  Description: {batch.group_description}")
       print(f"  Items: {batch.total_items}")
       print(f"  Context: {batch.get_batch_context()}")
      
       print("  Content Preview:")
       for item in batch.items[:2]:  # Show first 2 items
           print(f"    [{item.type.upper()}] {item.content[:50]}...")
       if batch.total_items > 2:
           print(f"    ... and {batch.total_items - 2} more items")
  
   # Show glossary and brand terms
   print(f"\n📚 Glossary Terms: {processor.get_glossary_terms()}")
   print(f"🏷️  Brand Terms: {processor.get_brand_terms()}")