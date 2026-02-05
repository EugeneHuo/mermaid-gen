# Semantic Diff Parsing Guide

## Overview

The Mermaid Diagram Generator now uses **LLM-powered semantic diff parsing** to intelligently understand code changes and update diagrams incrementally. This replaces the previous regex-based pattern matching with a more intelligent, context-aware approach.

---

## What is Semantic Diff Parsing?

Instead of using hardcoded regex patterns to detect changes, the system now:

1. **Extracts the full git diff** (excluding .md files)
2. **Sends it to GPT-4o** for semantic analysis
3. **Receives structured JSON** with meaningful change descriptions
4. **Maps changes to diagram nodes** using semantic understanding

---

## Key Benefits

### 🎯 **Intelligent Understanding**
- Understands the **meaning** of changes, not just pattern matching
- Recognizes relationships between code changes
- Identifies impact on pipeline architecture

### 🌐 **Language Agnostic**
- Works with Python, JavaScript, TypeScript, Java, Go, Ruby
- No need to maintain language-specific regex patterns

### 📊 **Better Node Mapping**
- LLM suggests which diagram nodes are affected
- Understands semantic relationships between components
- More accurate impact assessment

### 🔍 **Context Aware**
- Extracts configuration changes with context
- Understands why changes matter
- Provides human-readable summaries

---

## How It Works

### Step 1: Git Diff Extraction

```bash
# Extracts diff with 10 lines of context, excluding .md files
git diff HEAD~1 HEAD --unified=10 -- *.py *.js *.ts *.java *.go *.rb
```

**Exclusions:**
- `.md` files (documentation)
- Files matching `.gitignore` patterns

### Step 2: Semantic Analysis

The diff is sent to GPT-4o with a specialized prompt:

```python
{
  "changes": [
    {
      "component": "Chunking",
      "type": "config_update",
      "field": "chunk_size",
      "old_value": "1000",
      "new_value": "1500",
      "impact": "Larger chunks improve context but increase token usage",
      "affected_nodes": ["chunking", "text_splitting"]
    }
  ],
  "summary": "Updated chunking configuration",
  "changed_files": ["chunking.py"],
  "impact_assessment": "low"
}
```

### Step 3: Node Mapping

The `ChangeMapper` uses three strategies:

1. **LLM-Suggested Nodes**: Uses `affected_nodes` from semantic diff
2. **Component Mapping**: Maps component names to pipeline steps
3. **Field Matching**: Matches field names to node keywords

### Step 4: Incremental Update

Only affected nodes are updated while preserving:
- Node IDs
- Connections/edges
- Subgraph structure
- Unaffected nodes

---

## Configuration

### Enable Semantic Parsing

Semantic parsing is **enabled by default** when using incremental mode with an API key.

**Command Line:**
```bash
python main_incremental.py . --mode incremental
```

**GitHub Action:**
```yaml
- uses: EugeneHuo/mermaid-gen@main
  with:
    mode: 'incremental'  # or 'auto'
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

### Fallback to Regex

If API key is not provided, the system falls back to regex-based parsing:

```python
# In workflow_utils.py
if api_key:
    parsed_data = generate_semantic_diff_context(diff_output, api_key)
else:
    print("⚠️  No API key provided, falling back to regex parsing")
    parsed_data = parse_git_diff_output(diff_output)  # Legacy
```

---

## Semantic Diff Format

### Change Object Structure

```json
{
  "component": "Chunking|Embedding|Vector DB|Storage|Database|Processing|Cache|API|Ingestion",
  "type": "config_update|method_change|new_component|removed_component|flow_change",
  "field": "chunk_size|model|namespace|bucket|etc",
  "old_value": "previous value or N/A",
  "new_value": "new value or N/A",
  "impact": "Human-readable description of impact",
  "affected_nodes": ["list", "of", "node", "identifiers"]
}
```

### Component Categories

| Component | Description | Examples |
|-----------|-------------|----------|
| **Ingestion** | Reading/loading data | File readers, API clients |
| **Chunking** | Text splitting | RecursiveCharacterTextSplitter |
| **Embedding** | Vector generation | OpenAI embeddings, Cohere |
| **Vector DB** | Vector storage | Pinecone, Turbopuffer, Weaviate |
| **Storage** | File/object storage | GCS, S3, local files |
| **Database** | Document storage | Firestore, MongoDB |
| **Processing** | Data transformation | Parsers, transformers |
| **Cache** | Intermediate storage | Pickle files, Redis |
| **API** | External services | REST APIs, webhooks |

### Impact Assessment Levels

| Level | Percentage | Action |
|-------|-----------|--------|
| **none** | 0% | No changes detected |
| **low** | <20% | Use incremental update |
| **medium** | 20-50% | Use incremental update |
| **high** | >50% | Fall back to full regeneration |

---

## Examples

### Example 1: Configuration Change

**Git Diff:**
```diff
-chunk_size = 1000
+chunk_size = 1500
```

**Semantic Diff Output:**
```json
{
  "changes": [{
    "component": "Chunking",
    "type": "config_update",
    "field": "chunk_size",
    "old_value": "1000",
    "new_value": "1500",
    "impact": "Larger chunks may improve context retention",
    "affected_nodes": ["chunking", "text_splitting"]
  }],
  "summary": "Increased chunk size for better context",
  "impact_assessment": "low"
}
```

### Example 2: Model Change

**Git Diff:**
```diff
-model="text-embedding-3-small"
+model="text-embedding-3-large"
```

**Semantic Diff Output:**
```json
{
  "changes": [{
    "component": "Embedding",
    "type": "config_update",
    "field": "model",
    "old_value": "text-embedding-3-small",
    "new_value": "text-embedding-3-large",
    "impact": "Higher quality embeddings but increased cost",
    "affected_nodes": ["embedding", "embedding_generation"]
  }],
  "summary": "Upgraded to larger embedding model",
  "impact_assessment": "low"
}
```

### Example 3: New Component

**Git Diff:**
```diff
+from turbopuffer import TurboPuffer
+
+def store_in_vectordb(embeddings):
+    tp = TurboPuffer(namespace="production")
+    tp.upsert(embeddings)
```

**Semantic Diff Output:**
```json
{
  "changes": [{
    "component": "Vector DB",
    "type": "new_component",
    "field": "N/A",
    "old_value": "N/A",
    "new_value": "TurboPuffer",
    "impact": "Added vector database storage capability",
    "affected_nodes": ["vectordb", "storage", "turbopuffer"]
  }],
  "summary": "Added TurboPuffer vector database integration",
  "impact_assessment": "medium"
}
```

---

## Debugging

### Enable Debug Mode

```bash
python main_incremental.py . --mode incremental --debug
```

This creates two debug files:

1. **`semantic_diff_context.json`**: Raw semantic diff output
2. **`incremental_update_debug.txt`**: Full debug information

### Debug File Contents

**semantic_diff_context.json:**
```json
{
  "changes": [...],
  "summary": "...",
  "changed_files": [...],
  "impact_assessment": "low"
}
```

**incremental_update_debug.txt:**
```
================================================================================
INCREMENTAL UPDATE DEBUG
================================================================================

