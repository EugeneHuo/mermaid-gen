"""
Enhanced main.py with incremental update support
This wraps the original main.py and adds incremental mode
"""

import os
import sys

# Import everything from original main
from main import *
from incremental_update import process_incremental_update

# Override the main command with incremental support
@app.command()
def main_with_incremental(
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
    entry_points_only: bool = typer.Option(False, "--entry-points-only", "-e", help="Scan only entry point files and folder structure (for new projects)"),
    force_full: bool = typer.Option(False, "--force-full", help="Force full regeneration even if incremental is possible")
):
    """
    Reads a local folder and generates a Mermaid Architecture diagram with incremental update support.
    
    Modes:
    - auto: Automatically detect if project is new or existing (checks for git and diagram.html)
    - new: Scan file names, folder structures, and entry point files only
    - incremental: Use git diff to find changed files (existing projects) - ENHANCED with Parse-Filter-Update
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
    
    # Build metadata section
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
    
    # Execute based on mode
    prompt = None
    context = None
    
    if actual_mode == "new":
        print("🎯 Scanning entry points and project structure...")
        context = ingest_entry_points_and_structure(path, spec, include_comments=include_comments)
    elif actual_mode == "incremental":
        print("🔄 Using INCREMENTAL update mode with Parse-Filter-Update logic...")
        
        # Try incremental update
        use_incremental, incremental_prompt, mode_info = process_incremental_update(
            path=path,
            include_comments=include_comments,
            debug=debug,
            force_full=force_full,
            metadata_section=metadata_section
        )
        
        if use_incremental:
            prompt = incremental_prompt
            print(f"✅ Incremental mode active - updating {len(mode_info['affected_nodes'])} node(s)")
        else:
            print(f"⚠️  {mode_info['fallback_reason']}. Falling back to full regeneration.")
            actual_mode = "full"
            context = ingest_directory(path, spec, include_comments=include_comments)
    else:  # full mode
        print("📁 Scanning all files in directory...")
        context = ingest_directory(path, spec, include_comments=include_comments)
    
    # Build prompt if not already built (incremental mode)
    if prompt is None:
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
    else:
        print(f"📦 Using incremental update prompt. Sending to LLM...")
    
    # Send to LLM
    client = openai.OpenAI(
        api_key=api_key,
        base_url=FUEL_PROXY_URL
    )
    
    print(f"🤖 Sending request to GPT-4o...")
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


# Make this the default command (no command name needed)
if __name__ == "__main__":
    # Call the function directly instead of using Typer app
    import sys
    
    # Remove the script name from argv
    sys.argv = sys.argv
    
    # Create a new Typer app with this as the default command
    standalone_app = typer.Typer()
    standalone_app.command()(main_with_incremental)
    standalone_app()
