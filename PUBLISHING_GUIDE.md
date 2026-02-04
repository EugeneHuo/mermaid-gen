# Publishing Guide - Making This a GitHub Action for Your Organization

This guide explains how to publish this tool as a GitHub Action that your organization can use.

## Table of Contents
1. [Quick Start](#quick-start)
2. [Publishing Options](#publishing-options)
3. [Step-by-Step Publishing](#step-by-step-publishing)
4. [Using the Action in Workflows](#using-the-action-in-workflows)
5. [Versioning Strategy](#versioning-strategy)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Option 1: Use Directly from Your Repository (Recommended for Orgs)

Your team can use the action directly from your GitHub repository without publishing to the Marketplace:

```yaml
# In any repository's .github/workflows/diagram.yml
name: Generate Diagram

on:
  push:
    branches: [main, develop]

jobs:
  generate-diagram:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Important for incremental mode
      
      - uses: EugeneHuo/mermaid-gen@main
        with:
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          mode: auto
          debug: true
      
      - name: Commit diagram
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add diagram.html
          git diff --quiet && git diff --staged --quiet || git commit -m "Auto-update diagram [skip ci]"
          git push
```

---

## Publishing Options

### Option 1: Internal Organization Use (Recommended)
- ✅ Keep the repository private or public within your org
- ✅ Team members reference it directly: `EugeneHuo/mermaid-gen@main`
- ✅ No need to publish to Marketplace
- ✅ Full control over updates

### Option 2: GitHub Marketplace (Public)
- ✅ Available to everyone on GitHub
- ✅ Discoverable in Marketplace
- ❌ Repository must be public
- ❌ More maintenance overhead

### Option 3: GitHub Enterprise (Private Marketplace)
- ✅ Available only to your enterprise
- ✅ Can keep repository private
- ✅ Controlled distribution
- ❌ Requires GitHub Enterprise

---

## Step-by-Step Publishing

### For Internal Organization Use (Easiest)

#### Step 1: Push to GitHub
```bash
cd c:/Users/T773534/Desktop/mermaid-gen

# Make sure everything is committed
git add .
git commit -m "Add GitHub Action support"
git push origin main
```

#### Step 2: Create a Release (Optional but Recommended)
```bash
# Tag a version
git tag -a v1.0.0 -m "Initial release with incremental updates"
git push origin v1.0.0
```

#### Step 3: Share with Your Team
Send them this usage example:

```yaml
# .github/workflows/diagram.yml
- uses: EugeneHuo/mermaid-gen@v1.0.0  # Use specific version
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

**That's it!** Your team can now use it.

---

### For GitHub Marketplace (Public)

#### Step 1: Ensure Repository is Public
```bash
# Go to GitHub repository settings
# Settings → Danger Zone → Change visibility → Make public
```

#### Step 2: Add Required Files

The action already has:
- ✅ `action.yml` - Action definition
- ✅ `README.md` - Documentation
- ✅ `LICENSE` - Add if missing

Create a LICENSE file:
```bash
# Add MIT License (or your preferred license)
cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2026 EugeneHuo

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF
```

#### Step 3: Create a Release on GitHub

1. Go to your repository on GitHub
2. Click "Releases" → "Create a new release"
3. Tag version: `v1.0.0`
4. Release title: `v1.0.0 - Initial Release`
5. Description:
   ```markdown
   ## Features
   - 🔄 Incremental diagram updates (Parse-Filter-Update logic)
   - 🎯 Auto-detection of changes
   - 📊 Smart node mapping
   - 🤖 GPT-4o powered analysis
   - 📝 Comprehensive metadata support
   
   ## Usage
   See [ACTION_README.md](ACTION_README.md) for details.
   ```
6. ✅ Check "Publish this Action to the GitHub Marketplace"
7. Select primary category: "Continuous Integration"
8. Click "Publish release"

#### Step 4: Verify Marketplace Listing

- Go to https://github.com/marketplace
- Search for "Mermaid Diagram Generator"
- Your action should appear!

---

## Using the Action in Workflows

### Basic Usage

```yaml
name: Generate Diagram

on:
  push:
    branches: [main]

jobs:
  diagram:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - uses: EugeneHuo/mermaid-gen@v1.0.0
        with:
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

### Advanced Usage with All Options

```yaml
name: Generate Diagram

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  diagram:
    runs-on: ubuntu-latest
    permissions:
      contents: write  # Needed to commit diagram
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Important for incremental mode
          token: ${{ secrets.GITHUB_TOKEN }}
      
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
          include-comments: true
          debug: true
      
      - name: Commit and push diagram
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add diagram.html diff_context.txt incremental_update_debug.txt
          git diff --quiet && git diff --staged --quiet || \
            git commit -m "🤖 Auto-update diagram [skip ci]"
          git push
```

### Conditional Execution (Only on Code Changes)

```yaml
name: Generate Diagram

on:
  push:
    paths:
      - '**.py'
      - '**.js'
      - '**.ts'
      - '**.java'

jobs:
  diagram:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - uses: EugeneHuo/mermaid-gen@v1.0.0
        with:
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          mode: incremental
```

---

## Versioning Strategy

### Semantic Versioning

Use semantic versioning: `vMAJOR.MINOR.PATCH`

- **MAJOR** (v2.0.0): Breaking changes
- **MINOR** (v1.1.0): New features, backward compatible
- **PATCH** (v1.0.1): Bug fixes

### Creating New Versions

```bash
# Bug fix
git tag -a v1.0.1 -m "Fix: Correct git diff filtering"
git push origin v1.0.1

# New feature
git tag -a v1.1.0 -m "Feature: Add support for TypeScript"
git push origin v1.1.0

# Breaking change
git tag -a v2.0.0 -m "Breaking: Change output format"
git push origin v2.0.0
```

### Version References in Workflows

Users can reference:

```yaml
# Specific version (recommended for production)
- uses: EugeneHuo/mermaid-gen@v1.0.0

# Major version (gets latest v1.x.x)
- uses: EugeneHuo/mermaid-gen@v1

# Latest from main (not recommended for production)
- uses: EugeneHuo/mermaid-gen@main
```

---

## Setting Up Secrets

### For Repository Owners

1. Go to repository Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `OPENAI_API_KEY`
4. Value: Your OpenAI API key
5. Click "Add secret"

### For Organization-Wide Use

1. Go to Organization Settings → Secrets and variables → Actions
2. Click "New organization secret"
3. Name: `OPENAI_API_KEY`
4. Value: Your OpenAI API key
5. Repository access: Select repositories that can use it
6. Click "Add secret"

Now all repositories can use:
```yaml
openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

---

## Sharing with Your Team

### Create a Team Guide

Create a file in your organization's documentation:

```markdown
# Using the Mermaid Diagram Generator

## Quick Setup

1. Add this workflow to your repository:

   Create `.github/workflows/diagram.yml`:
   ```yaml
   name: Generate Diagram
   
   on:
     push:
       branches: [main]
   
   jobs:
     diagram:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
           with:
             fetch-depth: 0
         
         - uses: EugeneHuo/mermaid-gen@v1.0.0
           with:
             openai-api-key: ${{ secrets.OPENAI_API_KEY }}
         
         - run: |
             git config user.name "github-actions[bot]"
             git config user.email "github-actions[bot]@users.noreply.github.com"
             git add diagram.html
             git commit -m "Update diagram [skip ci]" || true
             git push
   ```

2. Make sure your repository has access to the `OPENAI_API_KEY` secret

3. Push code changes and watch the diagram update automatically!

## Documentation

- [Full Usage Guide](https://github.com/EugeneHuo/mermaid-gen/blob/main/ACTION_USAGE.md)
- [Examples](https://github.com/EugeneHuo/mermaid-gen/tree/main/examples)
```

---

## Troubleshooting

### Issue: "Action not found"

**Solution**: Make sure the repository is public or accessible to the organization.

```yaml
# Check the reference
- uses: EugeneHuo/mermaid-gen@v1.0.0  # Correct
- uses: EugeneHuo/mermaid-gen@main    # Also works
```

### Issue: "Missing API key"

**Solution**: Add the secret to repository or organization settings.

```yaml
# Make sure this is set
openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

### Issue: "Permission denied" when pushing

**Solution**: Add write permissions to the workflow.

```yaml
jobs:
  diagram:
    runs-on: ubuntu-latest
    permissions:
      contents: write  # Add this
```

### Issue: "Fetch depth too shallow"

**Solution**: Use `fetch-depth: 0` for incremental mode.

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0  # Important!
```

---

## Testing the Action Locally

Use [act](https://github.com/nektos/act) to test locally:

```bash
# Install act
# Windows: choco install act-cli
# Mac: brew install act

# Test the action
cd your-project
act -j diagram -s OPENAI_API_KEY=sk-your-key
```

---

## Monitoring Usage

### View Action Runs

1. Go to repository → Actions tab
2. See all workflow runs
3. Click on a run to see details

### Check Outputs

The action provides outputs you can use:

```yaml
- uses: EugeneHuo/mermaid-gen@v1.0.0
  id: diagram
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}

- name: Show results
  run: |
    echo "Mode used: ${{ steps.diagram.outputs.mode-used }}"
    echo "Affected nodes: ${{ steps.diagram.outputs.affected-nodes }}"
    echo "Impact level: ${{ steps.diagram.outputs.impact-level }}"
```

---

## Next Steps

1. ✅ Push your code to GitHub
2. ✅ Create a release (v1.0.0)
3. ✅ Share with your team
4. ✅ Add to organization documentation
5. ✅ Monitor usage and gather feedback

Your GitHub Action is ready to use! 🎉
