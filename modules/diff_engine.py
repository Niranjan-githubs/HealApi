import yaml
import json
from typing import Dict, Any

def load_spec(path: str) -> Dict[str, Any]:
    """Load an OpenAPI spec from YAML or JSON file."""
    with open(path, 'r') as f:
        if path.endswith('.yaml') or path.endswith('.yml'):
            return yaml.safe_load(f)
        else:
            return json.load(f)

def diff_specs(old_spec: Dict[str, Any], new_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two OpenAPI specs and return a diff."""
    old_paths = set(old_spec.get('paths', {}).keys())
    new_paths = set(new_spec.get('paths', {}).keys())

    added = new_paths - old_paths
    removed = old_paths - new_paths
    common = old_paths & new_paths

    diff = {
        'added_endpoints': list(added),
        'removed_endpoints': list(removed),
        'changed_endpoints': []
    }

    # Optionally, compare methods and schemas for changed endpoints
    for path in common:
        old_methods = set(old_spec['paths'][path].keys())
        new_methods = set(new_spec['paths'][path].keys())
        if old_methods != new_methods:
            diff['changed_endpoints'].append({
                'path': path,
                'old_methods': list(old_methods),
                'new_methods': list(new_methods)
            })

    return diff

# Example usage:
if __name__ == "__main__":
    old = load_spec('old_openapi.yaml')
    new = load_spec('new_openapi.yaml')
    result = diff_specs(old, new)
    print(json.dumps(result, indent=2))