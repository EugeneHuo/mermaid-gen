"""
Change Mapper
Maps code changes from git diff to diagram nodes
"""

import re
from typing import Dict, List, Set, Tuple
from mermaid_parser import MermaidDiagram


class ChangeMapper:
    """Maps code changes to diagram nodes that need updating"""
    
    # Keywords that indicate specific pipeline steps
    STEP_KEYWORDS = {
        'chunking': ['chunk', 'split', 'textsplitter', 'chunk_size', 'chunk_overlap'],
        'embedding': ['embedding', 'embed', 'openai', 'model', 'text-embedding'],
        'storage': ['bucket', 'gcs', 'storage', 'upload', 'download'],
        'cache': ['pickle', 'pkl', 'cache', 'dump', 'load'],
        'vectordb': ['pinecone', 'turbopuffer', 'weaviate', 'upsert', 'namespace', 'index'],
        'database': ['firestore', 'mongodb', 'collection', 'document'],
        'ingestion': ['ingest', 'read', 'load', 'source', 'input'],
        'processing': ['process', 'transform', 'parse'],
    }
    
    def __init__(self, diagram: MermaidDiagram):
        self.diagram = diagram
        self.node_keywords = self._build_node_keyword_map()
    
    def _build_node_keyword_map(self) -> Dict[str, Set[str]]:
        """Build a map of node_id -> set of keywords found in that node"""
        node_keywords = {}
        
        for node_id, node_data in self.diagram.nodes.items():
            content = node_data.get('content', '').lower()
            keywords = set()
            
            # Extract keywords from content
            for step_type, step_keywords in self.STEP_KEYWORDS.items():
                for keyword in step_keywords:
                    if keyword in content:
                        keywords.add(keyword)
                        keywords.add(step_type)
            
            node_keywords[node_id] = keywords
        
        return node_keywords
    
    def map_changes_to_nodes(self, diff_data: Dict) -> List[str]:
        """
        Map code changes to diagram nodes
        
        Args:
            diff_data: Dictionary containing either:
                SEMANTIC FORMAT (preferred):
                - changes: List of semantic change objects
                - summary: Overall summary
                - changed_files: List of changed file paths
                - impact_assessment: Impact level
                
                LEGACY FORMAT (fallback):
                - changed_files: List of changed file paths
                - changed_functions: List of changed function names
                - changed_configs: Dict of config key -> new value
                - diff_text: Raw diff text
        
        Returns:
            List of node IDs that should be updated
        """
        affected_nodes = set()
        
        # Check if this is semantic diff format
        if 'changes' in diff_data and isinstance(diff_data['changes'], list):
            # Use semantic mapping (preferred)
            affected_nodes.update(self._map_semantic_changes(diff_data))
        else:
            # Fallback to legacy regex-based mapping
            affected_nodes.update(self._map_legacy_changes(diff_data))
        
        return list(affected_nodes)
    
    def _map_semantic_changes(self, semantic_diff: Dict) -> Set[str]:
        """
        Map semantic changes to diagram nodes using LLM-parsed data
        
        Args:
            semantic_diff: Semantic diff dictionary with 'changes' list
            
        Returns:
            Set of affected node IDs
        """
        affected_nodes = set()
        
        for change in semantic_diff.get('changes', []):
            component = change.get('component', '').lower()
            
            # Strategy 1: Use LLM-suggested affected nodes
            if 'affected_nodes' in change:
                for suggested_node in change['affected_nodes']:
                    # Try to find matching node IDs
                    suggested_lower = suggested_node.lower()
                    for node_id in self.diagram.nodes.keys():
                        if suggested_lower in node_id.lower() or node_id.lower() in suggested_lower:
                            affected_nodes.add(node_id)
            
            # Strategy 2: Map by component name
            for step_type, keywords in self.STEP_KEYWORDS.items():
                if component in keywords or step_type in component:
                    nodes = self._find_nodes_by_step_type(step_type)
                    affected_nodes.update(nodes)
            
            # Strategy 3: Map by field name
            field = change.get('field', '').lower()
            if field:
                for node_id, keywords in self.node_keywords.items():
                    if field in keywords or any(kw in field for kw in keywords):
                        affected_nodes.add(node_id)
        
        return affected_nodes
    
    def _map_legacy_changes(self, diff_data: Dict) -> Set[str]:
        """
        Legacy regex-based mapping (fallback)
        
        Args:
            diff_data: Legacy diff data format
            
        Returns:
            Set of affected node IDs
        """
        affected_nodes = set()
        
        # Strategy 1: Map by file name
        for file_path in diff_data.get('changed_files', []):
            file_name = file_path.split('/')[-1].lower()
            
            # Extract keywords from filename
            for step_type, keywords in self.STEP_KEYWORDS.items():
                if any(kw in file_name for kw in keywords):
                    # Find nodes related to this step
                    nodes = self._find_nodes_by_step_type(step_type)
                    affected_nodes.update(nodes)
        
        # Strategy 2: Map by function names
        for func_name in diff_data.get('changed_functions', []):
            func_lower = func_name.lower()
            
            for step_type, keywords in self.STEP_KEYWORDS.items():
                if any(kw in func_lower for kw in keywords):
                    nodes = self._find_nodes_by_step_type(step_type)
                    affected_nodes.update(nodes)
        
        # Strategy 3: Map by config changes
        for config_key in diff_data.get('changed_configs', {}).keys():
            config_lower = config_key.lower()
            
            # Direct keyword matching
            for node_id, keywords in self.node_keywords.items():
                if any(kw in config_lower for kw in keywords):
                    affected_nodes.add(node_id)
        
        # Strategy 4: Analyze diff text for specific patterns
        diff_text = diff_data.get('diff_text', '')
        if diff_text:
            affected_nodes.update(self._analyze_diff_text(diff_text))
        
        return affected_nodes
    
    def _find_nodes_by_step_type(self, step_type: str) -> List[str]:
        """Find all nodes related to a specific step type"""
        matching_nodes = []
        
        for node_id, keywords in self.node_keywords.items():
            if step_type in keywords:
                matching_nodes.append(node_id)
        
        # Also check subgraph names
        for subgraph_name, node_ids in self.diagram.subgraphs.items():
            if step_type.lower() in subgraph_name.lower():
                matching_nodes.extend(node_ids)
        
        return list(set(matching_nodes))
    
    def _analyze_diff_text(self, diff_text: str) -> Set[str]:
        """Analyze raw diff text to find affected nodes"""
        affected = set()
        
        # Look for specific config changes
        patterns = {
            r'chunk_size\s*=\s*(\d+)': 'chunking',
            r'chunk_overlap\s*=\s*(\d+)': 'chunking',
            r'model\s*=\s*["\']([^"\']+)["\']': 'embedding',
            r'namespace\s*=\s*["\']([^"\']+)["\']': 'vectordb',
            r'bucket\s*=\s*["\']([^"\']+)["\']': 'storage',
        }
        
        for pattern, step_type in patterns.items():
            if re.search(pattern, diff_text, re.IGNORECASE):
                nodes = self._find_nodes_by_step_type(step_type)
                affected.update(nodes)
        
        return affected
    
    def get_node_context(self, node_id: str) -> Dict:
        """Get full context for a node including its subgraph and connections"""
        if node_id not in self.diagram.nodes:
            return {}
        
        node = self.diagram.nodes[node_id]
        
        # Find incoming and outgoing edges
        incoming = [src for src, dst in self.diagram.edges if dst == node_id]
        outgoing = [dst for src, dst in self.diagram.edges if src == node_id]
        
        return {
            'node_id': node_id,
            'content': node['content'],
            'type': node['type'],
            'subgraph': node.get('subgraph'),
            'incoming_nodes': incoming,
            'outgoing_nodes': outgoing,
            'keywords': list(self.node_keywords.get(node_id, set()))
        }


