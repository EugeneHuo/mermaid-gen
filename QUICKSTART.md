# Quick Start Guide - For Team Members

This guide helps you add automatic diagram generation to your repository in 5 minutes.

## Prerequisites

- ✅ Your repository is on GitHub
- ✅ You have access to the organization's `OPENAI_API_KEY` secret
- ✅ Your code is in Python, JavaScript, TypeScript, or Java

---

## Step 1: Add the Workflow File (2 minutes)

Create a new file in your repository:

**Path**: `.github/workflows/diagram.yml`

**Content**:
```yaml
name: Generate Architecture Diagram

on:
  push:
    branches: [main, develop]
    paths:
      - '**.py'
      - '**.js'
      - '**.ts'
      - '**.java'

jobs:
  generate-diagram:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Important for incremental updates
      
      - name: Generate/Update Diagram
        uses: EugeneHuo/mermaid-gen@v1.0.0
        with:
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          mode: auto
          debug: true
      
      - name: Commit diagram
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add diagram.html
          git diff --quiet && git diff --staged --quiet || \
            git commit -m "🤖 Auto-update architecture diagram [skip ci]"
          git push
```

---

## Step 2: Commit and Push (1 minute)

```bash
git add .github/workflows/diagram.yml
git commit -m "Add automatic diagram generation"
git push
```

---

## Step 3: Watch It Work! (2 minutes)

1. Go to your repository on GitHub
2. Click the "Actions" tab
3. You should see "Generate Architecture Diagram" running
4. Wait for it to complete (~1-2 minutes)
5. Check your repository - you'll see a new `diagram.html` file!

---

## Step 4: View Your Diagram

### Option 1: GitHub Pages (Recommended)
1. Go to Settings → Pages
2. Source: Deploy from a branch
3. Branch: main, folder: / (root)
4. Save
5. Visit: `https://your-org.github.io/your-repo/diagram.html`

### Option 2: Download and Open Locally
1. Download `diagram.html` from your repository
2. Open it in your browser
3. See your architecture diagram!

### Option 3: Use GitHub's HTML Preview
1. Go to https://htmlpreview.github.io/
2. Paste your diagram.html URL
3. View the rendered diagram

---

## Customization (Optional)

### Add Metadata to Your Diagram

Update the workflow to include pipeline information:

```yaml
- name: Generate/Update Diagram
  uses: EugeneHuo/mermaid-gen@v1.0.0
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
    mode: auto
    pipeline-name: "My Data Pipeline"
    pipeline-purpose: "Processes documents and generates embeddings"
    data-type: "PDF documents"
    data-source: "GCS bucket"
    use-case: "RAG system"
    team-owner: "Data Engineering Team"
    debug: true
```

### Change When It Runs

```yaml
# Run on every push
on:
  push:
    branches: [main]

# Run on pull requests too
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

# Run on schedule (daily at midnight)
on:
  schedule:
    - cron: '0 0 * * *'
  push:
    branches: [main]
```

---

## How It Works

### First Time (Full Mode)
1. Scans all your code files
2. Extracts structure and configuration
3. Generates a complete Mermaid diagram
4. Commits `diagram.html` to your repo

### Subsequent Times (Incremental Mode)
1. Detects what code changed (via git diff)
2. Identifies which diagram nodes are affected
3. Updates only those nodes
4. Preserves the rest of the diagram
5. Commits the updated `diagram.html`

**Result**: Fast updates that maintain diagram consistency!

---

## Understanding the Output

### Files Created

- **diagram.html** - Your architecture diagram (open in browser)
- **diff_context.txt** - Git diff used for incremental updates (debug mode)
- **incremental_update_debug.txt** - Detailed update information (debug mode)

### Action Summary

After each run, check the Actions tab for a summary:

```
📊 Mermaid Diagram Generation

- Mode: incremental
- Diagram: diagram.html
- Affected Nodes: 2
- Impact Level: low

✅ Diagram generation completed successfully!
```

---

## Troubleshooting

### "Missing API key" Error

**Problem**: The workflow can't find the OpenAI API key.

**Solution**: 
1. Ask your admin to add `OPENAI_API_KEY` to organization secrets
2. Or add it to your repository secrets:
   - Settings → Secrets and variables → Actions
   - New repository secret
   - Name: `OPENAI_API_KEY`
   - Value: `sk-...`

### "Permission denied" Error

**Problem**: The workflow can't push the diagram back to the repo.

**Solution**: Add permissions to the workflow:
```yaml
jobs:
  generate-diagram:
    runs-on: ubuntu-latest
    permissions:
      contents: write  # Add this line
```

### Diagram Not Updating

**Problem**: You made code changes but the diagram didn't update.

**Solution**: 
1. Check if you changed code files (`.py`, `.js`, etc.) not docs
2. Make sure the workflow ran (check Actions tab)
3. Try forcing a full regeneration:
   ```yaml
   with:
     force-full: true
   ```

### Diagram Shows Wrong Values

**Problem**: The diagram doesn't reflect your actual code.

**Solution**:
1. Delete `diagram.html` from your repo
2. Push the deletion
3. The next run will generate a fresh diagram

---

## Advanced Usage

### Multiple Diagrams

Generate different diagrams for different parts of your codebase:

```yaml
jobs:
  backend-diagram:
    steps:
      - uses: EugeneHuo/mermaid-gen@v1.0.0
        with:
          path: ./backend
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
      - run: mv diagram.html backend-diagram.html
  
  frontend-diagram:
    steps:
      - uses: EugeneHuo/mermaid-gen@v1.0.0
        with:
          path: ./frontend
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
      - run: mv diagram.html frontend-diagram.html
```

### Conditional Updates

Only update diagram if code in specific directories changed:

```yaml
on:
  push:
    paths:
      - 'src/pipeline/**'
      - 'src/data/**'
```

### Use Outputs in Next Steps

```yaml
- uses: EugeneHuo/mermaid-gen@v1.0.0
  id: diagram
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}

- name: Notify team
  if: steps.diagram.outputs.mode-used == 'incremental'
  run: |
    echo "Updated ${{ steps.diagram.outputs.affected-nodes }} nodes"
    echo "Impact: ${{ steps.diagram.outputs.impact-level }}"
```

---

## Getting Help

- 📖 [Full Documentation](https://github.com/EugeneHuo/mermaid-gen/blob/main/ACTION_README.md)
- 💡 [Examples](https://github.com/EugeneHuo/mermaid-gen/tree/main/examples)
- 🐛 [Report Issues](https://github.com/EugeneHuo/mermaid-gen/issues)
- 💬 Ask in your team's Slack/Teams channel

---

## What's Next?

1. ✅ Set up the workflow (you just did this!)
2. 📊 View your first diagram
3. 🔄 Make code changes and watch it update
4. 🎨 Customize with metadata
5. 📢 Share with your team!

**That's it!** Your repository now has automatic architecture diagrams. 🎉
