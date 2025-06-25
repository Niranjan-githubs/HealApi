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

def diff_specs(old_spec: Dict[str, Any], new_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two OpenAPI specs and return a diff."""
    try:
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
        logger.info("Diff computed between specs")
        return diff
    except Exception as e:
        logger.error(f"Error during spec diff: {e}")
        raise

# Example usage:
if __name__ == "__main__":
    old = load_spec('old_openapi.yaml')
    new = load_spec('new_openapi.yaml')
    result = diff_specs(old, new)
    print(json.dumps(result, indent=2))