import os
import subprocess
import re
import glob
import sys
from pathlib import Path

# Configuration
PIPELINE_ROOT = r"C:\Users\T773534\Downloads\gen-ai-data-ingestion-1\gen-ai-data-ingestion\src"
# List of pipelines to evaluate. You can add more folder names here.
TARGET_PIPELINES = [
    "aia_milo_pipeline"
]

def count_readme_steps(pipeline_path):
    """Counts steps in README.md based on '#### Number.' pattern."""
    readme_path = os.path.join(pipeline_path, "README.md")
    if not os.path.exists(readme_path):
        return 0
    
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Regex to find headers like "#### 1. Initial Setup"
            # We look for #### followed by a number and a dot
            matches = re.findall(r'####\s+\d+\.', content)
            return len(matches)
    except Exception as e:
        print(f"Error reading README at {readme_path}: {e}")
        return 0

def calculate_raw_tokens(pipeline_path):
    """Calculates total characters in .py files to simulate raw LLM scan."""
    total_chars = 0
    for root, dirs, files in os.walk(pipeline_path):
        # Skip hidden dirs and venv
        dirs[:] = [d for d in dirs if not d.startswith('.') and 'venv' not in d]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        total_chars += len(f.read())
                except Exception:
                    pass
    return total_chars

def get_tool_metrics():
    """Extracts metrics from the tool's output files."""
    tool_chars = 0
    diagram_steps = 0
    
    # 1. Get context size from debug output
    if os.path.exists("ast_debug_output.txt"):
        try:
            with open("ast_debug_output.txt", 'r', encoding='utf-8') as f:
                content = f.read()
                # Look for "Total context size: 1234 characters"
                match = re.search(r"Total context size: (\d+) characters", content)
                if match:
                    tool_chars = int(match.group(1))
        except Exception as e:
            print(f"Error reading debug output: {e}")

    # 2. Get step count from diagram
    if os.path.exists("diagram.html"):
        try:
            with open("diagram.html", 'r', encoding='utf-8') as f:
                content = f.read()
                # Count "subgraph Step" occurrences
                # This matches the tool's output format: subgraph Step1_Ingestion, etc.
                matches = re.findall(r'subgraph Step\d+', content)
                diagram_steps = len(matches)
        except Exception as e:
            print(f"Error reading diagram: {e}")
            
    return tool_chars, diagram_steps

def main():
    print(f"{'Pipeline':<30} | {'README Steps':<12} | {'Diagram Steps':<13} | {'Raw Chars':<10} | {'Tool Chars':<10} | {'Savings':<8}")
    print("-" * 100)

    for pipeline_name in TARGET_PIPELINES:
        full_path = os.path.join(PIPELINE_ROOT, pipeline_name)
        
        if not os.path.exists(full_path):
            print(f"Skipping {pipeline_name} (not found)")
            continue

        # 1. Static Analysis
        readme_steps = count_readme_steps(full_path)
        raw_chars = calculate_raw_tokens(full_path)

        # 2. Run the Tool
        # We run main.py with the --debug flag to get AST stats
        # We capture stdout to avoid cluttering the console
        try:
            # Load API key from .env manually for the subprocess
            env = os.environ.copy()
            # Force UTF-8 encoding for the subprocess to handle emojis
            env["PYTHONIOENCODING"] = "utf-8"
            
            with open(".env", "r") as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        env[key] = value

            subprocess.run(
                [sys.executable, "main.py", full_path, "--debug"], 
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                env=env
            )
        except subprocess.CalledProcessError as e:
            print(f"Error running tool on {pipeline_name}")
            print(f"STDERR: {e.stderr.decode('utf-8', errors='replace')}")
            continue

        # 3. Extract Results
        tool_chars, diagram_steps = get_tool_metrics()

        # 4. Calculate Savings
        savings = 0
        if raw_chars > 0:
            savings = ((raw_chars - tool_chars) / raw_chars) * 100

        # 5. Print Row
        print(f"{pipeline_name:<30} | {readme_steps:<12} | {diagram_steps:<13} | {raw_chars:<10} | {tool_chars:<10} | {savings:.1f}%")

if __name__ == "__main__":
    main()
