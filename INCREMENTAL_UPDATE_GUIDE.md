# Incremental Update Guide

## Overview

The **Parse-Filter-Update** logic enables smart incremental updates to your Mermaid diagrams. Instead of regenerating the entire diagram when code changes, the system:

1. **Parses** the existing diagram to understand its structure
2. **Filters** changes using git diff to identify affected components
3. **Updates** only the nodes that need modification while preserving the rest as a "Locked Template"

## Architecture

```
┌─────────────────────────────────────┐
│  1. PARSE - Extract Diagram         │
│     mermaid_parser.py                │
│     • Reads diagram.html             │
│     • Parses Mermaid structure       │
│     • Builds node/edge map           │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  2. FILTER - Map Changes to Nodes   │
│     change_mapper.py                 │
│     • Generates diff_context.txt     │
│     • Analyzes code changes          │
│     • Maps to affected nodes         │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  3. UPDATE - Selective Regeneration  │
│     incremental_update.py            │
│     • Creates targeted LLM prompt    │
│     • Updates only affected nodes    │
│     • Preserves diagram structure    │
└─────────────────────────────────────┘
```

## Usage

### Local Development

#### Basic Incremental Update
```bash
# Auto-detect mode (uses incremental if diagram.html exists)
python main_incremental.py . --mode auto

# Force incremental mode
python main_incremental.py . --mode incremental

# Force full regeneration
python main_incremental.py . --mode full
# OR
python main_incremental.py . --force-full
```

#### With Debug Output
```bash
# See detailed incremental update process
python main_incremental.py . --mode incremental --debug

# This creates:
# - diff_context.txt: Git diff output
# - incremental_update_debug.txt: Detailed update analysis
```

#### With Metadata
```bash
python main_incremental.py . \
  --mode incremental \
  --pipeline-name "Document Embedding Pipeline" \
  --pipeline-purpose "Processes PDFs and generates embeddings" \
  --debug
```

### GitHub Actions Workflow

The workflow automatically runs on push/PR and intelligently chooses the mode:

#### Workflow Stages

**Stage 1: The Scout (analyze-state)**
- Checks if `diagram.html` exists
- Determines mode: `full` or `incremental`
- Counts changed files
- Outputs state for next job

**Stage 2: The Engine (generate-diagram)**
- Waits for Scout to complete
- Runs conditional steps based on mode:
  - **If mode == 'full'**: Generates complete diagram
  - **If mode == 'incremental'**: Updates only affected nodes
- Commits and pushes results
- Uploads artifacts

#### Setup

1. **Add OpenAI API Key to GitHub Secrets**
   ```
   Repository Settings → Secrets and variables → Actions → New repository secret
   Name: OPENAI_API_KEY
   Value: sk-your-api-key-here
   ```

2. **Enable Workflow Permissions**
   ```
   Repository Settings → Actions → General → Workflow permissions
   ✅ Read and write permissions
   ```

3. **Trigger the Workflow**
   - Push to `main` or `develop` branch
   - Create a pull request
   - Manual trigger via Actions tab

## How It Works

### 1. Parse Phase

**File**: `mermaid_parser.py`

Extracts the existing diagram structure:

```python
from mermaid_parser import extract_mermaid_from_html, parse_mermaid_diagram

# Extract Mermaid code from HTML
mermaid_code = extract_mermaid_from_html("diagram.html")

# Parse into structured format
diagram = parse_mermaid_diagram(mermaid_code)

# Access structure
print(f"Nodes: {len(diagram.nodes)}")
print(f"Edges: {len(diagram.edges)}")
print(f"Subgraphs: {list(diagram.subgraphs.keys())}")
```

**Parsed Structure**:
```python
{
  "nodes": {
    "A": {"type": "rect", "content": "• Item 1<br/>• Item 2", "subgraph": "Step1"},
    "B": {"type": "cylinder", "content": "Database", "subgraph": "Step2"}
  },
  "edges": [("A", "B")],
  "subgraphs": {"Step1": ["A"], "Step2": ["B"]},
  "metadata": {"title": "Pipeline Name"}
}
```