def parse_git_diff_output(diff_output: str) -> Dict:
    """
    Parse git diff output into structured format
    
    Args:
        diff_output: Raw output from git diff command
        
    Returns:
        Dictionary with parsed diff information
    """
    result = {
        'changed_files': [],
        'changed_functions': [],
        'changed_configs': {},
        'diff_text': diff_output
    }
    
    # Extract changed files
    file_pattern = r'diff --git a/(.*?) b/'
    files = re.findall(file_pattern, diff_output)
    result['changed_files'] = files
    
    # Extract function definitions that changed
    func_pattern = r'[-+]\s*def\s+(\w+)\s*\('
    functions = re.findall(func_pattern, diff_output)
    result['changed_functions'] = list(set(functions))
    
    # Extract config changes (key=value patterns)
    config_patterns = [
        r'[-+]\s*(\w+)\s*=\s*(\d+)',  # numeric configs
        r'[-+]\s*(\w+)\s*=\s*["\']([^"\']+)["\']',  # string configs
    ]
    
    for pattern in config_patterns:
        matches = re.findall(pattern, diff_output)
        for key, value in matches:
            result['changed_configs'][key] = value
    
    return result


def calculate_change_impact(affected_nodes: List[str], total_nodes: int) -> Tuple[str, float]:
    """
    Calculate the impact level of changes
    
    Args:
        affected_nodes: List of affected node IDs
        total_nodes: Total number of nodes in diagram
        
    Returns:
        Tuple of (impact_level, percentage)
        impact_level: 'low', 'medium', 'high', or 'full'
    """
    if total_nodes == 0:
        return 'full', 100.0
    
    percentage = (len(affected_nodes) / total_nodes) * 100
    
    if percentage == 0:
        return 'none', 0.0
    elif percentage < 20:
        return 'low', percentage
    elif percentage < 50:
        return 'medium', percentage
    elif percentage < 80:
        return 'high', percentage
    else:
        return 'full', percentage


