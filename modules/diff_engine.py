import yaml
import json
import logging
from typing import Dict, Any

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

    added = new_paths - old_paths
    removed = old_paths - new_paths
    common = old_paths & new_paths

    diff = {
        'added_endpoints': list(added),
        'removed_endpoints': list(removed),
        'changed_endpoints': [],
        'property_changes': []
    }

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