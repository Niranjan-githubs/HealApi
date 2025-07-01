# ...existing code from modules/diff_engine.py...
import yaml
import json
import logging
from typing import Dict, Any
from difflib import SequenceMatcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_spec(path: str) -> Dict[str, Any]:
    """Load an OpenAPI spec from YAML or JSON file."""
    try:
        with open(path, 'r') as f:
            if path.endswith('.yaml') or path.endswith('.yml'):
                spec = yaml.safe_load(f)
            else:
                spec = json.load(f)
        logger.info(f"Loaded spec from {path}")
        return spec
    except Exception as e:
        logger.error(f"Failed to load spec from {path}: {e}")
        raise

def get_schema_properties(spec, path, method):
    try:
        responses = spec['paths'][path][method].get('responses', {})
        for code, resp in responses.items():
            content = resp.get('content', {})
            for ctype, cval in content.items():
                schema = cval.get('schema', {})
                if 'properties' in schema:
                    return set(schema['properties'].keys())
        return set()
    except Exception:
        return set()

def diff_specs(old_spec: Dict[str, Any], new_spec: Dict[str, Any]) -> Dict[str, Any]:
    old_paths = set(old_spec.get('paths', {}).keys())
    new_paths = set(new_spec.get('paths', {}).keys())

    added = list(new_paths - old_paths)
    removed = list(old_paths - new_paths)
    
    renamed = []
    still_added = []
    still_removed = list(removed)

    for p_add in added:
        best_match = None
        highest_score = 0.7  # Similarity threshold

        add_methods = set(new_spec['paths'][p_add].keys())
        add_props = get_schema_properties(new_spec, p_add, list(add_methods)[0]) if add_methods else set()

        for p_rem in still_removed:
            rem_methods = set(old_spec['paths'][p_rem].keys())
            
            if not add_methods.isdisjoint(rem_methods):
                # Advanced score: path similarity + property similarity
                path_ratio = SequenceMatcher(None, p_rem, p_add).ratio()
                
                rem_props = get_schema_properties(old_spec, p_rem, list(rem_methods)[0]) if rem_methods else set()
                prop_ratio = 0
                if add_props and rem_props:
                    prop_ratio = len(add_props.intersection(rem_props)) / len(add_props.union(rem_props))
                
                # Combine scores (weights can be tuned)
                score = 0.6 * path_ratio + 0.4 * prop_ratio
                
                if score > highest_score:
                    highest_score = score
                    best_match = p_rem
        
        if best_match:
            renamed.append({"from": best_match, "to": p_add})
            still_removed.remove(best_match)
        else:
            still_added.append(p_add)

    diff = {
        'added_endpoints': still_added,
        'removed_endpoints': still_removed,
        'renamed_endpoints': renamed,
        'changed_endpoints': [],
        'property_changes': []
    }

    common = old_paths & new_paths
    for path in common:
        old_methods = set(old_spec['paths'][path].keys())
        new_methods = set(new_spec['paths'][path].keys())
        method_changes = old_methods ^ new_methods
        if method_changes:
            diff['changed_endpoints'].append({
                'path': path,
                'old_methods': list(old_methods),
                'new_methods': list(new_methods)
            })
        # Property-level diff for common methods
        for method in old_methods & new_methods:
            old_props = get_schema_properties(old_spec, path, method)
            new_props = get_schema_properties(new_spec, path, method)
            added_props = new_props - old_props
            removed_props = old_props - new_props
            if added_props or removed_props:
                diff['property_changes'].append({
                    'path': path,
                    'method': method,
                    'added_properties': list(added_props),
                    'removed_properties': list(removed_props)
                })
    logger.info("Diff computed between specs")
    return diff

# Example usage:
if __name__ == "__main__":
    old = load_spec('old_openapi.yaml')
    new = load_spec('new_openapi.yaml')
    result = diff_specs(old, new)
    print(json.dumps(result, indent=2))