# Mermaid Pipeline Documentation Generator - Usage Guide

## Overview

This tool automatically generates Mermaid flowchart diagrams from your codebase with intelligent mode detection for new and existing projects.

## Scan Modes

The tool supports **4 different scan modes** to optimize for different scenarios:

### 1. **Auto Mode** (Default - Recommended)
Automatically detects the best mode based on your project state:

```bash
python main.py /path/to/project
# or explicitly
python main.py /path/to/project --mode auto
```

**Detection Logic:**
- **Incremental Mode**: If git repository exists AND diagram.html exists
- **New Mode**: If git repository exists BUT no diagram.html
- **Full Mode**: If not a git repository

### 2. **New Project Mode** (`--mode new` or `-e`)
Scans only entry points and folder structure - ideal for initial project exploration.

```bash
# Using mode flag
python main.py /path/to/project --mode new

# Using shorthand flag
python main.py /path/to/project --entry-points-only
python main.py /path/to/project -e
```

**What it scans:**
- ✅ Project folder structure (directories, file types)
- ✅ Entry point files (main.py, index.ts, app.java, etc.)
- ✅ File count and distribution statistics
- ❌ Does NOT scan all files (saves time and tokens)

**Best for:**
- First-time analysis of a new codebase
- Quick overview of project structure
- Understanding entry points without full scan

### 3. **Incremental Mode** (`--mode incremental`)
Uses `git diff --name-only` to find changed files and only processes those.

```bash
python main.py /path/to/project --mode incremental
```

**What it scans:**
- ✅ Files modified since last commit (`git diff --name-only HEAD`)
- ✅ Untracked files (`git ls-files --others --exclude-standard`)
- ✅ Filters for supported file types (.py, .js, .ts, .java)
- ❌ Skips unchanged files

**Best for:**
- Updating diagrams after code changes
- Iterative development workflows
- Reducing processing time on large codebases

**Requirements:**
- Must be a git repository
- Git must be installed and accessible

### 4. **Full Mode** (`--mode full`)
Scans all files in the directory (original behavior).

```bash
python main.py /path/to/project --mode full
```

**What it scans:**
- ✅ All Python files (with AST parsing)
- ✅ All JS/TS/Java files (first 2000 chars)
- ✅ Respects .gitignore patterns
- ✅ Complete project analysis

**Best for:**
- Comprehensive documentation
- Non-git projects
- When you need complete context

---

## Usage Examples

### Example 1: New Project - Quick Overview
```bash
# Scan a new project you just cloned
python main.py C:\Projects\new-pipeline --entry-points-only

# Output:
# 📂 Scanning project at: C:\Projects\new-pipeline...
# 📋 Mode: new
# 🎯 Scanning entry points and project structure...
# 📦 Context size: 3,245 characters. Sending to LLM...
```

### Example 2: Existing Project - Incremental Update
```bash
# After making changes to your pipeline
python main.py C:\Projects\my-pipeline --mode incremental

# Output:
# 📂 Scanning project at: C:\Projects\my-pipeline...
# 🔍 Auto-detected: Existing project (using incremental mode)
# 📋 Mode: incremental
# 🔄 Detecting changed files with git diff...
# 📝 Found 2 changed file(s):
#    - src/chunking.py
#    - src/embedding.py
# 📦 Context size: 5,120 characters. Sending to LLM...
```

### Example 3: Auto-Detection
```bash
# Let the tool decide the best mode
python main.py C:\Projects\my-pipeline

# If it's a new git project:
# 🔍 Auto-detected: New git project (using entry points mode)

# If it's an existing project with diagram:
# 🔍 Auto-detected: Existing project (using incremental mode)

# If no changes detected:
# ✅ No changes detected. Diagram is up to date.
```

### Example 4: Full Scan with Metadata
```bash
python main.py C:\Projects\embedding-pipeline \
  --mode full \
  --pipeline-name "Document Embedding Pipeline" \
  --pipeline-purpose "Processes PDF documents and generates embeddings for RAG" \
  --data-type "PDF documents" \
  --data-source "GCS bucket: gs://company-docs" \
  --use-case "RAG system for customer support" \
  --team-owner "Data Engineering Team" \
  --include-comments \
  --debug
```

---

## Command-Line Options

### Required Arguments
| Argument | Description | Example |
|----------|-------------|---------|
| `path` | Path to your project folder | `C:\Projects\my-pipeline` |

