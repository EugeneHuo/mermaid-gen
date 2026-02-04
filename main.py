import os
import typer
import openai
import pathspec
from pathlib import Path
import tokenize
import io
import subprocess
import json
from typing import List, Dict, Optional

app = typer.Typer()
FUEL_PROXY_URL = "https://api-beta.fuelix.ai"

import ast

# Entry point detection patterns
ENTRY_POINT_PATTERNS = {
    'python': ['main.py', 'app.py', '__main__.py', 'run.py', 'pipeline.py'],
    'javascript': ['index.js', 'app.js', 'main.js', 'server.js'],
    'typescript': ['index.ts', 'app.ts', 'main.ts', 'server.ts'],
    'java': ['Main.java', 'App.java', 'Application.java']
}

# Comment extraction function
def extract_comments_with_context(source_code: str) -> List[Dict]:
    """Extract comments with their line numbers and categorize them"""
    comments = []
    
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source_code).readline)
        
        for token in tokens:
            if token.type == tokenize.COMMENT:
                comment_text = token.string.strip('#').strip()
                
                # Skip empty comments
                if not comment_text:
                    continue
                
                # Categorize comments
                if comment_text.startswith('=') or comment_text.startswith('-'):
                    comment_type = 'section_header'
                elif comment_text.upper().startswith(('TODO', 'FIXME', 'HACK', 'XXX')):
                    comment_type = 'todo'  # Skip these
                elif comment_text.upper().startswith('STEP') or 'STEP' in comment_text.upper()[:20]:
                    comment_type = 'step_marker'
                elif len(comment_text) > 100:
                    comment_type = 'docstring'  # Long explanatory comment
                else:
                    comment_type = 'explanation'
                
                comments.append({
                    'line': token.start[0],
                    'text': comment_text,
                    'type': comment_type,
                    'raw': token.string
                })
    except:
        pass
    
    return comments

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
    def __init__(self, comments: List[Dict] = None):
        self.structure = []
        self.indent_level = 0
        self.comments = comments or []
        self.last_line = 0

    def _indent(self):
        return "  " * self.indent_level
    
    def _get_comments_before_line(self, line_num: int) -> List[Dict]:
        """Get comments that appear before this line"""
        relevant_comments = []
        
        # Look for comments within 2 lines before this code
        for comment in self.comments:
            if self.last_line < comment['line'] <= line_num:
                # Comment is between last processed line and current line
                if line_num - comment['line'] <= 2:  # Within 2 lines
                    # Skip TODO comments
                    if comment['type'] != 'todo':
                        relevant_comments.append(comment)
        
        return relevant_comments
    
    def _format_comment(self, comment: Dict) -> str:
        """Format comment for output"""
        if comment['type'] == 'section_header':
            return f"\n{'='*70}\n{comment['text']}\n{'='*70}"
        elif comment['type'] == 'step_marker':
            return f"\n>>> {comment['text']}"
        elif comment['type'] == 'docstring':
            # Truncate long comments
            text = comment['text'][:150] + "..." if len(comment['text']) > 150 else comment['text']
            return f"  ## {text}"
        else:
            return f"  # {comment['text']}"

    def visit_Import(self, node):
        # We can skip imports now, they clutter the logic flow
        pass

    def visit_ImportFrom(self, node):
        pass

    def visit_If(self, node):
        # Get comments before this IF statement
        if hasattr(node, 'lineno'):
            comments = self._get_comments_before_line(node.lineno)
            for comment in comments:
                self.structure.append(self._format_comment(comment))
        
        condition = ast.unparse(node.test)
        self.structure.append(f"{self._indent()}IF CHECK: {condition}")
        
        if hasattr(node, 'lineno'):
            self.last_line = node.lineno
        
        self.indent_level += 1
        self.generic_visit(node)
        self.indent_level -= 1

    def visit_Assign(self, node):
        # Get comments before this assignment
        if hasattr(node, 'lineno'):
            comments = self._get_comments_before_line(node.lineno)
            for comment in comments:
                self.structure.append(self._format_comment(comment))
        
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
            important_keywords = ['chunk_size', 'chunk_overlap', 'model', 'namespace', 'index', 'bucket', 'path', 
                                 'alias', 'collection', 'database', 'pkl', 'pickle', 'cache', 'embedding']
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
        
        # Update last processed line
        if hasattr(node, 'lineno'):
            self.last_line = node.lineno

    def visit_Call(self, node):
        # Get comments before this call
        if hasattr(node, 'lineno'):
            comments = self._get_comments_before_line(node.lineno)
            for comment in comments:
                self.structure.append(self._format_comment(comment))
        
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

