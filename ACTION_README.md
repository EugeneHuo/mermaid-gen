# Mermaid Diagram Generator - GitHub Action

[![GitHub Action](https://img.shields.io/badge/GitHub-Action-blue?logo=github-actions)](https://github.com/EugeneHuo/mermaid-gen)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Automatically generate or incrementally update Mermaid architecture diagrams from your codebase using AI.

## ✨ Features

- 🤖 **AI-Powered**: Uses GPT-4o to analyze your code and generate diagrams
- ⚡ **Incremental Updates**: Only updates affected nodes when code changes (Parse-Filter-Update logic)
- 🔒 **Structure Preservation**: Maintains diagram layout and connections during updates
- 📊 **Impact Analysis**: Shows what percentage of diagram is affected by changes
- 🎯 **Smart Fallback**: Automatically falls back to full regeneration when needed
- 🐍 **Multi-Language**: Supports Python, JavaScript, TypeScript, Java

## 🚀 Quick Start

### 1. Add to Your Workflow

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
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - uses: EugeneHuo/mermaid-gen@main
        with:
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
      
      - run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add diagram.html
          git diff --staged --quiet || git commit -m "🤖 Update diagram"
          git push
```

### 2. Add OpenAI API Key

Go to your repository settings:
```
Settings → Secrets → New repository secret
Name: OPENAI_API_KEY
Value: sk-your-api-key-here
```

### 3. Enable Workflow Permissions

```
Settings → Actions → General → Workflow permissions
✅ Read and write permissions
```

### 4. Push and Watch! 🎉

The action will automatically generate or update your diagram on every push.

## 📖 Usage

### Basic Example

```yaml
- uses: EugeneHuo/mermaid-gen@main
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

### With All Options

```yaml
- uses: EugeneHuo/mermaid-gen@main
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
    mode: auto
    path: .
    pipeline-name: "My Pipeline"
    pipeline-purpose: "Processes data"
    data-type: "JSON files"
    data-source: "API"
    use-case: "Analytics"
    team-owner: "Data Team"
    include-comments: true
    debug: true
```

### With Outputs

```yaml
- id: diagram
  uses: EugeneHuo/mermaid-gen@main
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}

- run: |
    echo "Mode: ${{ steps.diagram.outputs.mode-used }}"
    echo "Impact: ${{ steps.diagram.outputs.impact-level }}"
    echo "Affected: ${{ steps.diagram.outputs.affected-nodes }}"
```

## 📥 Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `openai-api-key` | ✅ | - | OpenAI API key |
| `mode` | ❌ | `auto` | `auto`, `new`, `incremental`, or `full` |
| `path` | ❌ | `.` | Path to analyze |
| `pipeline-name` | ❌ | - | Pipeline name |
| `pipeline-purpose` | ❌ | - | What it does |
| `data-type` | ❌ | - | Data type processed |
| `data-source` | ❌ | - | Data source |
| `use-case` | ❌ | - | Use case |
| `team-owner` | ❌ | - | Team/owner |
| `include-comments` | ❌ | `false` | Include code comments |
| `debug` | ❌ | `false` | Enable debug output |
| `force-full` | ❌ | `false` | Force full regeneration |

## 📤 Outputs

| Output | Description |
|--------|-------------|
| `diagram-path` | Path to `diagram.html` |
| `mode-used` | Mode used (`full` or `incremental`) |
| `affected-nodes` | Number of affected nodes |
| `impact-level` | Impact level (`none`, `low`, `medium`, `high`, `full`) |

## 🎯 Modes

### Auto Mode (Recommended)
```yaml
mode: auto
```
- Detects if diagram exists
- Uses incremental if possible
- Falls back to full when needed

### Incremental Mode
```yaml
mode: incremental
```
- Updates only changed nodes
- Preserves diagram structure
- Faster and cheaper

### Full Mode
```yaml
mode: full
```
- Regenerates entire diagram
- Best for major refactors
- Ignores existing diagram

## 💡 Examples

### Example 1: Auto-Update on Push

```yaml
on:
  push:
    branches: [main]

jobs:
  diagram:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - uses: EugeneHuo/mermaid-gen@main
        with:
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

### Example 2: PR Comments

```yaml
- id: diagram
  uses: EugeneHuo/mermaid-gen@main
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
    debug: true

- if: github.event_name == 'pull_request'
  uses: actions/github-script@v6
  with:
    script: |
      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: `📊 Diagram updated! Mode: ${{ steps.diagram.outputs.mode-used }}`
      });
```

### Example 3: Weekly Full Regeneration

```yaml
on:
  schedule:
    - cron: '0 0 * * 0'  # Sunday midnight

jobs:
  regenerate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: EugeneHuo/mermaid-gen@main
        with:
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          force-full: true
```

### Example 4: Monorepo Multi-Service

```yaml
strategy:
  matrix:
    service: [api, worker, frontend]

steps:
  - uses: EugeneHuo/mermaid-gen@main
    with:
      openai-api-key: ${{ secrets.OPENAI_API_KEY }}
      path: ./services/${{ matrix.service }}
      pipeline-name: "${{ matrix.service }} Service"
```

## 🔧 How It Works

### Incremental Update Flow

```
1. PARSE
   ↓ Extract existing diagram structure
   
2. FILTER  
   ↓ Analyze git diff to find changes
   ↓ Map changes to diagram nodes
   
3. UPDATE
   ↓ Generate targeted LLM prompt
   ↓ Update only affected nodes
   ↓ Preserve everything else
```

### Change Impact Levels

| Impact | % Changed | Action |
|--------|-----------|--------|
| None | 0% | Skip |
| Low | <20% | Incremental ✅ |
| Medium | 20-50% | Incremental ✅ |
| High | 50-80% | Consider full ⚠️ |
| Full | >80% | Full regen ❌ |

## 📚 Documentation

- **[ACTION_USAGE.md](ACTION_USAGE.md)** - Complete usage guide
- **[INCREMENTAL_UPDATE_GUIDE.md](INCREMENTAL_UPDATE_GUIDE.md)** - Detailed technical docs
- **[examples/](examples/)** - Example workflows

## 🐛 Troubleshooting

### "Action not found"
Make sure the repository is public or you have access.

### "OPENAI_API_KEY not set"
Add the secret to your repository settings.

### "Permission denied"
Enable write permissions in Actions settings.

### "No changes detected"
Use `fetch-depth: 0` in checkout step.

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

## 🙏 Acknowledgments

- Built with OpenAI GPT-4o
- Mermaid.js for diagram rendering
- GitHub Actions for automation

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/EugeneHuo/mermaid-gen/issues)
- **Discussions**: [GitHub Discussions](https://github.com/EugeneHuo/mermaid-gen/discussions)
- **Documentation**: See docs above

---

**Made with ❤️ by [EugeneHuo](https://github.com/EugeneHuo)**

⭐ Star this repo if you find it useful!
