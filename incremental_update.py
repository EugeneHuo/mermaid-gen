"""
Incremental Update Module
Handles incremental diagram updates using Parse-Filter-Update logic
"""

from typing import List, Dict
from mermaid_parser import extract_mermaid_from_html, parse_mermaid_diagram
from change_mapper import ChangeMapper, calculate_change_impact
from workflow_utils import generate_diff_context, should_use_incremental_mode


def generate_incremental_prompt(existing_diagram: str, diff_context: str, affected_nodes: List[str], 
                                node_contexts: List[Dict], metadata_section: str) -> str:
    """
    Generate targeted prompt for incremental diagram updates
    
    Args:
        existing_diagram: Current Mermaid diagram code
        diff_context: Git diff output showing changes
        affected_nodes: List of node IDs that need updating
        node_contexts: List of context dicts for affected nodes
        metadata_section: Metadata section from original prompt
        
    Returns:
        Formatted prompt for LLM
    """
    affected_nodes_str = ", ".join(affected_nodes) if affected_nodes else "None detected"
    
    node_details = ""
    for ctx in node_contexts:
        node_details += f"\n  Node {ctx['node_id']}:"
        node_details += f"\n    - Current Content: {ctx['content'][:150]}..."
        node_details += f"\n    - Subgraph: {ctx.get('subgraph', 'None')}"
        node_details += f"\n    - Keywords: {', '.join(ctx.get('keywords', []))}"
        node_details += f"\n    - Connected to: {', '.join(ctx.get('incoming_nodes', []) + ctx.get('outgoing_nodes', []))}"
    
    prompt = f"""
    You are updating an EXISTING Mermaid diagram with new code changes.
    {metadata_section}
    
    CRITICAL INSTRUCTIONS - LOCKED TEMPLATE APPROACH:
    1. **PRESERVE THE EXISTING STRUCTURE**: Keep ALL node IDs, subgraph names, and connections EXACTLY as shown
    2. **UPDATE ONLY AFFECTED NODES**: Only modify the content of nodes listed in "AFFECTED NODES" section
    3. **MAINTAIN ALL CONNECTIONS**: Do not add, remove, or modify any arrows/edges
    4. **KEEP UNAFFECTED NODES UNCHANGED**: Copy them exactly as they appear in the existing diagram
    5. **EXTRACT ACTUAL VALUES**: For affected nodes, extract real configuration values from the diff context
    
    EXISTING DIAGRAM (LOCKED TEMPLATE):
    ```mermaid
{existing_diagram}
    ```
    
    AFFECTED NODES (Update these only):
    {affected_nodes_str}
    
    NODE DETAILS:
    {node_details}
    
    CODE CHANGES (from git diff):
    ```
{diff_context[:3000]}
    ```
    
    TASK:
    1. Analyze the code changes in the diff context
    2. Extract NEW configuration values (chunk_size, model names, etc.)
    3. Update ONLY the affected nodes with the new values
    4. Keep everything else EXACTLY the same
    5. Output the COMPLETE updated diagram
    
    EXAMPLE OF WHAT TO DO:
    If chunk_size changed from 1000 to 1500 in the diff:
    - Find the node containing "chunk_size" or "Chunking"
    - Update that node's content: "• Size: 1000" → "• Size: 1500"
    - Keep all other nodes, connections, and structure unchanged
    
    Output ONLY the complete Mermaid code with updates applied.
    """
    
    return prompt