### Optional Flags
| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--mode` | `-m` | Scan mode: auto, new, incremental, full | `auto` |
| `--entry-points-only` | `-e` | Force new project mode | `False` |
| `--include-comments` | `-c` | Include code comments in analysis | `False` |
| `--debug` | `-d` | Save AST parsing results to file | `False` |

### Metadata Options
| Option | Description | Example |
|--------|-------------|---------|
| `--pipeline-name` | Name of the pipeline | "Document Embedding Pipeline" |
| `--pipeline-purpose` | What the pipeline does | "Processes documents and generates embeddings" |
| `--data-type` | Type of data processed | "PDF documents" |
| `--data-source` | Where data comes from | "GCS bucket" |
| `--use-case` | What pipeline is used for | "RAG system" |
| `--team-owner` | Team or person responsible | "Data Engineering Team" |

### Environment Variables
| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | Yes |

---

## Entry Point Detection

The tool automatically detects common entry point files:

### Python
- `main.py`
- `app.py`
- `__main__.py`
- `run.py`
- `pipeline.py`

### JavaScript
- `index.js`
- `app.js`
- `main.js`
- `server.js`

### TypeScript
- `index.ts`
- `app.ts`
- `main.ts`
- `server.ts`

### Java
- `Main.java`
- `App.java`
- `Application.java`

---

## Git Integration

### Incremental Mode Requirements
1. **Git repository**: Project must be initialized with git
2. **Git installed**: `git` command must be available in PATH
3. **Committed changes**: Compares against HEAD (last commit)

### What Gets Detected
```bash
# Modified files
git diff --name-only HEAD

# Untracked files
git ls-files --others --exclude-standard
```

### Filtered File Types
Only processes:
- `.py` (Python)
- `.js` (JavaScript)
- `.ts` (TypeScript)
- `.java` (Java)

---

## Output Files

### diagram.html
The generated Mermaid flowchart visualization.

**Location**: Current working directory  
**Auto-opens**: Yes (in default browser)

### ast_debug_output.txt (with `--debug`)
Intermediate AST parsing results for inspection.

**Contains:**
- Total context size
- Source directory
- Parsed content sent to LLM
- Semantic structure extraction

---

## Workflow Recommendations

### For New Projects
```bash
# Step 1: Quick overview
python main.py /path/to/project -e

# Step 2: Review diagram, then do full scan if needed
python main.py /path/to/project --mode full
```

### For Active Development
```bash
# Daily workflow: Let auto-detection handle it
python main.py /path/to/project

# After making changes, it will automatically use incremental mode
```

### For Documentation Updates
```bash
# Force full regeneration with metadata
python main.py /path/to/project \
  --mode full \
  --pipeline-name "My Pipeline" \
  --pipeline-purpose "Description here" \
  --include-comments
```

---

## Troubleshooting

### "No changes detected" but I made changes
**Solution**: Commit your changes or use `--mode full`
```bash
git add .
git commit -m "Update pipeline"
python main.py /path/to/project
```

### "Not a git repository" error
**Solution**: Either initialize git or use `--mode full`
```bash
# Option 1: Initialize git
git init

# Option 2: Use full mode
python main.py /path/to/project --mode full
```

### Want to force full scan on git project
**Solution**: Use `--mode full` to override auto-detection
```bash
python main.py /path/to/project --mode full
```

---

## Performance Comparison

| Mode | Files Scanned | Typical Context Size | Best Use Case |
|------|---------------|---------------------|---------------|
| **New** | 1-5 entry points | 2-5K chars | Initial exploration |
| **Incremental** | 1-10 changed files | 3-15K chars | Daily updates |
| **Full** | All files | 20-100K chars | Complete documentation |

---

## Tips & Best Practices

1. **Use auto mode** for most scenarios - it's smart enough to choose the right approach
2. **Commit frequently** when using incremental mode for accurate change detection
3. **Add metadata** for better diagram context and team onboarding
4. **Use `--debug`** to inspect what's being sent to the LLM
5. **Entry points mode** is great for understanding unfamiliar codebases quickly
6. **Incremental mode** saves time and API costs on large projects

---

## API Key Setup

### Windows PowerShell
```powershell
$env:OPENAI_API_KEY="your-api-key-here"
```

### Linux/Mac
```bash
export OPENAI_API_KEY="your-api-key-here"
```

### .env File
```
OPENAI_API_KEY=your-api-key-here
```

---

## Support

For issues or questions, please refer to the main README.md or open an issue on GitHub.