Affected Nodes: ['chunking', 'embedding']
Impact: low (15.0%)

================================================================================
EXISTING DIAGRAM:
================================================================================
flowchart TD
  ...

================================================================================
DIFF CONTEXT:
================================================================================
diff --git a/chunking.py b/chunking.py
...
```

---

## Cost Considerations

### LLM API Costs

- **Semantic parsing**: ~$0.01-0.05 per diff
- **Diagram update**: ~$0.10-0.30 per update
- **Total per incremental update**: ~$0.11-0.35

### Optimization Tips

1. **Use incremental mode**: Only for small changes (<50% impact)
2. **Batch commits**: Combine related changes in one commit
3. **Cache results**: Semantic diff is saved to JSON for reuse

---

## Troubleshooting

### Issue: Semantic parsing fails

**Symptoms:**
```
⚠️  Failed to parse LLM response as JSON
```

**Solution:**
- Check API key is valid
- Verify network connectivity
- Review diff size (max 15,000 characters)

### Issue: No changes detected

**Symptoms:**
```
⚠️  No code file changes detected
```

**Solution:**
- Ensure changes are in code files (.py, .js, .ts, etc.)
- Check that changes are committed to git
- Verify .md files are not the only changes

### Issue: Falls back to full regeneration

**Symptoms:**
```
⚠️  High impact (65.0%) - using full regeneration
```

**Solution:**
- This is expected for large changes
- Use `--force-full` to skip incremental check
- Consider breaking changes into smaller commits

---

## Advanced Usage

### Custom Component Mapping

Edit `semantic_diff_parser.py` to add custom component categories:

```python
COMPONENT CATEGORIES (use these standardized names):
- Ingestion: Reading/loading data from sources
- Chunking: Text splitting, document chunking
- YourCustomComponent: Your description
```

### Adjust Impact Threshold

Edit `workflow_utils.py` to change the threshold:

```python
# Default: 50% (0.5)
use_incremental, reason = should_use_incremental_mode(path, threshold=0.7)
```

### Disable Semantic Parsing

To use legacy regex parsing:

```python
# In workflow_utils.py
diff_output, diff_data = generate_diff_context(path, api_key=None)
```

---

## Comparison: Semantic vs. Regex

| Feature | Semantic (LLM) | Regex (Legacy) |
|---------|---------------|----------------|
| **Accuracy** | High - understands context | Low - pattern matching only |
| **Language Support** | All languages | Hardcoded patterns |
| **Maintenance** | Self-updating | Requires manual updates |
| **Cost** | ~$0.01-0.05 per diff | Free |
| **Speed** | 2-5 seconds | <1 second |
| **Context** | Full semantic understanding | Limited to patterns |

---

## Best Practices

1. ✅ **Use semantic parsing for production**: More accurate node mapping
2. ✅ **Enable debug mode initially**: Verify semantic diff quality
3. ✅ **Review semantic_diff_context.json**: Ensure changes are captured correctly
4. ✅ **Commit code changes separately from docs**: Avoid .md file noise
5. ✅ **Use meaningful commit messages**: Helps LLM understand intent

---

## Future Enhancements

- [ ] Support for multi-commit diffs
- [ ] Custom LLM model selection (GPT-4o-mini for cost savings)
- [ ] Semantic diff caching to reduce API calls
- [ ] Support for branch comparisons
- [ ] Integration with PR review workflows

---

## Related Documentation

- [Incremental Update Guide](INCREMENTAL_UPDATE_GUIDE.md)
- [Testing Guide](TESTING_GUIDE.md)
- [Action Usage](ACTION_USAGE.md)
