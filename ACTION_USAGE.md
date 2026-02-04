# Using Mermaid Diagram Generator as a GitHub Action

This repository can be used as a **custom GitHub Action** in any of your projects to automatically generate or update Mermaid architecture diagrams.

## Quick Start

### Basic Usage

Add this to your workflow file (e.g., `.github/workflows/diagram.yml`):

```yaml
name: Generate Diagram

on:
  push:
    branches: [main]

jobs:
  generate-diagram:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Required for incremental mode
      
      - name: Generate Mermaid Diagram
        uses: EugeneHuo/mermaid-gen@main
        with:
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          mode: auto
      
      - name: Commit diagram
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add diagram.html
          git diff --staged --quiet || git commit -m "🤖 Update diagram"
          git push
```

## Complete Example with All Options

```yaml
name: Generate Architecture Diagram

on:
  push:
    branches: [main, develop]
  pull_request:
  workflow_dispatch:

jobs:
  generate-diagram:
    runs-on: ubuntu-latest
    permissions:
      contents: write  # Required to commit changes
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Full history for git diff
      
      - name: Generate/Update Diagram
        id: diagram
        uses: EugeneHuo/mermaid-gen@main
        with:
          # Required
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          
          # Optional - Mode selection
          mode: auto  # auto, new, incremental, or full
          path: .     # Path to analyze
          
          # Optional - Pipeline metadata
          pipeline-name: "Document Embedding Pipeline"
          pipeline-purpose: "Processes PDFs and generates embeddings for RAG"
          data-type: "PDF documents"
          data-source: "GCS bucket gs://my-docs"
          use-case: "RAG system for customer support"
          team-owner: "Data Engineering Team"
          
          # Optional - Flags
          include-comments: true
          debug: true
          force-full: false
      
      - name: Display results
        run: |
          echo "Mode used: ${{ steps.diagram.outputs.mode-used }}"
          echo "Diagram path: ${{ steps.diagram.outputs.diagram-path }}"
          echo "Affected nodes: ${{ steps.diagram.outputs.affected-nodes }}"
          echo "Impact level: ${{ steps.diagram.outputs.impact-level }}"
      
      - name: Commit and push
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add diagram.html diff_context.txt incremental_update_debug.txt || true
          git diff --staged --quiet || git commit -m "🤖 Update diagram [${{ steps.diagram.outputs.mode-used }} mode]"
          git push
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: diagram-files
          path: |
            diagram.html
            diff_context.txt
            incremental_update_debug.txt
          if-no-files-found: ignore
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `openai-api-key` | ✅ Yes | - | OpenAI API key for GPT-4o |
| `path` | No | `.` | Path to your project folder |
| `mode` | No | `auto` | Scan mode: `auto`, `new`, `incremental`, or `full` |
| `pipeline-name` | No | - | Name of the pipeline |
| `pipeline-purpose` | No | - | What this pipeline does |
| `data-type` | No | - | Type of data being processed |
| `data-source` | No | - | Where the data comes from |
| `use-case` | No | - | What the pipeline is used for |
| `team-owner` | No | - | Team or person responsible |
| `include-comments` | No | `false` | Include code comments in analysis |
| `debug` | No | `false` | Enable debug output |
| `force-full` | No | `false` | Force full regeneration |

## Outputs

| Output | Description |
|--------|-------------|
| `diagram-path` | Path to the generated `diagram.html` file |
| `mode-used` | The mode that was actually used (`full` or `incremental`) |
| `affected-nodes` | Number of nodes affected (incremental mode only) |
| `impact-level` | Impact level of changes (`none`, `low`, `medium`, `high`, `full`) |

## Usage Examples

### Example 1: Auto-detect Mode (Recommended)

```yaml
- uses: EugeneHuo/mermaid-gen@main
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
    mode: auto
```

**Behavior:**
- If `diagram.html` exists → Uses incremental mode
- If no diagram exists → Uses full mode
- Automatically chooses the best approach

### Example 2: Force Incremental Update

```yaml
- uses: EugeneHuo/mermaid-gen@main
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
    mode: incremental
    debug: true
```

**Behavior:**
- Always attempts incremental update
- Falls back to full if not possible
- Creates debug files for analysis

### Example 3: Full Regeneration

```yaml
- uses: EugeneHuo/mermaid-gen@main
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
    mode: full
```

**Behavior:**
- Always regenerates complete diagram
- Ignores existing diagram
- Useful for major refactors

### Example 4: With Metadata

```yaml
- uses: EugeneHuo/mermaid-gen@main
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
    pipeline-name: "ML Training Pipeline"
    pipeline-purpose: "Trains and deploys ML models"
    data-type: "Training datasets"
    data-source: "S3 bucket"
    use-case: "Model deployment automation"
    team-owner: "ML Platform Team"
