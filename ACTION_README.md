# Mermaid Diagram Generator - GitHub Action

Auto-generate/update Mermaid architecture diagrams from code using GPT-4o.

## Features

- 🤖 GPT-4o powered code analysis
- ⚡ Incremental updates (Parse-Filter-Update)
- 🔒 Structure preservation during updates
- 📊 Impact analysis
- 🎯 Smart fallback to full regen
- 🐍 Multi-language (Python, JS, TS, Java)

## Quick Start

**1. Create `.github/workflows/diagram.yml`:**

```yaml
name: Generate Diagram
on: [push]

jobs:
  diagram:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: EugeneHuo/mermaid-gen@v1.0.0
        with:
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}

      - run: |
          git config user.name "github-actions[bot]"
          git config user.email "action@github.com"
          git add diagram.html || true
          git commit -m "Update diagram" || true
          git push
```

**2. Add secret:** Settings → Secrets → `OPENAI_API_KEY`

**3. Enable write:** Settings → Actions → Read/write permissions

**4. Push. Done.**

## Usage

**Minimal:**
```yaml
- uses: EugeneHuo/mermaid-gen@v1.0.0
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

**All options:**
```yaml
- uses: EugeneHuo/mermaid-gen@v1.0.0
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
    mode: auto                        # auto|new|incremental|full
    path: .
    pipeline-name: "My Pipeline"
    pipeline-purpose: "Processes data"
    data-type: "JSON"
    data-source: "API"
    use-case: "Analytics"
    team-owner: "Data Team"
    include-comments: true
    debug: true
```

**With outputs:**
```yaml
- id: gen
  uses: EugeneHuo/mermaid-gen@v1.0.0
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}

- run: echo "${{ steps.gen.outputs.mode-used }}, ${{ steps.gen.outputs.impact-level }}"
```

## Inputs

| Input | Req | Default | Description |
|-------|-----|---------|-------------|
| `openai-api-key` | ✅ | - | OpenAI API key |
| `mode` | - | `auto` | auto/new/incremental/full |
| `path` | - | `.` | Project path |
| `pipeline-name` | - | - | Pipeline name |
| `pipeline-purpose` | - | - | What it does |
| `data-type` | - | - | Data type |
| `data-source` | - | - | Source |
| `use-case` | - | - | Use case |
| `team-owner` | - | - | Owner |
| `include-comments` | - | `false` | Include comments |
| `debug` | - | `false` | Debug mode |
| `force-full` | - | `false` | Force full regen |

## Outputs

| Output | Value |
|--------|-------|
| `diagram-path` | `diagram.html` |
| `mode-used` | `full` or `incremental` |
| `affected-nodes` | Count |
| `impact-level` | none/low/medium/high/full |

## Modes

**Auto (default):** Detects diagram → incremental or full
**Incremental:** Updates changed nodes only → fast/cheap
**Full:** Regen entire diagram → for major refactors
**New:** Entry points only → initial scan

## Examples

**PR comment:**
```yaml
- id: gen
  uses: EugeneHuo/mermaid-gen@v1.0.0
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}

- if: github.event_name == 'pull_request'
  run: echo "Mode: ${{ steps.gen.outputs.mode-used }}, Impact: ${{ steps.gen.outputs.impact-level }}"
```

**Weekly full regen:**
```yaml
on:
  schedule:
    - cron: '0 0 * * 0'
jobs:
  regen:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: EugeneHuo/mermaid-gen@v1.0.0
        with:
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          force-full: true
```

**Monorepo:**
```yaml
strategy:
  matrix:
    svc: [api, worker, ui]
steps:
  - uses: EugeneHuo/mermaid-gen@v1.0.0
    with:
      openai-api-key: ${{ secrets.OPENAI_API_KEY }}
      path: ./services/${{ matrix.svc }}
```

## How It Works

**Incremental flow:**
```
PARSE → extract diagram
FILTER → git diff → map to nodes
UPDATE → targeted LLM → update nodes only
```

**Impact levels:**
- None (0%) → skip
- Low (<20%) → incremental
- Medium (20-50%) → incremental
- High (50-80%) → consider full
- Full (>80%) → full regen

## Docs

- [ACTION_USAGE.md](ACTION_USAGE.md) - Full guide
- [INCREMENTAL_UPDATE_GUIDE.md](INCREMENTAL_UPDATE_GUIDE.md) - Technical details
- [examples/](examples/) - Workflow examples

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Action not found | Repo must be public or accessible |
| API key not set | Add to repo secrets |
| Permission denied | Enable write in Actions settings |
| No changes detected | Use `fetch-depth: 0` in checkout |

## Version Pinning

```yaml
uses: EugeneHuo/mermaid-gen@v1.0.0  # Tag (recommended)
uses: EugeneHuo/mermaid-gen@main    # Branch (auto-updates)
uses: EugeneHuo/mermaid-gen@abc123  # SHA (locked)
```

## License

MIT

---

Built with GPT-4o • [Issues](https://github.com/EugeneHuo/mermaid-gen/issues) • ⭐ Star if useful
