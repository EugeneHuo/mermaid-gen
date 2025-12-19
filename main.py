import os
import typer
import openai
import pathspec
from pathlib import Path

app = typer.Typer()
FUEL_PROXY_URL = "https://api-beta.fuelix.ai"

import ast

class PipelineVisitor(ast.NodeVisitor):
    def __init__(self):
        self.structure = []
        self.indent_level = 0

    def _indent(self):
        return "  " * self.indent_level

    def visit_Import(self, node):
        names = [n.name for n in node.names]
        self.structure.append(f"{self._indent()}IMPORT: {', '.join(names)}")

    def visit_ImportFrom(self, node):
        names = [n.name for n in node.names]
        self.structure.append(f"{self._indent()}FROM {node.module} IMPORT: {', '.join(names)}")

    def visit_If(self, node):
        # Extract the condition text roughly
        condition = ast.unparse(node.test)
        self.structure.append(f"{self._indent()}IF ({condition}):")
        self.indent_level += 1
        self.generic_visit(node)
        self.indent_level -= 1

    def visit_For(self, node):
        target = ast.unparse(node.target)
        iterator = ast.unparse(node.iter)
        self.structure.append(f"{self._indent()}FOR {target} IN {iterator}:")
        self.indent_level += 1
        self.generic_visit(node)
        self.indent_level -= 1

    def visit_Call(self, node):
        # This captures function calls like 'log_to_bigquery(...)'
        try:
            func_name = ast.unparse(node.func)
            self.structure.append(f"{self._indent()}CALL: {func_name}(...)")
        except:
            pass

    def visit_Assign(self, node):
        # Captures 'doc_ref = ...' but ignores the huge dictionary details
        targets = [ast.unparse(t) for t in node.targets]
        # We don't recurse into value to avoid printing dictionary bodies
        # But we do check if the value is a Function Call
        if isinstance(node.value, ast.Call):
            func_name = ast.unparse(node.value.func)
            self.structure.append(f"{self._indent()}SET {'='.join(targets)} = CALL {func_name}(...)")
        else:
            self.structure.append(f"{self._indent()}SET {'='.join(targets)} = [Value]")

    def visit_FunctionDef(self, node):
        # In case there are helper functions defined
        self.structure.append(f"{self._indent()}DEF {node.name}(args):")
        self.indent_level += 1
        self.generic_visit(node)
        self.indent_level -= 1

import ast

class SemanticVisitor(ast.NodeVisitor):
    def __init__(self):
        self.structure = []
        self.indent_level = 0

    def _indent(self):
        return "  " * self.indent_level

    def visit_Import(self, node):
        # We can skip imports now, they clutter the logic flow
        pass

    def visit_ImportFrom(self, node):
        pass

    def visit_If(self, node):
        condition = ast.unparse(node.test)
        self.structure.append(f"{self._indent()}IF CHECK: {condition}")
        self.indent_level += 1
        self.generic_visit(node)
        self.indent_level -= 1

    def visit_Assign(self, node):
        targets = [ast.unparse(t) for t in node.targets]
        # logic to capture important data transformations
        if isinstance(node.value, ast.Call):
            func_name = ast.unparse(node.value.func)
            
            # Capture both positional and keyword arguments with their values
            args = []
            for a in node.value.args:
                args.append(ast.unparse(a))
            
            # Capture keyword arguments (these often contain config!)
            kwargs = []
            for kw in node.value.keywords:
                key = kw.arg
                value = ast.unparse(kw.value)
                kwargs.append(f"{key}={value}")
            
            # Combine args and kwargs
            all_args = args + kwargs
            arg_str = ", ".join(all_args)
            
            # Don't truncate if it contains important config keywords
            important_keywords = ['chunk_size', 'chunk_overlap', 'model', 'namespace', 'index', 'bucket', 'path']
            if any(kw in arg_str.lower() for kw in important_keywords):
                # Keep full args for config-heavy calls
                self.structure.append(f"{self._indent()}CONFIG: {'='.join(targets)} = {func_name}({arg_str})")
            else:
                # Truncate for non-config calls
                if len(arg_str) > 50: 
                    arg_str = arg_str[:50] + "..."
                self.structure.append(f"{self._indent()}ASSIGN: {'='.join(targets)} = CALL {func_name}({arg_str})")
        
        # Capture Dict creations (Config/Data objects)
        elif isinstance(node.value, ast.Dict):
            keys = [ast.unparse(k) for k in node.value.keys if k]
            self.structure.append(f"{self._indent()}DATA_STRUCT: {'='.join(targets)} = Keys[{', '.join(keys)}]")
        
        # Capture constant assignments (like model names, paths)
        elif isinstance(node.value, ast.Constant):
            value = node.value.value
            if isinstance(value, str) and len(value) < 100:
                self.structure.append(f"{self._indent()}CONSTANT: {'='.join(targets)} = \"{value}\"")

    def visit_Call(self, node):
        # This is the most important part: Capturing Logging and External Calls
        func_name = ast.unparse(node.func)
        
        # If it's a logging call, it usually describes the "Step"
        if "log" in func_name or "print" in func_name:
            if node.args and isinstance(node.args[0], ast.Constant):
                # This captures: logging.info("Finished processing chunks")
                self.structure.append(f"{self._indent()}LOG_EVENT: \"{node.args[0].value}\"")
            return

        # If it's a major operation (upload, download, split)
        args = [ast.unparse(a) for a in node.args]
        arg_str = ", ".join(args)
        if len(arg_str) > 50: arg_str = arg_str[:50] + "..."
        
        self.structure.append(f"{self._indent()}ACTION: {func_name}({arg_str})")

    def visit_FunctionDef(self, node):
        self.structure.append(f"{self._indent()}DEF FUNCTION {node.name}:")
        self.indent_level += 1
        self.generic_visit(node)
        self.indent_level -= 1

