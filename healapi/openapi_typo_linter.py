# ...existing code from modules/openapi_typo_linter.py...
import yaml
from difflib import get_close_matches

# List of valid OpenAPI keys (partial, can be extended)
VALID_KEYS = [
    'openapi', 'info', 'title', 'version', 'description', 'paths', 'get', 'post', 'put', 'delete', 'patch',
    'summary', 'responses', 'content', 'application/json', 'schema', 'type', 'properties', 'items', 'required',
    'parameters', 'in', 'name', 'example', 'examples', 'enum', 'format', 'default', 'minimum', 'maximum', 'minLength', 'maxLength', 'minItems', 'maxItems', 'oneOf', 'anyOf', 'allOf', 'not', 'nullable', 'deprecated', 'readOnly', 'writeOnly', 'externalDocs', 'reference', '$ref', 'tags', 'servers', 'security', 'components', 'requestBody', 'headers', 'description', 'operationId', 'produces', 'consumes', 'definitions', 'securitySchemes', 'securityDefinitions', 'schemes', 'host', 'basePath', 'definitions', 'parameters', 'responses', 'security', 'tags', 'externalDocs'
]

# Fuzzy match threshold
FUZZY_THRESHOLD = 0.8

def find_typos_in_yaml(yaml_path, valid_keys=VALID_KEYS, threshold=FUZZY_THRESHOLD):
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    typos = []
    def recurse(obj, path=None):
        if path is None:
            path = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k not in valid_keys:
                    matches = get_close_matches(k, valid_keys, n=1, cutoff=threshold)
                    if matches:
                        typos.append({
                            'path': '.'.join(path + [k]),
                            'typo': k,
                            'suggestion': matches[0]
                        })
                recurse(v, path + [k])
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                recurse(item, path + [str(idx)])
    recurse(data)
    return typos

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print('Usage: python openapi_typo_linter.py <openapi.yaml>')
        sys.exit(1)
    typos = find_typos_in_yaml(sys.argv[1])
    if typos:
        print('Possible typos found:')
        for t in typos:
            print(f"{t['path']}: '{t['typo']}' -> '{t['suggestion']}'")
    else:
        print('No typos found.')