if __name__ == "__main__":
    # Test the change mapper
    from mermaid_parser import extract_mermaid_from_html, parse_mermaid_diagram
    from pathlib import Path
    
    test_html = "diagram.html"
    if Path(test_html).exists():
        print("Testing Change Mapper...")
        
        # Parse existing diagram
        mermaid_code = extract_mermaid_from_html(test_html)
        if mermaid_code:
            diagram = parse_mermaid_diagram(mermaid_code)
            mapper = ChangeMapper(diagram)
            
            # Test with sample diff data
            sample_diff = {
                'changed_files': ['chunking.py', 'embedding_service.py'],
                'changed_functions': ['split_documents', 'generate_embeddings'],
                'changed_configs': {'chunk_size': '1500', 'model': 'text-embedding-3-large'},
                'diff_text': '''
                -chunk_size = 1000
                +chunk_size = 1500
                -model = "text-embedding-3-small"
                +model = "text-embedding-3-large"
                '''
            }
            
            affected = mapper.map_changes_to_nodes(sample_diff)
            impact, percentage = calculate_change_impact(affected, len(diagram.nodes))
            
            print(f"\n=== Change Analysis ===")
            print(f"Total Nodes: {len(diagram.nodes)}")
            print(f"Affected Nodes: {len(affected)}")
            print(f"Impact Level: {impact} ({percentage:.1f}%)")
            print(f"Affected Node IDs: {affected}")
            
            if affected:
                print("\n=== Node Details ===")
                for node_id in affected[:3]:  # Show first 3
                    context = mapper.get_node_context(node_id)
                    print(f"\nNode {node_id}:")
                    print(f"  Subgraph: {context.get('subgraph')}")
                    print(f"  Content: {context.get('content', '')[:100]}...")
                    print(f"  Keywords: {context.get('keywords')}")
        else:
            print("No Mermaid code found")
    else:
        print(f"Test file '{test_html}' not found")