```

**Behavior:**
- Adds metadata to diagram
- Enhances diagram with context
- Better documentation

### Example 5: Conditional Execution

```yaml
- name: Check for Python changes
  id: changes
  uses: dorny/paths-filter@v2
  with:
    filters: |
      python:
        - '**.py'

- name: Generate diagram
  if: steps.changes.outputs.python == 'true'
  uses: EugeneHuo/mermaid-gen@main
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
    mode: incremental
```

**Behavior:**
- Only runs when Python files change
- Saves API calls and execution time
- More efficient CI/CD

### Example 6: Multiple Repositories

```yaml
# In repo A
- uses: EugeneHuo/mermaid-gen@main
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
    path: ./service-a

# In repo B
- uses: EugeneHuo/mermaid-gen@main
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
    path: ./service-b
```

**Behavior:**
- Same action, different repositories
- Centralized maintenance
- Consistent diagram generation

## Version Pinning

### Use Specific Version (Recommended for Production)

```yaml
# Pin to specific commit
- uses: EugeneHuo/mermaid-gen@abc123def

# Pin to tag/release
- uses: EugeneHuo/mermaid-gen@v1.0.0

# Pin to branch (auto-updates)
- uses: EugeneHuo/mermaid-gen@main
```

## Setup Requirements

### 1. Add OpenAI API Key Secret

In your target repository:

```
Settings → Secrets and variables → Actions → New repository secret
Name: OPENAI_API_KEY
Value: sk-your-api-key-here
```

### 2. Enable Workflow Permissions

```
Settings → Actions → General → Workflow permissions
✅ Read and write permissions
```

### 3. Create Workflow File

Create `.github/workflows/diagram.yml` in your repository with the examples above.

## Advanced Patterns

### Pattern 1: PR Comments with Diagram

```yaml
- name: Generate diagram
  id: diagram
  uses: EugeneHuo/mermaid-gen@main
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
    mode: incremental
    debug: true

- name: Comment on PR
  if: github.event_name == 'pull_request'
  uses: actions/github-script@v6
  with:
    script: |
      const fs = require('fs');
      const diagram = fs.readFileSync('diagram.html', 'utf8');
      
      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: `## 📊 Diagram Updated\n\n**Mode**: ${{ steps.diagram.outputs.mode-used }}\n**Impact**: ${{ steps.diagram.outputs.impact-level }}\n**Affected Nodes**: ${{ steps.diagram.outputs.affected-nodes }}`
      });
```

### Pattern 2: Scheduled Regeneration

```yaml
on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:

jobs:
  regenerate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: EugeneHuo/mermaid-gen@main
        with:
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          force-full: true  # Full regeneration weekly
```

### Pattern 3: Multi-Project Monorepo

```yaml
jobs:
  generate-diagrams:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [api, worker, frontend]
    steps:
      - uses: actions/checkout@v3
      
      - name: Generate diagram for ${{ matrix.service }}
        uses: EugeneHuo/mermaid-gen@main
        with:
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          path: ./services/${{ matrix.service }}
          pipeline-name: "${{ matrix.service }} Service"
      
      - name: Rename diagram
        run: mv diagram.html diagram-${{ matrix.service }}.html
```

## Troubleshooting

### Issue: "Action not found"

**Solution:** Make sure the action repository is public or you have access to it.

```yaml
# Correct format
uses: EugeneHuo/mermaid-gen@main

# Not: uses: ./mermaid-gen
```

### Issue: "OPENAI_API_KEY not set"

**Solution:** Add the secret to your repository settings.

```yaml
with:
  openai-api-key: ${{ secrets.OPENAI_API_KEY }}  # Must be in secrets
```

### Issue: "Permission denied" when pushing

**Solution:** Enable workflow write permissions.

```
Settings → Actions → General → Workflow permissions
✅ Read and write permissions
```

### Issue: "No changes detected" in incremental mode

**Solution:** Make sure you have `fetch-depth: 0` in checkout step.

```yaml
- uses: actions/checkout@v3
  with:
    fetch-depth: 0  # Required for git diff
```

## Best Practices

1. **Pin to specific version** in production workflows
2. **Use auto mode** for most cases
3. **Enable debug** when troubleshooting
4. **Upload artifacts** for review
5. **Add PR comments** to show impact
6. **Use conditional execution** to save resources
7. **Test locally first** with `main_incremental.py`

## Local Testing

Before using in GitHub Actions, test locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Test the action logic
export OPENAI_API_KEY=sk-your-key
python main_incremental.py . --mode auto --debug

# Review outputs
cat incremental_update_debug.txt
```

## Support

- **Documentation**: See INCREMENTAL_UPDATE_GUIDE.md
- **Issues**: Open an issue on GitHub
- **Examples**: Check `.github/workflows/generate-diagram.yml`

## License

Same as main project
