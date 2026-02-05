"""
Workflow Utilities
Helper functions for CI/CD integration and incremental updates
"""

import subprocess
import os
from typing import List, Dict, Optional, Tuple
from pathlib import Path


def generate_diff_context(repo_path: str, base_ref: str = "HEAD~1", api_key: str = None) -> Tuple[str, Dict]:
    """
    Generate diff_context.txt from git diff with semantic parsing
    
    Args:
        repo_path: Path to git repository
        base_ref: Base reference for diff (default: HEAD~1)
        api_key: OpenAI API key for semantic parsing (required)
        
    Returns:
        Tuple of (diff_output, semantic_diff_data)
    """
    try:
        # Get detailed diff with context - ONLY for code files, EXCLUDE .md files
        # Filter to only include Python, JavaScript, TypeScript, Java files
        result = subprocess.run(
            ["git", "diff", base_ref, "HEAD", "--unified=10", "--", "*.py", "*.js", "*.ts", "*.java", "*.go", "*.rb"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        
        diff_output = result.stdout
        
        # If no code files changed, try without filter but EXCLUDE .md files
        if not diff_output.strip():
            print("⚠️  No code file changes detected, checking all files (excluding .md)...")
            result = subprocess.run(
                ["git", "diff", base_ref, "HEAD", "--unified=10", "--", ".", ":(exclude)*.md"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            diff_output = result.stdout
        
        # Save to diff_context.txt
        diff_file = os.path.join(repo_path, "diff_context.txt")
        with open(diff_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("GIT DIFF CONTEXT - Incremental Diagram Update\n")
            f.write("="*80 + "\n\n")
            f.write(f"Base Reference: {base_ref}\n")
            f.write(f"Current Reference: HEAD\n\n")
            f.write("="*80 + "\n")
            f.write("DIFF OUTPUT:\n")
            f.write("="*80 + "\n\n")
            f.write(diff_output)
        
        print(f"✅ Generated diff_context.txt ({len(diff_output)} characters)")
        
        # Use semantic parsing with LLM
        if api_key:
            from semantic_diff_parser import generate_semantic_diff_context, save_semantic_diff
            parsed_data = generate_semantic_diff_context(diff_output, api_key)
            save_semantic_diff(parsed_data)
        else:
            print("⚠️  No API key provided, falling back to regex parsing")
            from change_mapper import parse_git_diff_output
            parsed_data = parse_git_diff_output(diff_output)
        
        return diff_output, parsed_data
        
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Git diff failed: {e}")
        return "", {}
    except Exception as e:
        print(f"⚠️  Error generating diff context: {e}")
        return "", {}


def analyze_repository_state(repo_path: str) -> Dict:
    """
    Analyze repository state to determine update mode
    
    Args:
        repo_path: Path to repository
        
    Returns:
        Dictionary with state information:
        - has_diagram: bool
        - is_git_repo: bool
        - mode: 'full', 'incremental', or 'new'
        - diagram_path: str or None
    """
    state = {
        'has_diagram': False,
        'is_git_repo': False,
        'mode': 'full',
        'diagram_path': None
    }
    
    # Check for diagram.html
    diagram_path = os.path.join(repo_path, "diagram.html")
    if os.path.exists(diagram_path):
        state['has_diagram'] = True
        state['diagram_path'] = diagram_path
    
    # Check if git repository
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=repo_path,
            capture_output=True,
            check=True
        )
        state['is_git_repo'] = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        state['is_git_repo'] = False
    
    # Determine mode
    if state['has_diagram'] and state['is_git_repo']:
        state['mode'] = 'incremental'
    elif state['is_git_repo']:
        state['mode'] = 'new'
    else:
        state['mode'] = 'full'
    
    return state


def get_changed_files_detailed(repo_path: str, base_ref: str = "HEAD~1") -> List[str]:
    """
    Get list of changed files with more detail
    
    Args:
        repo_path: Path to repository
        base_ref: Base reference for comparison
        
    Returns:
        List of changed file paths
    """
    try:
        # Get changed files
        result = subprocess.run(
            ["git", "diff", "--name-only", base_ref, "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        
        changed_files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
        
        # Filter for supported file types
        supported_extensions = ('.py', '.js', '.ts', '.java')
        filtered_files = [f for f in changed_files if f.endswith(supported_extensions)]
        
        return filtered_files
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def validate_mermaid_syntax(mermaid_code: str) -> Tuple[bool, str]:
    """
    Basic validation of Mermaid syntax
    
    Args:
        mermaid_code: Mermaid diagram code
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not mermaid_code or not mermaid_code.strip():
        return False, "Empty diagram code"
    
    lines = mermaid_code.strip().split('\n')
    
    # Check for diagram type
    first_line = lines[0].strip()
    if not (first_line.startswith('flowchart') or first_line.startswith('graph')):
        return False, "Missing or invalid diagram type declaration"
    
    # Check for balanced subgraphs
    subgraph_count = 0
    end_count = 0
    
    for line in lines:
        line = line.strip()
        if line.startswith('subgraph'):
            subgraph_count += 1
        elif line == 'end':
            end_count += 1
    
    if subgraph_count != end_count:
        return False, f"Unbalanced subgraphs: {subgraph_count} subgraph(s) vs {end_count} end(s)"
    
    # Check for at least one node
    has_node = any('[' in line or '(' in line for line in lines[1:])
    if not has_node:
        return False, "No nodes found in diagram"
    
    return True, "Valid"


def create_html_from_mermaid(mermaid_code: str, output_path: str) -> bool:
    """
    Create HTML file from Mermaid code
    
    Args:
        mermaid_code: Mermaid diagram code
        output_path: Path to save HTML file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Validate first
        is_valid, error = validate_mermaid_syntax(mermaid_code)
        if not is_valid:
            print(f"⚠️  Invalid Mermaid syntax: {error}")
            return False
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Mermaid Diagram</title>
</head>
<body>
    <div class="mermaid">
{mermaid_code}
    </div>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true }});
    </script>
</body>
</html>
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Created {output_path}")
        return True
        
    except Exception as e:
        print(f"⚠️  Error creating HTML: {e}")
        return False


def should_use_incremental_mode(repo_path: str, threshold: float = 0.5, api_key: str = None) -> Tuple[bool, str]:
    """
    Determine if incremental mode should be used based on change impact
    
    Args:
        repo_path: Path to repository
        threshold: Percentage threshold for switching to full mode (0.0-1.0)
        api_key: OpenAI API key for semantic diff parsing
        
    Returns:
        Tuple of (use_incremental, reason)
    """
    state = analyze_repository_state(repo_path)
    
    if not state['has_diagram']:
        return False, "No existing diagram found"
    
    if not state['is_git_repo']:
        return False, "Not a git repository"
    
    # Check if there are changes
    changed_files = get_changed_files_detailed(repo_path)
    
    if not changed_files:
        return False, "No changes detected"
    
    # Parse existing diagram to check impact
    try:
        from mermaid_parser import extract_mermaid_from_html, parse_mermaid_diagram
        from change_mapper import ChangeMapper, calculate_change_impact, parse_git_diff_output
        
        mermaid_code = extract_mermaid_from_html(state['diagram_path'])
        if not mermaid_code:
            return False, "Could not parse existing diagram"
        
        diagram = parse_mermaid_diagram(mermaid_code)
        
        # Generate diff and analyze impact
        diff_output, diff_data = generate_diff_context(repo_path, api_key=api_key)
        
        if not diff_output:
            return False, "Could not generate diff"
        
        mapper = ChangeMapper(diagram)
        affected_nodes = mapper.map_changes_to_nodes(diff_data)
        impact_level, percentage = calculate_change_impact(affected_nodes, len(diagram.nodes))
        
        print(f"📊 Change Impact: {impact_level} ({percentage:.1f}% of nodes affected)")
        
        if percentage > (threshold * 100):
            return False, f"High impact ({percentage:.1f}%) - using full regeneration"
        
        return True, f"Low impact ({percentage:.1f}%) - using incremental update"
        
    except Exception as e:
        print(f"⚠️  Error analyzing impact: {e}")
        return False, "Error during impact analysis"


if __name__ == "__main__":
    # Test workflow utils
    print("Testing Workflow Utilities...")
    
    repo_path = "."
    
    print("\n=== Repository State ===")
    state = analyze_repository_state(repo_path)
    for key, value in state.items():
        print(f"{key}: {value}")
    
    if state['is_git_repo']:
        print("\n=== Changed Files ===")
        changed = get_changed_files_detailed(repo_path)
        print(f"Found {len(changed)} changed file(s):")
        for f in changed:
            print(f"  - {f}")
        
        print("\n=== Incremental Mode Decision ===")
        use_incremental, reason = should_use_incremental_mode(repo_path)
        print(f"Use Incremental: {use_incremental}")
        print(f"Reason: {reason}")