def parse_pipeline_script(file_content, include_comments=False):
    try:
        # Extract comments if requested
        comments = []
        if include_comments:
            comments = extract_comments_with_context(file_content)
        
        tree = ast.parse(file_content)
        visitor = SemanticVisitor(comments=comments)
        # Iterate over top-level nodes
        for node in tree.body:
            visitor.visit(node)
        return "\n".join(visitor.structure)
    except Exception as e:
        return f"Error parsing script: {e}"

# NEW: Git diff detection functions
def is_git_repository(path):
    """Check if the path is a git repository"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def get_changed_files(path, base_ref="HEAD"):
    """Get list of changed files using git diff"""
    try:
        # Get uncommitted changes
        result = subprocess.run(
            ["git", "diff", "--name-only", base_ref],
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )
        
        changed_files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
        
        # Also get untracked files
        result_untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )
        
        untracked_files = [f.strip() for f in result_untracked.stdout.strip().split('\n') if f.strip()]
        
        all_changed = list(set(changed_files + untracked_files))
        
        # Filter for supported file types
        supported_extensions = ('.py', '.js', '.ts', '.java')
        filtered_files = [f for f in all_changed if f.endswith(supported_extensions)]
        
        return filtered_files
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

# NEW: Entry point detection functions
def detect_entry_points(path):
    """Detect entry point files in the project"""
    entry_points = []
    
    for root, dirs, files in os.walk(path):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            # Check against entry point patterns
            for lang, patterns in ENTRY_POINT_PATTERNS.items():
                if file in patterns:
                    rel_path = os.path.relpath(os.path.join(root, file), path)
                    entry_points.append({
                        'file': rel_path,
                        'language': lang,
                        'full_path': os.path.join(root, file)
                    })
    
    return entry_points

def scan_project_structure(path):
    """Scan and summarize project structure"""
    structure = {
        'directories': [],
        'file_types': {},
        'total_files': 0
    }
    
    for root, dirs, files in os.walk(path):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        rel_dir = os.path.relpath(root, path)
        if rel_dir != '.':
            structure['directories'].append(rel_dir)
        
        for file in files:
            structure['total_files'] += 1
            ext = os.path.splitext(file)[1]
            if ext:
                structure['file_types'][ext] = structure['file_types'].get(ext, 0) + 1
    
    return structure
    
# 1. Helper to read .gitignore so we don't upload garbage
def get_gitignore_spec(path):
    gitignore_path = os.path.join(path, '.gitignore')
    if os.path.exists(gitignore_path):
         with open(gitignore_path, 'r') as f:
            return pathspec.PathSpec.from_lines('gitwildmatch', f)
    return None

# 2. The Ingestion Logic
def ingest_directory(root_path, spec, include_comments=False, files_to_process=None):
    """
    Ingest directory with optional file filtering
    
    Args:
        root_path: Root directory to scan
        spec: Gitignore spec for filtering
        include_comments: Whether to include comments in parsing
        files_to_process: Optional list of specific files to process (for incremental mode)
    """
    project_context = ""
    
    # Walk the directory
    for root, dirs, files in os.walk(root_path):
        # Remove hidden directories (like .git)
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, root_path)
            
            # If specific files are provided, only process those
            if files_to_process is not None:
                if rel_path not in files_to_process and rel_path.replace('\\', '/') not in files_to_process:
                    continue
            
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
                    skeleton = parse_pipeline_script(content, include_comments=include_comments)
                    project_context += f"\n--- PIPELINE: {rel_path} ---\n{skeleton}\n"
                    # --- NEW LOGIC END ---
                    
    return project_context

def ingest_entry_points_and_structure(root_path, spec, include_comments=False):
    """
    Ingest only entry points and project structure for new projects
    """
    context = ""
    
    # 1. Scan project structure
    structure = scan_project_structure(root_path)
    context += "="*80 + "\n"
    context += "PROJECT STRUCTURE OVERVIEW\n"
    context += "="*80 + "\n"
    context += f"Total Files: {structure['total_files']}\n"
    context += f"Total Directories: {len(structure['directories'])}\n\n"
    context += "File Types Distribution:\n"
    for ext, count in sorted(structure['file_types'].items(), key=lambda x: x[1], reverse=True):
        context += f"  {ext}: {count} files\n"
    context += "\n"
    context += "Directory Structure:\n"
    for dir_path in sorted(structure['directories'])[:20]:  # Limit to first 20 dirs
        context += f"  📁 {dir_path}\n"
    context += "\n"
    
    # 2. Detect and parse entry points
    entry_points = detect_entry_points(root_path)
    context += "="*80 + "\n"
    context += "DETECTED ENTRY POINTS\n"
    context += "="*80 + "\n"
    
    if entry_points:
        for ep in entry_points:
            context += f"\n🎯 Entry Point: {ep['file']} ({ep['language']})\n"
            context += "-"*80 + "\n"
            
            # Parse the entry point file
            try:
                with open(ep['full_path'], 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if ep['file'].endswith('.py'):
                    skeleton = parse_pipeline_script(content, include_comments=include_comments)
                    context += skeleton + "\n"
                else:
                    # For non-Python files, show preview
                    preview = content[:2000]
                    context += preview + "\n"
            except Exception as e:
                context += f"Error reading file: {e}\n"
    else:
        context += "No standard entry points detected.\n"
    
    return context

# 3. The Command
@app.command()
def main(
    path: str = typer.Argument(..., help="Path to your project folder"),
    api_key: str = typer.Option(..., envvar="OPENAI_API_KEY"),
    pipeline_name: str = typer.Option(None, help="Name of the pipeline (e.g., 'Document Embedding Pipeline')"),
    pipeline_purpose: str = typer.Option(None, help="What this pipeline does (e.g., 'Processes documents and generates embeddings')"),
    data_type: str = typer.Option(None, help="Type of data being processed (e.g., 'PDF documents', 'JSON logs', 'CSV files')"),
    data_source: str = typer.Option(None, help="Where the data comes from (e.g., 'GCS bucket', 'S3', 'Local filesystem')"),
    use_case: str = typer.Option(None, help="What the pipeline is used for (e.g., 'RAG system', 'Analytics', 'ETL')"),
    team_owner: str = typer.Option(None, help="Team or person responsible for this pipeline"),
    include_comments: bool = typer.Option(False, "--include-comments", "-c", help="Include code comments in AST parsing for better context"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Save intermediate AST parsing results to ast_debug_output.txt"),
    mode: str = typer.Option("auto", "--mode", "-m", help="Scan mode: 'auto' (detect), 'new' (entry points only), 'incremental' (git diff), 'full' (all files)"),
    entry_points_only: bool = typer.Option(False, "--entry-points-only", "-e", help="Scan only entry point files and folder structure (for new projects)")
):
    """
    Reads a local folder and generates a Mermaid Architecture diagram.
    
    Modes:
    - auto: Automatically detect if project is new or existing (checks for git and diagram.html)
    - new: Scan file names, folder structures, and entry point files only
    - incremental: Use git diff to find changed files (existing projects)
    - full: Scan all files in the directory (default behavior)
    """
    print(f"📂 Scanning project at: {path}...")
    
    # Determine the actual mode to use
    actual_mode = mode
    if mode == "auto":
        # Auto-detect mode
        is_git_repo = is_git_repository(path)
        has_diagram = os.path.exists("diagram.html")
        
        if is_git_repo and has_diagram:
            actual_mode = "incremental"
            print("🔍 Auto-detected: Existing project (using incremental mode)")
        elif is_git_repo:
            actual_mode = "new"
            print("🔍 Auto-detected: New git project (using entry points mode)")
        else:
            actual_mode = "full"
            print("🔍 Auto-detected: Non-git project (using full scan mode)")
    
    # Override with entry_points_only flag if set
    if entry_points_only:
        actual_mode = "new"
    
    print(f"📋 Mode: {actual_mode}")
    
    if include_comments:
        print("💬 Comment extraction enabled - including developer comments in analysis")
    
    spec = get_gitignore_spec(path)
    
    # Execute based on mode
    if actual_mode == "new":
        print("🎯 Scanning entry points and project structure...")
        context = ingest_entry_points_and_structure(path, spec, include_comments=include_comments)
    elif actual_mode == "incremental":
        print("🔄 Detecting changed files with git diff...")
        changed_files = get_changed_files(path)
        
        if changed_files is None:
            print("⚠️  Not a git repository. Falling back to full scan mode.")
            context = ingest_directory(path, spec, include_comments=include_comments)
        elif len(changed_files) == 0:
            print("✅ No changes detected. Diagram is up to date.")
            return
        else:
            print(f"📝 Found {len(changed_files)} changed file(s):")
            for f in changed_files:
                print(f"   - {f}")
            context = ingest_directory(path, spec, include_comments=include_comments, files_to_process=changed_files)
    else:  # full mode
        print("📁 Scanning all files in directory...")
        context = ingest_directory(path, spec, include_comments=include_comments)
    
    print(f"📦 Context size: {len(context)} characters. Sending to LLM...")
    
    # Save intermediate AST parsing results if debug flag is enabled
    if debug:
        debug_file = "ast_debug_output.txt"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write("="*80 + "\n")
            f.write("INTERMEDIATE AST PARSING RESULTS\n")
            f.write("="*80 + "\n\n")
            f.write(f"Total context size: {len(context)} characters\n")
            f.write(f"Source directory: {path}\n\n")
            f.write("="*80 + "\n")
            f.write("PARSED CONTENT (sent to LLM):\n")
            f.write("="*80 + "\n\n")
            f.write(context)
            f.write("\n\n" + "="*80 + "\n")
            f.write("END OF AST PARSING RESULTS\n")
            f.write("="*80 + "\n")
        print(f"📝 Debug mode: AST parsing results saved to '{debug_file}'")

    client = openai.OpenAI(
            api_key=api_key,
            base_url=FUEL_PROXY_URL
        )
    
    # Build metadata section if any optional info is provided
    metadata_section = ""
    if any([pipeline_name, pipeline_purpose, data_type, data_source, use_case, team_owner]):
        metadata_section = "\n    PIPELINE METADATA (Use this context to enhance the diagram):\n"
        if pipeline_name:
            metadata_section += f"    - Pipeline Name: {pipeline_name}\n"
        if pipeline_purpose:
            metadata_section += f"    - Purpose: {pipeline_purpose}\n"
        if data_type:
            metadata_section += f"    - Data Type: {data_type}\n"
        if data_source:
            metadata_section += f"    - Data Source: {data_source}\n"
        if use_case:
            metadata_section += f"    - Use Case: {use_case}\n"
        if team_owner:
            metadata_section += f"    - Owner: {team_owner}\n"
    
    prompt = f"""
    You are a Technical Documentation Specialist creating adoption-friendly pipeline documentation.
    {metadata_section}
    
    GOAL: Generate a concise Mermaid flowchart showing WHAT the pipeline does and WHAT configuration it uses.
    Focus on extracting ACTUAL configuration values from the code, not generic descriptions.
    
    METADATA USAGE (IMPORTANT - Use these to enhance the diagram):
    - If Pipeline Name is provided, MUST use it as the diagram title using: title(Pipeline Name)
    - If Purpose is provided, MUST add it as an annotation below the title: purpose[Purpose: description]
    - If Data Type is provided, MUST reference it in the first ingestion node (e.g., "Type: PDF documents")
    - If Data Source is provided, MUST label it in the first ingestion node (e.g., "Source: GCS bucket")
    - If Use Case is provided, MUST add context to the final output/destination nodes (e.g., "Use: RAG system")
    - If Owner is provided, MUST add it as a note: note[Owner: Team Name]
    - Connect title/purpose/note nodes to the main flow or group them at the top
    
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
    - **Source**: Bucket names, file paths, collection names, API endpoints
    - **Cache/Intermediate Storage**: 
      * File format (.pkl/.json/.parquet) - MUST extract the actual filename if present
      * For .pkl files: Specify the data structure (e.g., "Dict[doc_id: embedding]", "List[LangChain Documents]")
      * Look for pickle.dump(), pickle.load(), or file write operations
      * Include the variable name being saved (e.g., "embeddings.pkl stores: doc_embeddings_dict")
    - **Vector DB**: 
      * Service name (Pinecone/Turbopuffer/Weaviate/etc)
      * Namespace name (extract the actual string value or config key, e.g., "production-docs" or "Config[INDEX_NAME]")
      * Index name if different from namespace
      * Alias name if used (e.g., for Turbopuffer alias or Pinecone index alias)
      * Look for upsert() calls and their namespace/alias parameters
    - **Document Storage (Firestore/MongoDB/etc)**:
      * Database/Collection name
      * Document structure or key fields being stored
      * Any alias or reference names used
      * Look for .set(), .add(), .update() operations
    
    OUTPUT FORMAT:
    - Use `flowchart TD`
    - Each node: 2-3 bullet points MAX using bullet character (•)
    - Format bullets with <br/> for line breaks: "• Item 1<br/>• Item 2<br/>• Item 3"
    - ALL nodes must be connected in a logical flow
    - Use cylinder shapes `[(Name)]` for databases/storage
    - Group related steps in subgraphs with descriptive names (e.g., Step1_Ingestion, Step2_Chunking)
    - If metadata is provided, include title/purpose/owner nodes at the top
    
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
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        seed=42
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