def process_incremental_update(path: str, include_comments: bool = False, debug: bool = False,
                               force_full: bool = False, metadata_section: str = "", api_key: str = None) -> tuple:
    """
    Process incremental diagram update
    
    Args:
        path: Repository path
        include_comments: Whether to include comments in parsing
        debug: Enable debug output
        force_full: Force full regeneration
        metadata_section: Metadata section for prompt
        api_key: OpenAI API key for semantic diff parsing
        
    Returns:
        Tuple of (use_incremental, prompt_or_context, mode_info)
        - use_incremental: bool indicating if incremental mode should be used
        - prompt_or_context: Either the incremental prompt or fallback context
        - mode_info: Dict with mode details for debugging
    """
    import os
    
    mode_info = {
        'mode': 'incremental',
        'affected_nodes': [],
        'impact_level': 'none',
        'impact_percentage': 0.0,
        'fallback_reason': None
    }
    
    # Check if we should use incremental mode
    if force_full:
        mode_info['fallback_reason'] = "--force-full flag set"
        return False, None, mode_info
    
    use_incremental, reason = should_use_incremental_mode(path, threshold=0.5, api_key=api_key)
    
    if not use_incremental:
        mode_info['fallback_reason'] = reason
        return False, None, mode_info
    
    print(f"✅ {reason}")
    
    # Parse existing diagram
    diagram_path = os.path.join(path, "diagram.html")
    existing_mermaid = extract_mermaid_from_html(diagram_path)
    
    if not existing_mermaid:
        mode_info['fallback_reason'] = "Could not parse existing diagram"
        return False, None, mode_info
    
    diagram = parse_mermaid_diagram(existing_mermaid)
    
    print(f"📊 Existing diagram: {len(diagram.nodes)} nodes, {len(diagram.edges)} connections")
    
    # Generate diff context with semantic parsing
    diff_output, diff_data = generate_diff_context(path, api_key=api_key)
    
    if not diff_output:
        mode_info['fallback_reason'] = "Could not generate diff context"
        return False, None, mode_info
    
    # Map changes to nodes
    mapper = ChangeMapper(diagram)
    affected_nodes = mapper.map_changes_to_nodes(diff_data)
    impact_level, percentage = calculate_change_impact(affected_nodes, len(diagram.nodes))
    
    mode_info['affected_nodes'] = affected_nodes
    mode_info['impact_level'] = impact_level
    mode_info['impact_percentage'] = percentage
    
    print(f"🎯 Affected nodes: {affected_nodes}")
    print(f"📈 Impact: {impact_level} ({percentage:.1f}%)")
    
    # Get context for affected nodes
    node_contexts = [mapper.get_node_context(node_id) for node_id in affected_nodes]
    
    # Generate incremental prompt
    prompt = generate_incremental_prompt(
        existing_diagram=existing_mermaid,
        diff_context=diff_output,
        affected_nodes=affected_nodes,
        node_contexts=node_contexts,
        metadata_section=metadata_section
    )
    
    # Save debug info if requested
    if debug:
        debug_file = "incremental_update_debug.txt"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write("="*80 + "\n")
            f.write("INCREMENTAL UPDATE DEBUG\n")
            f.write("="*80 + "\n\n")
            f.write(f"Affected Nodes: {affected_nodes}\n")
            f.write(f"Impact: {impact_level} ({percentage:.1f}%)\n\n")
            f.write("="*80 + "\n")
            f.write("EXISTING DIAGRAM:\n")
            f.write("="*80 + "\n\n")
            f.write(existing_mermaid + "\n\n")
            f.write("="*80 + "\n")
            f.write("DIFF CONTEXT:\n")
            f.write("="*80 + "\n\n")
            f.write(diff_output[:2000] + "\n\n")
            f.write("="*80 + "\n")
            f.write("NODE CONTEXTS:\n")
            f.write("="*80 + "\n\n")
            for ctx in node_contexts:
                f.write(f"Node {ctx['node_id']}:\n")
                f.write(f"  Content: {ctx['content']}\n")
                f.write(f"  Subgraph: {ctx.get('subgraph')}\n")
                f.write(f"  Keywords: {ctx.get('keywords')}\n\n")
            f.write("="*80 + "\n")
            f.write("PROMPT SENT TO LLM:\n")
            f.write("="*80 + "\n\n")
            f.write(prompt)
        print(f"📝 Debug mode: Incremental update details saved to '{debug_file}'")
    
    return True, prompt, mode_info
