"""
Mermaid Diagram Parser
Extracts and parses Mermaid diagram structure from HTML files
"""

import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class MermaidDiagram:
    """Represents a parsed Mermaid diagram structure"""
    
    def __init__(self):
        self.nodes: Dict[str, Dict] = {}
        self.edges: List[Tuple[str, str]] = []
        self.subgraphs: Dict[str, List[str]] = {}
        self.metadata: Dict[str, str] = {}
        self.raw_mermaid: str = ""
        self.diagram_type: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation"""
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "subgraphs": self.subgraphs,
            "metadata": self.metadata,
            "diagram_type": self.diagram_type
        }


def extract_mermaid_from_html(html_path: str) -> Optional[str]:
    """
    Extract Mermaid code block from HTML file
    
    Args:
        html_path: Path to the HTML file containing Mermaid diagram
        
    Returns:
        Mermaid code as string, or None if not found
    """
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find content between <div class="mermaid"> and </div>
        pattern = r'<div class="mermaid">\s*(.*?)\s*</div>'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        return None
    except Exception as e:
        print(f"Error reading HTML file: {e}")
        return None


def parse_mermaid_diagram(mermaid_code: str) -> MermaidDiagram:
    """
    Parse Mermaid diagram code into structured format
    
    Args:
        mermaid_code: Raw Mermaid diagram code
        
    Returns:
        MermaidDiagram object with parsed structure
    """
    diagram = MermaidDiagram()
    diagram.raw_mermaid = mermaid_code
    
    lines = mermaid_code.strip().split('\n')
    if not lines:
        return diagram
    
    # Extract diagram type (e.g., "flowchart TD")
    first_line = lines[0].strip()
    if first_line.startswith('flowchart') or first_line.startswith('graph'):
        diagram.diagram_type = first_line
    
    current_subgraph = None
    
    for line in lines[1:]:  # Skip first line (diagram type)
        line = line.strip()
        
        if not line or line.startswith('%%'):  # Skip empty lines and comments
            continue
        
        # Parse subgraph start
        if line.startswith('subgraph'):
            match = re.match(r'subgraph\s+(\w+)', line)
            if match:
                current_subgraph = match.group(1)
                diagram.subgraphs[current_subgraph] = []
        
        # Parse subgraph end
        elif line == 'end':
            current_subgraph = None
        
        # Parse title/metadata nodes
        elif line.startswith('title(') or line.startswith('purpose[') or line.startswith('note['):
            match = re.match(r'(\w+)\[(.*?)\]', line)
            if match:
                key = match.group(1)
                value = match.group(2)
                diagram.metadata[key] = value
        
        # Parse node definitions
        else:
            # Try to match various node patterns
            node_patterns = [
                # Rectangle: A["content"]
                r'(\w+)\["(.*?)"\]',
                # Rectangle with HTML: A["• Item 1<br/>• Item 2"]
                r'(\w+)\["(.*?)"\]',
                # Cylinder: A[("content")] or A[(content)]
                r'(\w+)\[\("(.*?)"\)\]',
                r'(\w+)\[\((.*?)\)\]',
                # Simple rectangle: A[content]
                r'(\w+)\[(.*?)\]',
                # Rounded: A(content)
                r'(\w+)\((.*?)\)',
            ]
            
            node_matched = False
            for pattern in node_patterns:
                match = re.search(pattern, line)
                if match:
                    node_id = match.group(1)
                    content = match.group(2)
                    
                    # Determine node type
                    node_type = "rect"
                    if "[(" in line:
                        node_type = "cylinder"
                    elif "(" in line and "[" not in line:
                        node_type = "rounded"
                    
                    diagram.nodes[node_id] = {
                        "type": node_type,
                        "content": content,
                        "subgraph": current_subgraph,
                        "raw_line": line
                    }
                    
                    # Add to current subgraph
                    if current_subgraph:
                        diagram.subgraphs[current_subgraph].append(node_id)
                    
                    node_matched = True
                    break
            
            # Parse edges/connections
            if '-->' in line or '---' in line:
                # Extract node IDs from connection
                # Patterns: A --> B, A["text"] --> B["text"], etc.
                edge_match = re.search(r'(\w+)(?:\[.*?\])?\s*(?:-->|---)\s*(\w+)', line)
                if edge_match:
                    from_node = edge_match.group(1)
                    to_node = edge_match.group(2)
                    diagram.edges.append((from_node, to_node))
    
    return diagram


def get_nodes_by_subgraph(diagram: MermaidDiagram, subgraph_name: str) -> List[str]:
    """Get all node IDs in a specific subgraph"""
    return diagram.subgraphs.get(subgraph_name, [])


def get_node_content(diagram: MermaidDiagram, node_id: str) -> Optional[str]:
    """Get the content of a specific node"""
    node = diagram.nodes.get(node_id)
    return node["content"] if node else None


def find_nodes_by_keyword(diagram: MermaidDiagram, keyword: str) -> List[str]:
    """
    Find nodes containing a specific keyword in their content
    
    Args:
        diagram: Parsed MermaidDiagram object
        keyword: Keyword to search for (case-insensitive)
        
    Returns:
        List of node IDs containing the keyword
    """
    matching_nodes = []
    keyword_lower = keyword.lower()
    
    for node_id, node_data in diagram.nodes.items():
        content = node_data.get("content", "").lower()
        if keyword_lower in content:
            matching_nodes.append(node_id)
    
    return matching_nodes


def reconstruct_mermaid(diagram: MermaidDiagram, updated_nodes: Dict[str, str] = None) -> str:
    """
    Reconstruct Mermaid diagram code with optional node updates
    
    Args:
        diagram: Parsed MermaidDiagram object
        updated_nodes: Dict mapping node_id to new content (optional)
        
    Returns:
        Reconstructed Mermaid code as string
    """
    if updated_nodes is None:
        updated_nodes = {}
    
    lines = []
    
    # Add diagram type
    lines.append(diagram.diagram_type)
    lines.append("")
    
    # Add metadata nodes if present
    for key, value in diagram.metadata.items():
        lines.append(f"    {key}[{value}]")
    
    if diagram.metadata:
        lines.append("")
    
    # Track which nodes have been added
    added_nodes = set()
    
    # Add subgraphs with their nodes
    for subgraph_name, node_ids in diagram.subgraphs.items():
        lines.append(f"    subgraph {subgraph_name}")
        
        for node_id in node_ids:
            if node_id in diagram.nodes:
                node = diagram.nodes[node_id]
                
                # Use updated content if available
                content = updated_nodes.get(node_id, node["content"])
                
                # Reconstruct node based on type
                if node["type"] == "cylinder":
                    lines.append(f'        {node_id}[("{content}")]')
                elif node["type"] == "rounded":
                    lines.append(f'        {node_id}({content})')
                else:  # rectangle
                    lines.append(f'        {node_id}["{content}"]')
                
                added_nodes.add(node_id)
        
        lines.append("    end")
        lines.append("")
    
    # Add nodes not in any subgraph
    for node_id, node in diagram.nodes.items():
        if node_id not in added_nodes:
            content = updated_nodes.get(node_id, node["content"])
            
            if node["type"] == "cylinder":
                lines.append(f'    {node_id}[("{content}")]')
            elif node["type"] == "rounded":
                lines.append(f'    {node_id}({content})')
            else:
                lines.append(f'    {node_id}["{content}"]')
    
    if any(node_id not in added_nodes for node_id in diagram.nodes):
        lines.append("")
    
    # Add edges
    for from_node, to_node in diagram.edges:
        lines.append(f"    {from_node} --> {to_node}")
    
    return '\n'.join(lines)


if __name__ == "__main__":
    # Test the parser
    test_html = "diagram.html"
    if Path(test_html).exists():
        print("Testing Mermaid Parser...")
        mermaid_code = extract_mermaid_from_html(test_html)
        
        if mermaid_code:
            print("\n=== Extracted Mermaid Code ===")
            print(mermaid_code[:500] + "..." if len(mermaid_code) > 500 else mermaid_code)
            
            diagram = parse_mermaid_diagram(mermaid_code)
            
            print(f"\n=== Parsed Structure ===")
            print(f"Diagram Type: {diagram.diagram_type}")
            print(f"Total Nodes: {len(diagram.nodes)}")
            print(f"Total Edges: {len(diagram.edges)}")
            print(f"Subgraphs: {list(diagram.subgraphs.keys())}")
            print(f"Metadata: {diagram.metadata}")
            
            print("\n=== Sample Nodes ===")
            for i, (node_id, node_data) in enumerate(list(diagram.nodes.items())[:3]):
                print(f"{node_id}: {node_data['content'][:100]}...")
        else:
            print("No Mermaid code found in HTML file")
    else:
        print(f"Test file '{test_html}' not found")