### 2. Filter Phase

**File**: `change_mapper.py`

Maps code changes to diagram nodes:

```python
from change_mapper import ChangeMapper, parse_git_diff_output

# Parse git diff
diff_data = parse_git_diff_output(diff_output)

# Map changes to nodes
mapper = ChangeMapper(diagram)
affected_nodes = mapper.map_changes_to_nodes(diff_data)

# Calculate impact
impact_level, percentage = calculate_change_impact(affected_nodes, len(diagram.nodes))
```

**Mapping Strategies**:

1. **File Name Matching**: `chunking.py` → nodes with "chunk" keyword
2. **Function Name Matching**: `generate_embeddings()` → nodes with "embedding" keyword
3. **Config Changes**: `chunk_size=1500` → nodes with "chunk_size" in content
4. **Pattern Matching**: Regex patterns for specific config changes

**Example**:
```python
# If this diff is detected:
-chunk_size = 1000
+chunk_size = 1500

# The mapper identifies:
affected_nodes = ["C"]  # Node C contains chunking config
impact = "low (10% of nodes)"
```

### 3. Update Phase

**File**: `incremental_update.py`

Generates targeted LLM prompt:

```python
from incremental_update import process_incremental_update

use_incremental, prompt, mode_info = process_incremental_update(
    path=".",
    debug=True,
    metadata_section=metadata
)

if use_incremental:
    # Send targeted prompt to LLM
    # Only updates affected nodes
    print(f"Updating {len(mode_info['affected_nodes'])} nodes")
else:
    # Fallback to full regeneration
    print(f"Reason: {mode_info['fallback_reason']}")
```

**Targeted Prompt Structure**:
```
EXISTING DIAGRAM (LOCKED TEMPLATE):
[Full current diagram]

AFFECTED NODES: C, D
Node C: Chunking configuration
Node D: Embedding model

CODE CHANGES:
-chunk_size = 1000
+chunk_size = 1500

INSTRUCTIONS:
1. Keep ALL nodes and connections exactly as shown
2. ONLY update nodes C and D with new values
3. Output the complete updated diagram
```

## Change Impact Levels

The system calculates impact to decide between incremental and full regeneration:

| Impact Level | Percentage | Action |
|--------------|------------|--------|
| **None** | 0% | No changes, skip update |
| **Low** | < 20% | ✅ Use incremental mode |
| **Medium** | 20-50% | ✅ Use incremental mode |
| **High** | 50-80% | ⚠️ Consider full regeneration |
| **Full** | > 80% | ❌ Force full regeneration |

**Threshold**: Default is 50% (configurable in `workflow_utils.py`)

## Fallback Mechanisms

The system automatically falls back to full regeneration if:

1. ❌ No existing `diagram.html` found
2. ❌ Not a git repository
3. ❌ Cannot parse existing diagram
4. ❌ Cannot generate git diff
5. ❌ Impact exceeds threshold (>50%)
6. ❌ `--force-full` flag is set

## Debug Output

### diff_context.txt
```
================================================================================
GIT DIFF CONTEXT - Incremental Diagram Update
================================================================================

Base Reference: HEAD~1
Current Reference: HEAD

================================================================================
DIFF OUTPUT:
================================================================================

diff --git a/chunking.py b/chunking.py
-chunk_size = 1000
+chunk_size = 1500
```

### incremental_update_debug.txt
```
================================================================================
INCREMENTAL UPDATE DEBUG
================================================================================

Affected Nodes: ['C', 'D']
Impact: low (15.0%)

================================================================================
EXISTING DIAGRAM:
================================================================================
flowchart TD
    subgraph Step2_Chunking
        C["• Size: 1000<br/>• Overlap: 200"]
    end
...

================================================================================
NODE CONTEXTS:
================================================================================
Node C:
  Content: • Size: 1000<br/>• Overlap: 200
  Subgraph: Step2_Chunking
  Keywords: ['chunk', 'chunking', 'chunk_size']
```

