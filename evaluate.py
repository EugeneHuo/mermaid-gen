import os
import subprocess
import re
import sys

# Configuration
# Using raw strings for Windows paths
PIPELINES = [
    r"C:\Users\T773534\Downloads\gen-ai-data-ingestion-1\gen-ai-data-ingestion\src\aia_onesource_pipeline",
    r"C:\Users\T773534\Downloads\gen-ai-data-ingestion-1\gen-ai-data-ingestion\src\aia_crtc_pipeline"
]
TOOL_SCRIPT = "main.py"
PYTHON_CMD = sys.executable

def count_tokens(text):
    # Approximation: 1 token ~= 4 characters
    return len(text) / 4

def get_raw_code_token_count(directory):
    total_chars = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                try:
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        total_chars += len(f.read())
                except:
                    pass
    return count_tokens(" " * total_chars)

def parse_mermaid_steps(html_path):
    if not os.path.exists(html_path):
        return 0
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r'<div class="mermaid">\s*(.*?)\s*</div>', content, re.DOTALL)
        if match:
            mermaid_code = match.group(1)
            # Count nodes: Look for identifiers followed by brackets/parens
            # e.g. A[Text], B(Text), C{Text}
            nodes = re.findall(r'\w+\s*[\[\(\{\<].*?[\]\)\}\>]', mermaid_code)
            return len(nodes)
    except Exception as e:
        print(f"Error parsing mermaid: {e}")
    return 0

def parse_readme_steps(directory):
    readme_path = os.path.join(directory, "README.md")
    if not os.path.exists(readme_path):
        return 0
    
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Heuristic: Count numbered list items (1. Step)
    # We look for lines starting with a number and a dot
    steps = re.findall(r'^\s*\d+\.\s+', content, re.MULTILINE)
    return len(steps)

def evaluate_pipeline(pipeline_path):
    pipeline_name = os.path.basename(pipeline_path)
    print(f"Evaluating {pipeline_name}...")
    
    # 1. Run the tool
    # We assume .env is loaded by the subprocess or we pass env vars
    cmd = [PYTHON_CMD, TOOL_SCRIPT, pipeline_path, "--debug", "--include-comments"]
    
    # Load .env manually to ensure subprocess gets it
    env = os.environ.copy()
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k] = v
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            print(f"Tool failed for {pipeline_name}: {result.stderr}")
            # Continue anyway to see if we can salvage metrics
    except Exception as e:
        print(f"Execution error: {e}")
        return None

    # 2. Analyze AST Debug Output (Tool Usage)
    ast_file = "ast_debug_output.txt"
    tool_token_count = 0
    if os.path.exists(ast_file):
        with open(ast_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract "Total context size: X characters"
            match = re.search(r'Total context size: (\d+) characters', content)
            if match:
                tool_token_count = int(match.group(1)) / 4
            else:
                tool_token_count = count_tokens(content)
        
        # Rename debug output to keep it
        os.rename(ast_file, f"ast_debug_{pipeline_name}.txt")

    # 3. Analyze Raw Code (Baseline)
    raw_token_count = get_raw_code_token_count(pipeline_path)
    
    # 4. Analyze Result (Diagram)
    diagram_file = "diagram.html"
    diagram_steps = parse_mermaid_steps(diagram_file)
    if os.path.exists(diagram_file):
        os.rename(diagram_file, f"diagram_{pipeline_name}.html")
    
    # 5. Analyze README (Ground Truth Proxy)
    readme_steps = parse_readme_steps(pipeline_path)
    
    return {
        "pipeline": pipeline_name,
        "raw_tokens": int(raw_token_count),
        "tool_tokens": int(tool_token_count),
        "savings_percent": f"{(1 - tool_token_count/raw_token_count)*100:.1f}%" if raw_token_count else "0%",
        "readme_steps": readme_steps,
        "diagram_steps": diagram_steps
    }

def main():
    results = []
    for p in PIPELINES:
        if os.path.exists(p):
            res = evaluate_pipeline(p)
            if res:
                results.append(res)
        else:
            print(f"Pipeline path not found: {p}")
            
    print("\n" + "="*95)
    print(f"{'Pipeline':<25} | {'Raw Tok':<10} | {'Tool Tok':<10} | {'Saved':<8} | {'README Steps':<12} | {'Diagram Nodes':<12}")
    print("-" * 95)
    for r in results:
        print(f"{r['pipeline']:<25} | {r['raw_tokens']:<10} | {r['tool_tokens']:<10} | {r['savings_percent']:<8} | {r['readme_steps']:<12} | {r['diagram_steps']:<12}")
    print("="*95)

if __name__ == "__main__":
    main()
