# Mermaid Diagram Generator - Incremental Update Feature

## 🚀 New Feature: Smart Incremental Updates

The diagram generator now supports **intelligent incremental updates** using Parse-Filter-Update logic. When you make small code changes, only the affected parts of your diagram are regenerated, preserving the rest as a "Locked Template."

## Quick Start

### Local Usage

```bash
# Auto-detect mode (recommended)
python main_incremental.py . --mode auto

# Force incremental update
python main_incremental.py . --mode incremental --debug

# Force full regeneration
python main_incremental.py . --force-full
```

### GitHub Actions (Automatic)

The workflow automatically runs on every push and intelligently chooses between:
- **Incremental Mode**: When `diagram.html` exists (updates only changed nodes)
- **Full Mode**: When no diagram exists (generates complete diagram)

## How It Works

```
Code Change → Git Diff → Parse Diagram → Map Changes → Update Nodes → Save
     ↓            ↓            ↓              ↓             ↓          ↓
  commit      analyze      extract        identify      targeted    diagram.html
              changes      structure      affected      LLM call    updated
                                          nodes
```

### Example: Chunk Size Change

**Before**:
```python
chunk_size = 1000
```

**After**:
```python
chunk_size = 1500
```

**Result**:
- ✅ Only the chunking node is updated
- ✅ All other nodes remain unchanged
- ✅ Diagram structure preserved
- ✅ Faster execution (1 node vs entire diagram)

## Key Benefits

1. **⚡ Faster Updates**: Only regenerate what changed
2. **🔒 Stable Structure**: Preserves diagram layout and connections
3. **🎯 Targeted Changes**: Updates only affected nodes
4. **🤖 Automatic Fallback**: Falls back to full regen when needed
5. **📊 Impact Analysis**: Shows what percentage of diagram is affected

## Architecture

### Core Modules

| Module | Purpose |
|--------|---------|
| `mermaid_parser.py` | Parse existing Mermaid diagrams into structured format |
| `change_mapper.py` | Map git diff changes to specific diagram nodes |
| `workflow_utils.py` | CI/CD integration and repository state analysis |
| `incremental_update.py` | Orchestrate the Parse-Filter-Update workflow |
| `main_incremental.py` | Enhanced CLI with incremental mode support |

### Workflow Files

- `.github/workflows/generate-diagram.yml` - GitHub Actions workflow with conditional logic

## Usage Examples

### 1. Basic Incremental Update

```bash
# Make code changes
vim chunking.py  # Change chunk_size from 1000 to 1500

# Run incremental update
python main_incremental.py . --mode incremental

# Output:
# 🔄 Using INCREMENTAL update mode...
# ✅ Low impact (5.0%) - using incremental update
# 📊 Existing diagram: 20 nodes, 25 connections
# 🎯 Affected nodes: ['C']
# 📈 Impact: low (5.0%)
# ✅ Incremental mode active - updating 1 node(s)
```

### 2. With Debug Output

```bash
python main_incremental.py . --mode incremental --debug

# Creates:
# - diff_context.txt: Full git diff output
# - incremental_update_debug.txt: Detailed analysis
```

### 3. Force Full Regeneration

```bash
# When you want to rebuild everything
python main_incremental.py . --force-full
```

### 4. With Metadata

```bash
python main_incremental.py . \
  --mode incremental \
  --pipeline-name "Document Embedding Pipeline" \
  --pipeline-purpose "Processes PDFs for RAG system" \
  --data-type "PDF documents" \
  --debug
```

## GitHub Actions Setup

### 1. Add API Key Secret

```
Repository Settings → Secrets → New repository secret
Name: OPENAI_API_KEY
Value: sk-your-key-here
```

### 2. Enable Workflow Permissions

```
Repository Settings → Actions → General
✅ Read and write permissions
```

### 3. Push Changes

```bash
git add .
git commit -m "feat: update chunk size"
git push
```

The workflow will:
1. **Analyze** repository state
2. **Detect** incremental mode (if diagram.html exists)
3. **Update** only affected nodes
4. **Commit** updated diagram
5. **Upload** artifacts for review

## Change Impact Levels

| Impact | Percentage | Action |
|--------|------------|--------|
| None | 0% | Skip update |
| Low | < 20% | ✅ Incremental |
| Medium | 20-50% | ✅ Incremental |
| High | 50-80% | ⚠️ Consider full |
| Full | > 80% | ❌ Full regen |

## Fallback Scenarios