## Best Practices

### 1. Commit diagram.html
Always commit `diagram.html` to your repository so incremental mode can detect it.

### 2. Use Descriptive Commits
Clear commit messages help understand what changed:
```bash
git commit -m "feat: increase chunk size to 1500 for better context"
```

### 3. Review Debug Output
Use `--debug` flag to understand what's being updated:
```bash
python main_incremental.py . --mode incremental --debug
```

### 4. Test Locally First
Before pushing, test incremental updates locally:
```bash
# Make code changes
# Then run
python main_incremental.py . --mode incremental --debug
# Review incremental_update_debug.txt
```

### 5. Force Full Regeneration When Needed
If diagram structure changes significantly:
```bash
python main_incremental.py . --force-full
```

## Troubleshooting

### Issue: "No changes detected"
**Cause**: No git changes or all changes are in ignored files  
**Solution**: Make sure you've committed changes to tracked Python files

### Issue: "Could not parse existing diagram"
**Cause**: diagram.html is corrupted or has invalid Mermaid syntax  
**Solution**: Delete diagram.html and run with `--mode full`

### Issue: "Fallback to full regeneration"
**Cause**: Impact threshold exceeded or parsing error  
**Solution**: Check debug output to see reason, may be expected behavior

### Issue: Workflow fails with "OPENAI_API_KEY not found"
**Cause**: Secret not configured in GitHub  
**Solution**: Add OPENAI_API_KEY to repository secrets

## Advanced Configuration

### Adjust Impact Threshold

Edit `workflow_utils.py`:
```python
def should_use_incremental_mode(repo_path: str, threshold: float = 0.5):
    # Change threshold from 0.5 (50%) to 0.7 (70%)
    # Higher = more tolerant of changes before full regen
```

### Customize Change Mapping

Edit `change_mapper.py` to add custom keywords:
```python
STEP_KEYWORDS = {
    'chunking': ['chunk', 'split', 'textsplitter'],
    'embedding': ['embedding', 'embed', 'openai'],
    'my_custom_step': ['custom', 'special'],  # Add your keywords
}
```

### Modify Workflow Triggers

Edit `.github/workflows/generate-diagram.yml`:
```yaml
on:
  push:
    branches: [main, develop, feature/*]  # Add more branches
    paths:
      - '**.py'  # Only trigger on Python file changes
  schedule:
    - cron: '0 0 * * 0'  # Weekly regeneration
```

## Files Reference

| File | Purpose |
|------|---------|
| `mermaid_parser.py` | Parse existing Mermaid diagrams |
| `change_mapper.py` | Map code changes to diagram nodes |
| `workflow_utils.py` | CI/CD helper functions |
| `incremental_update.py` | Orchestrate incremental updates |
| `main_incremental.py` | Enhanced CLI with incremental support |
| `.github/workflows/generate-diagram.yml` | GitHub Actions workflow |

## Examples

### Example 1: Chunk Size Change

**Code Change**:
```python
# Before
chunk_size = 1000

# After
chunk_size = 1500
```

**Result**:
- Affected nodes: 1 (chunking node)
- Impact: Low (5%)
- Mode: Incremental ✅
- Only chunking node content updated

### Example 2: Model Change

**Code Change**:
```python
# Before
model = "text-embedding-3-small"

# After
model = "text-embedding-3-large"
```

**Result**:
- Affected nodes: 1 (embedding node)
- Impact: Low (5%)
- Mode: Incremental ✅
- Only embedding node content updated

### Example 3: Major Refactor

**Code Change**:
- Renamed 5 files
- Changed 10 functions
- Modified pipeline structure

**Result**:
- Affected nodes: 15
- Impact: High (75%)
- Mode: Full regeneration ⚠️
- Complete diagram rebuilt

## Support

For issues or questions:
1. Check debug output files
2. Review this guide
3. Open an issue on GitHub
4. Use `/reportbug` command in the tool
