"""
Semantic Diff Parser
Uses LLM to parse git diff and extract semantic changes for pipeline diagrams
"""

import json
import openai
from typing import Dict, List
import os


# Fuel Proxy URL for OpenAI API
FUEL_PROXY_URL = "https://api-beta.fuelix.ai"


def generate_semantic_diff_context(diff_output: str, api_key: str) -> Dict:
    """
    Use LLM to parse git diff and extract semantic changes
    
    Args:
        diff_output: Raw git diff output
        api_key: OpenAI API key
        
    Returns:
        Dictionary with semantic diff information:
        {
            "changes": [
                {
                    "component": "Chunking",
                    "type": "config_update",
                    "field": "chunk_size",
                    "old_value": "1000",
                    "new_value": "1500",
                    "impact": "Description of impact",
                    "affected_nodes": ["node_id1", "node_id2"]
                },
                ...
            ],
            "summary": "Overall summary of changes",
            "changed_files": ["file1.py", "file2.js"],
            "impact_assessment": "low|medium|high"
        }
    """
    if not diff_output or not diff_output.strip():
        return {
            "changes": [],
            "summary": "No changes detected",
            "changed_files": [],
            "impact_assessment": "none"
        }
    
    # Truncate if too large (to fit in context window)
    max_diff_length = 15000
    if len(diff_output) > max_diff_length:
        diff_output = diff_output[:max_diff_length] + "\n\n... (diff truncated for length)"
    
    prompt = f"""
Analyze this git diff and extract semantic changes relevant to a data pipeline architecture diagram.

FOCUS ON:
1. Configuration changes (chunk sizes, model names, API endpoints, database names, etc.)
2. New/removed pipeline steps or components
3. Changes to data flow or processing logic
4. Infrastructure changes (databases, storage, vector DBs, APIs)
5. Algorithm or method changes (e.g., switching from one text splitter to another)

IGNORE:
- Documentation changes (.md files)
- Comments-only changes
- Formatting/whitespace changes
- Import statement reordering (unless new libraries added)

For each meaningful change, identify:
- **component**: Which pipeline component is affected (e.g., "Chunking", "Embedding", "Vector DB", "Storage", "Ingestion", "Processing")
- **type**: Type of change (config_update, method_change, new_component, removed_component, flow_change)
- **field**: Specific field/parameter that changed (e.g., "chunk_size", "model", "namespace")
- **old_value**: Previous value (if applicable, use "N/A" if new)
- **new_value**: New value (use "N/A" if removed)
- **impact**: Brief description of what this means for the pipeline
- **affected_nodes**: List of likely node identifiers that would be affected (use lowercase, underscores, e.g., ["chunking", "text_splitting", "embedding_generation"])

COMPONENT CATEGORIES (use these standardized names):
- Ingestion: Reading/loading data from sources
- Chunking: Text splitting, document chunking
- Embedding: Generating embeddings, vector representations
- Vector DB: Pinecone, Turbopuffer, Weaviate, etc.
- Storage: GCS, S3, file storage, buckets
- Database: Firestore, MongoDB, SQL databases
- Processing: Data transformation, parsing
- Cache: Pickle files, intermediate storage
- API: External API calls, services

Git Diff:
```
{diff_output}
```

Output ONLY valid JSON in this exact format (no markdown, no code blocks):
{{
  "changes": [
    {{
      "component": "Chunking",
      "type": "config_update",
      "field": "chunk_size",
      "old_value": "1000",
      "new_value": "1500",
      "impact": "Larger chunks may improve context retention but increase token usage",
      "affected_nodes": ["chunking", "text_splitting"]
    }}
  ],
  "summary": "Brief overall summary of all changes",
  "changed_files": ["list", "of", "changed", "files"],
  "impact_assessment": "low"
}}

Impact assessment should be: "low" (<20% of pipeline affected), "medium" (20-50%), "high" (>50%), or "none" (no meaningful changes).
"""
    
    try:
        client = openai.OpenAI(
            api_key=api_key,
            base_url=FUEL_PROXY_URL
        )
        
        print("🤖 Analyzing diff with LLM for semantic understanding...")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            seed=42
        )
        
        content = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        semantic_diff = json.loads(content)
        
        # Validate structure
        if "changes" not in semantic_diff:
            semantic_diff["changes"] = []
        if "summary" not in semantic_diff:
            semantic_diff["summary"] = "Changes detected"
        if "changed_files" not in semantic_diff:
            semantic_diff["changed_files"] = []
        if "impact_assessment" not in semantic_diff:
            semantic_diff["impact_assessment"] = "medium"
        
        print(f"✅ Semantic analysis complete: {len(semantic_diff['changes'])} changes identified")
        print(f"📊 Impact assessment: {semantic_diff['impact_assessment']}")
        
        return semantic_diff
        
    except json.JSONDecodeError as e:
        print(f"⚠️  Failed to parse LLM response as JSON: {e}")
        print(f"Response content: {content[:500]}")
        # Fallback to empty result
        return {
            "changes": [],
            "summary": "Error parsing semantic diff",
            "changed_files": [],
            "impact_assessment": "unknown"
        }
    except Exception as e:
        print(f"⚠️  Error during semantic diff parsing: {e}")
        # Fallback to empty result
        return {
            "changes": [],
            "summary": f"Error: {str(e)}",
            "changed_files": [],
            "impact_assessment": "unknown"
        }


def save_semantic_diff(semantic_diff: Dict, output_path: str = "semantic_diff_context.json"):
    """
    Save semantic diff to JSON file
    
    Args:
        semantic_diff: Semantic diff dictionary
        output_path: Path to save JSON file
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(semantic_diff, f, indent=2)
        print(f"💾 Semantic diff saved to {output_path}")
    except Exception as e:
        print(f"⚠️  Error saving semantic diff: {e}")


if __name__ == "__main__":
    # Test the semantic diff parser
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python semantic_diff_parser.py <api_key>")
        sys.exit(1)
    
    api_key = sys.argv[1]
    
    # Test with sample diff
    sample_diff = """
diff --git a/chunking.py b/chunking.py
index 1234567..abcdefg 100644
--- a/chunking.py
+++ b/chunking.py
@@ -10,7 +10,7 @@ from langchain.text_splitter import RecursiveCharacterTextSplitter
 
 def split_documents(documents):
     text_splitter = RecursiveCharacterTextSplitter(
-        chunk_size=1000,
+        chunk_size=1500,
-        chunk_overlap=200
+        chunk_overlap=300
     )
     return text_splitter.split_documents(documents)

diff --git a/embedding.py b/embedding.py
index 2345678..bcdefgh 100644
--- a/embedding.py
+++ b/embedding.py
@@ -5,7 +5,7 @@ from langchain.embeddings import OpenAIEmbeddings
 
 def generate_embeddings():
     embeddings = OpenAIEmbeddings(
-        model="text-embedding-3-small"
+        model="text-embedding-3-large"
     )
     return embeddings
"""
    
    print("Testing Semantic Diff Parser...")
    print("="*80)
    
    result = generate_semantic_diff_context(sample_diff, api_key)
    
    print("\n" + "="*80)
    print("SEMANTIC DIFF RESULT:")
    print("="*80)
    print(json.dumps(result, indent=2))
    
    save_semantic_diff(result)
