# Using as GitHub Action

Use in any repo to auto-generate/update Mermaid diagrams.

## Setup (3 steps)

**1. Add secret:** Settings → Secrets → `OPENAI_API_KEY`

**2. Enable write:** Settings → Actions → Read/write permissions

**3. Create `.github/workflows/diagram.yml`:**

```yaml
name: Diagram
on: [push]

jobs:
  gen:
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
          git config user.name "bot"
          git config user.email "bot@github.com"
          git add diagram.html || true
          git commit -m "Update diagram" || true
          git push
```

## All Options

```yaml
name: Diagram
on: [push, pull_request, workflow_dispatch]

jobs:
  gen:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - id: diagram
        uses: EugeneHuo/mermaid-gen@v1.0.0
        with:
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          mode: auto                          # auto|new|incremental|full
          path: .
          pipeline-name: "Data Pipeline"
          pipeline-purpose: "ETL"
          data-type: "JSON"
          data-source: "API"
          use-case: "Analytics"
          team-owner: "Data Team"
          include-comments: true
          debug: true
          force-full: false

      - run: echo "${{ steps.diagram.outputs.mode-used }}, ${{ steps.diagram.outputs.impact-level }}"

      - run: |
          git config user.name "bot"
          git config user.email "bot@github.com"
          git add diagram.html *.txt || true
          git commit -m "Update [${{ steps.diagram.outputs.mode-used }}]" || true
          git push

      - uses: actions/upload-artifact@v4
        with:
          name: diagrams
          path: |
            diagram.html
            *.txt
          if-no-files-found: ignore
```

## Inputs/Outputs

**Inputs:**
- `openai-api-key` (required)
- `mode` (auto|new|incremental|full, default: auto)
- `path` (default: .)
- `pipeline-name`, `pipeline-purpose`, `data-type`, `data-source`, `use-case`, `team-owner`
- `include-comments`, `debug`, `force-full` (booleans)

**Outputs:**
- `diagram-path`: diagram.html
- `mode-used`: full|incremental
- `affected-nodes`: count
- `impact-level`: none|low|medium|high|full

## Examples

**Auto mode (recommended):**
```yaml
- uses: EugeneHuo/mermaid-gen@v1.0.0
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

**Force incremental:**
```yaml
- uses: EugeneHuo/mermaid-gen@v1.0.0
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
    mode: incremental
    debug: true
```

**With metadata:**
```yaml
- uses: EugeneHuo/mermaid-gen@v1.0.0
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
    pipeline-name: "ML Pipeline"
    data-source: "S3"
    team-owner: "ML Team"
```

**Conditional (Python changes only):**
```yaml
- id: filter
  uses: dorny/paths-filter@v2
  with:
    filters: |
      py:
        - '**.py'

- if: steps.filter.outputs.py == 'true'
  uses: EugeneHuo/mermaid-gen@v1.0.0
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

## Version Pinning

```yaml
uses: EugeneHuo/mermaid-gen@v1.0.0  # Tag (prod)
uses: EugeneHuo/mermaid-gen@main    # Branch (dev)
uses: EugeneHuo/mermaid-gen@abc123  # SHA (locked)
```

## Advanced

**PR comment:**
```yaml
- id: gen
  uses: EugeneHuo/mermaid-gen@v1.0.0
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}

- if: github.event_name == 'pull_request'
  uses: actions/github-script@v6
  with:
    script: |
      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: `Mode: ${{ steps.gen.outputs.mode-used }}, Impact: ${{ steps.gen.outputs.impact-level }}`
      });
```

**Weekly regen:**
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

**Monorepo matrix:**
```yaml
strategy:
  matrix:
    svc: [api, worker, ui]
steps:
  - uses: EugeneHuo/mermaid-gen@v1.0.0
    with:
      openai-api-key: ${{ secrets.OPENAI_API_KEY }}
      path: ./services/${{ matrix.svc }}
      pipeline-name: "${{ matrix.svc }}"
  - run: mv diagram.html diagram-${{ matrix.svc }}.html
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Action not found | Repo must be public/accessible |
| API key not set | Add to repo secrets |
| Permission denied | Settings → Actions → Read/write perms |
| No changes detected | Use `fetch-depth: 0` in checkout |
| Git push fails on PR | Use `github.head_ref \|\| github.ref_name` for branch |

## Best Practices

- Pin to tag in prod (`@v1.0.0`)
- Use auto mode (smart detection)
- Enable debug for troubleshooting
- Upload artifacts for review
- Add PR comments showing impact
- Use conditional exec to save cost
- Test locally first: `python main_incremental.py . --mode auto --debug`

## Runs on GitHub Servers

When teams use `uses: EugeneHuo/mermaid-gen@v1.0.0`:
1. GitHub clones YOUR action to runner
2. Installs YOUR dependencies
3. Runs YOUR script on their code
4. Generates diagram in their workspace
5. They commit to their repo

**No local clone needed. Everything on GitHub's infrastructure.**

## More Info

- [INCREMENTAL_UPDATE_GUIDE.md](INCREMENTAL_UPDATE_GUIDE.md)
- [Issues](https://github.com/EugeneHuo/mermaid-gen/issues)
