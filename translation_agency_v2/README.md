# Parallel Batch Translation Workflow

A professional translation workflow using Google ADK with parallel batch processing, review, regeneration, and refinement.

## 🏗️ Architecture

```
StagedParallelTranslationWorkflow
├── StagedParallelTranslator (Sequential)
│   ├── ParallelGroup1 (Parallel: Navigation, Hero, Testimonials)
│   ├── ParallelGroup2 (Parallel: Store, Coaching, Vault)  
│   └── ParallelGroup3 (Parallel: Tutorials, Ask George, Footer)
├── ParallelBatchReviewer (Reviews all 9 translations)
├── BatchRegenerationAgent (Regenerates flagged batches)
└── FinalRefinementAgent (Final polish & consistency)
```

## 🚀 How to Test

### Recommended: Staged Parallel Test
```bash
python test_staged_parallel.py
```
- Tests 6 batches in 2 staged groups
- Demonstrates core parallel functionality
- Minimal API usage

### Full End-to-End Test
```bash
python test_parallel_batch_translation.py
```
- Tests complete workflow with all 9 batches
- Includes review, regeneration, and refinement
- ⚠️ Uses significant API calls

### Utility Demos
```bash
# Show batch processing logic
python demo_batch_strategies.py

# Production website translation workflow
python website_translation_workflow.py
```

## 📁 Core Files

- `agent.py` - Main ADK agents and workflow definition
- `batch_processor.py` - Content batching and processing logic
- `website_content.json` - Website content structured for batch processing

## 🔧 Key Features

- **Parallel Execution**: 3 batches processed simultaneously per stage
- **Race Condition Prevention**: Unique output keys for each batch
- **API Rate Limit Handling**: Staged approach prevents overwhelming API
- **Professional Quality**: Review → Regeneration → Refinement pipeline
- **State Management**: Dynamic instructions with contextual awareness