The system automatically falls back to full regeneration when:

- ❌ No existing diagram found
- ❌ Not a git repository
- ❌ Cannot parse existing diagram
- ❌ Cannot generate git diff
- ❌ Impact exceeds 50% threshold
- ❌ `--force-full` flag is used

## File Structure

```
mermaid-gen/
├── main_incremental.py          # Enhanced CLI with incremental support
├── mermaid_parser.py             # Diagram parsing logic
├── change_mapper.py              # Change-to-node mapping
├── workflow_utils.py             # CI/CD helpers
├── incremental_update.py         # Incremental update orchestration
├── .github/
│   └── workflows/
│       └── generate-diagram.yml  # GitHub Actions workflow
├── INCREMENTAL_UPDATE_GUIDE.md   # Detailed documentation
└── README_INCREMENTAL.md         # This file
```

## Debug Files

When using `--debug` flag:

### diff_context.txt
```
================================================================================
GIT DIFF CONTEXT - Incremental Diagram Update
================================================================================
Base Reference: HEAD~1
Current Reference: HEAD

diff --git a/chunking.py b/chunking.py
-chunk_size = 1000
+chunk_size = 1500
```

### incremental_update_debug.txt
```
================================================================================
INCREMENTAL UPDATE DEBUG
================================================================================
Affected Nodes: ['C']
Impact: low (5.0%)

Node C:
  Content: • Size: 1000<br/>• Overlap: 200
  Subgraph: Step2_Chunking
  Keywords: ['chunk', 'chunking', 'chunk_size']
```

## Advanced Configuration

### Adjust Impact Threshold

Edit `workflow_utils.py`:
```python
# Default: 50% threshold
use_incremental, reason = should_use_incremental_mode(path, threshold=0.5)

# More tolerant: 70% threshold
use_incremental, reason = should_use_incremental_mode(path, threshold=0.7)
```

### Add Custom Keywords

Edit `change_mapper.py`:
```python
STEP_KEYWORDS = {
    'chunking': ['chunk', 'split', 'textsplitter'],
    'embedding': ['embedding', 'embed', 'openai'],
    'my_step': ['custom', 'keyword'],  # Add your step
}
```

## Comparison: Full vs Incremental

### Full Mode
```bash
python main.py .
```
- ✅ Generates complete diagram
- ✅ Best for new projects
- ⏱️ Slower (processes all files)
- 💰 Higher token usage

### Incremental Mode
```bash
python main_incremental.py . --mode incremental
```
- ✅ Updates only changed nodes
- ✅ Best for existing projects
- ⚡ Faster (processes only changes)
- 💰 Lower token usage
- 🔒 Preserves diagram structure

## Troubleshooting

### "No changes detected"
```bash
# Make sure you have uncommitted changes
git status

# Or committed changes since last run
git log -1
```

### "Could not parse existing diagram"
```bash
# Delete and regenerate
rm diagram.html
python main_incremental.py . --mode full
```

### "Fallback to full regeneration"
```bash
# Check why with debug flag
python main_incremental.py . --mode incremental --debug
cat incremental_update_debug.txt
```

## Best Practices

1. **Commit diagram.html** - Required for incremental mode
2. **Use --debug locally** - Understand what's being updated
3. **Review artifacts** - Check GitHub Actions artifacts
4. **Test before push** - Run locally first
5. **Force full when needed** - Use `--force-full` for major changes

## Migration from Original main.py

### Before (Original)
```bash
python main.py . --mode incremental
```
- Simple git diff detection
- Regenerates entire diagram
- No structure preservation

### After (Enhanced)
```bash
python main_incremental.py . --mode incremental
```
- Parse-Filter-Update logic
- Updates only affected nodes
- Preserves diagram structure
- Automatic fallback

## Documentation

- **Quick Start**: This file (README_INCREMENTAL.md)
- **Detailed Guide**: INCREMENTAL_UPDATE_GUIDE.md
- **Original README**: README.md
- **Usage Guide**: USAGE_GUIDE.md

## Support

For issues or questions:
1. Check `incremental_update_debug.txt` (with --debug flag)
2. Review INCREMENTAL_UPDATE_GUIDE.md
3. Open an issue on GitHub
4. Use `/reportbug` command

## License

Same as main project

---

**Ready to try it?**

```bash
# Install dependencies
pip install -r requirements.txt

# Run with auto-detection
python main_incremental.py . --mode auto --debug

# Check the results
cat incremental_update_debug.txt
```