def parse_pipeline_script(file_content):
    try:
        tree = ast.parse(file_content)
        visitor = SemanticVisitor()
        # Iterate over top-level nodes
        for node in tree.body:
            visitor.visit(node)
        return "\n".join(visitor.structure)
    except Exception as e:
        return f"Error parsing script: {e}"
    
# 1. Helper to read .gitignore so we don't upload garbage
def get_gitignore_spec(path):
    gitignore_path = os.path.join(path, '.gitignore')
    if os.path.exists(gitignore_path):
         with open(gitignore_path, 'r') as f:
            return pathspec.PathSpec.from_lines('gitwildmatch', f)
    return None

# 2. The Ingestion Logic
def ingest_directory(root_path, spec):
    project_context = ""
    
    # Walk the directory
    for root, dirs, files in os.walk(root_path):
        # Remove hidden directories (like .git)
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, root_path)
            
            # Skip ignored files (node_modules, venv, etc.)
            if spec and spec.match_file(rel_path):
                continue
                
            # Only read specific extensions to save tokens
            if file.endswith(('.js', '.ts', '.java')):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # TRUNCATION STRATEGY: 
                        # For a simple version, we limit chars per file to avoid token overflow
                        # A better version would use AST to extract class names only.
                        preview = content[:2000] 
                        project_context += f"\n--- FILE: {rel_path} ---\n{preview}\n"
                except Exception:
                    continue # Skip binary files
            elif file.endswith('.py'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # --- NEW LOGIC START ---
                    # Instead of sending raw content, we parse the structure
                    skeleton = parse_pipeline_script(content)
                    project_context += f"\n--- PIPELINE: {rel_path} ---\n{skeleton}\n"
                    # --- NEW LOGIC END ---
                    
    return project_context

# 3. The Command
@app.command()
def main(
    path: str = typer.Argument(..., help="Path to your project folder"),
    api_key: str = typer.Option(..., envvar="OPENAI_API_KEY")
):
    """
    Reads a local folder and generates a Mermaid Architecture diagram.
    """
    print(f"📂 Scanning project at: {path}...")
    
    spec = get_gitignore_spec(path)
    context = ingest_directory(path, spec)
    
    print(f"📦 Context size: {len(context)} characters. Sending to LLM...")

    client = openai.OpenAI(
            api_key=api_key,
            base_url=FUEL_PROXY_URL
        )    
    
    prompt = f"""
    You are a Technical Documentation Specialist creating adoption-friendly pipeline documentation.
    
    GOAL: Generate a concise Mermaid flowchart showing WHAT the pipeline does and WHAT configuration it uses.
    Focus on extracting ACTUAL configuration values from the code, not generic descriptions.
    
    CRITICAL EXTRACTION RULES:
    1. **Look for LITERAL VALUES in the code trace**:
       - chunk_size=1000 → Use "1000", NOT "Default"
       - model="text-embedding-3-small" → Use exact model name
       - If you see a number or string literal, EXTRACT IT
    
    2. **For Config/Environment Variables - SHOW THE KEY NAME**:
       - os.getenv("BUCKET_NAME") → Use key: "BUCKET_NAME" (not {{{{BUCKET_NAME}}}})
       - Config.fetch("embedding-model") → Use key: "embedding-model"
       - os.environ["API_KEY"] → Use key: "API_KEY"
       - Format: "Config: embedding-model" or "Env: BUCKET_NAME"
       - This helps users know WHICH config to set
    
    3. **For Method Calls**:
       - RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
         → Extract: "Size: 1000, Overlap: 200"
       - OpenAIEmbeddings(model="text-embedding-3-small")
         → Extract: "Model: text-embedding-3-small"
       - If model comes from config: "Model: Config[embedding-model]"
    
    EXTRACTION TARGETS:
    - **Chunking**: Method class name, chunk_size (number), chunk_overlap (number)
    - **Embeddings**: Exact model name string, API service (OpenAI/Cohere/etc)
    - **Source**: Bucket names, file paths, collection names
    - **Storage**: 
      * File format (.pkl/.json) AND internal structure
      * For .pkl files: Specify if it's "page_content : embedding" or "langchain_doc : embedding"
      * Look for pickle.dump() calls to identify the data structure being saved
    - **Vector DB**: 
      * Service name (Pinecone/Turbopuffer/etc)
      * Namespace name (extract the actual string value, e.g., "production-docs", "dev-embeddings")
      * Index name if different from namespace
      * Look for upsert() calls and their namespace parameter
    
    OUTPUT FORMAT:
    - Use `flowchart TD`
    - Each node: 2-3 bullet points MAX
    - ALL nodes must be connected in a logical flow
    - Use cylinder shapes `[(Name)]` for databases/storage
    - Group related steps in subgraphs
    
    EXAMPLE (GOOD):
    ```
    subgraph Step2_Chunking
        C["• Method: RecursiveCharacterTextSplitter<br/>• Size: 1000 tokens, Overlap: 200<br/>• Splits by: Paragraph headers"]
    end
    
    subgraph Step3_Embedding
        D["• Model: text-embedding-3-small<br/>• Service: OpenAI API<br/>• Cache: embeddings.pkl"]
        E[(GCS Bucket)]
    end
    
    C --> D
    D --> E
    ```
    
    EXAMPLE (BAD - Don't do this):
    ```
    C["• Method: Default<br/>• Config: Default"]  ❌ Too vague!
    D["• Model: {{{{MODEL_NAME}}}}"]  ❌ Should extract actual model if in code!
    ```
    
    FLOW RULES:
    - Every node must connect to at least one other node
    - Show linear progression: Ingestion → Chunking → Embedding → Storage
    - Side branches (logging, alerts) should connect back to main flow
    - No orphaned nodes
    
    THE PARSED CODE TRACE:
    {context}
    
    Output ONLY the mermaid code. Extract ACTUAL values, not placeholders.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Clean the response
    diagram_code = response.choices[0].message.content
    diagram_code = diagram_code.replace("```mermaid", "").replace("```", "")
    # Remove any problematic Unicode characters
    diagram_code = diagram_code.encode('ascii', 'ignore').decode('ascii')
    
    # Save to a local HTML file so user can view it immediately
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Mermaid Diagram</title>
</head>
<body>
    <div class="mermaid">
{diagram_code}
    </div>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true }});
    </script>
</body>
</html>
"""
    
    with open("diagram.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print("✅ Diagram generated! Open 'diagram.html' in your browser.")
    
    # Optional: Automatically open it
    import webbrowser
    webbrowser.open("diagram.html")

if __name__ == "__main__":
    app()
