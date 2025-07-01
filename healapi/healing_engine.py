# ...existing code from modules/healing_engine.py...
import json
import re
import logging
import os
from typing import List, Dict, Any, Optional
from together import Together
import ast
import astor
import difflib
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional, but recommended

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set Together API key and default model if not already set
def _ensure_together_api_key_and_model(openai_model: Optional[str], llm_key_var: str) -> str:
    if not os.environ.get(llm_key_var):
        error_msg = f"{llm_key_var} not set. Please create a .env file with {llm_key_var}=your-key or set it in your environment."
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    if not openai_model:
        openai_model = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
        logger.info(f"Set Together model to {openai_model} by default.")
    return openai_model

def _extract_json_from_llm_response(response_text: str) -> str:
    """
    Extract the first JSON code block from an LLM response (markdown or plain).
    """
    # Try to find a ```json ... ``` code block
    match = re.search(r"```json\s*([\s\S]+?)```", response_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback: try to find any {...} block at the start of a line
    match = re.search(r"(\{[\s\S]+\})", response_text)
    if match:
        return match.group(1).strip()
    return response_text.strip()

def heal_pytest_files(affected_files: List[str], diff: Dict[str, Any], openapi_new: Dict[str, Any], openai_model: Optional[str] = None, llm_key_var: str = "TOGETHER_API_KEY") -> Dict[str, Any]:
    """
    Improved: Use AST to update endpoint paths, methods, and assertions in pytest files.
    Uses LLM (Together API) only for complex cases.
    Returns a dict with healing actions.
    """
    openai_model = _ensure_together_api_key_and_model(openai_model, llm_key_var)
    actions = []
    for file_path in affected_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            original_source = source
            tree = ast.parse(source)
            changed = False

            class HealVisitor(ast.NodeTransformer):
                def visit_Call(self, node):
                    # Update HTTP method calls (e.g., requests.get/post/put)
                    if isinstance(node.func, ast.Attribute) and node.func.attr in ["get", "post", "put", "delete", "patch"]:
                        # Check if the URL/path matches a changed/renamed endpoint
                        if node.args and isinstance(node.args[0], ast.Str):
                            old_path = node.args[0].s
                            # Find new path from diff
                            for change in diff.get("changed_endpoints", []):
                                if old_path == change.get("path") and "new_path" in change:
                                    node.args[0] = ast.Str(s=change["new_path"])
                                    nonlocal changed
                                    changed = True
                            # Update method if changed
                            for change in diff.get("changed_endpoints", []):
                                if node.func.attr in change.get("old_methods", []):
                                    node.func.attr = change.get("new_methods", [node.func.attr])[0]
                                    changed = True
                    return self.generic_visit(node)

                def visit_Assert(self, node):
                    # Update assertions on response properties
                    # e.g., assert response.json()["old_prop"] == ...
                    # Use diff to update property names
                    if isinstance(node.test, ast.Compare):
                        left = node.test.left
                        if (
                            isinstance(left, ast.Subscript)
                            and isinstance(left.value, ast.Call)
                            and hasattr(left.value.func, "attr")
                            and left.value.func.attr == "json"
                        ):
                            if isinstance(left.slice, ast.Index) and isinstance(left.slice.value, ast.Str):
                                old_prop = left.slice.value.s
                                for prop_change in diff.get("property_changes", []):
                                    if old_prop in prop_change.get("removed_properties", []):
                                        # Replace with new property if available
                                        new_props = prop_change.get("added_properties", [])
                                        if new_props:
                                            left.slice.value.s = new_props[0]
                                            nonlocal changed
                                            changed = True
                    return self.generic_visit(node)

            tree = HealVisitor().visit(tree)
            healed_code = astor.to_source(tree)
            # LLM fallback for complex cases
            if not changed and openai_model:
                prompt = f"""The following pytest test is broken due to these OpenAPI changes: {json.dumps(diff)}\nHere is the test code:\n{original_source}\nHere is the new OpenAPI schema:\n{json.dumps(openapi_new)}\nPlease suggest a fixed version that will pass with the new API spec."""
                try:
                    client = Together()
                    response = client.chat.completions.create(
                        model=openai_model,
                        messages=[{"role": "user", "content": prompt}],
                        stream=True
                    )
                    new_content = ""
                    for token in response:
                        if hasattr(token, 'choices'):
                            new_content += token.choices[0].delta.content or ""
                    if new_content.strip():
                        healed_code = new_content
                        changed = True
                except Exception as e:
                    logger.error(f"LLM healing failed for {file_path}: {e}")
            if changed and healed_code != original_source:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(healed_code)
                actions.append({"file": file_path, "action": "patched"})
                logger.info(f"Patched {file_path}")
            else:
                actions.append({"file": file_path, "action": "no_change"})
        except Exception as e:
            logger.error(f"Error healing {file_path}: {e}")
            actions.append({"file": file_path, "action": "error", "error": str(e)})
    return {"healed_pytest_files": actions}

def _find_renamed_endpoints(diff, old_spec, new_spec):
    """
    Heuristic: If an endpoint is removed in old and a new one is added in new, and their methods and response schemas are similar, treat as rename.
    Returns a dict: {old_path: new_path}
    """
    renames = {}
    old_paths = set(old_spec.get('paths', {}).keys())
    new_paths = set(new_spec.get('paths', {}).keys())
    removed = set(diff.get('removed_endpoints', []))
    added = set(diff.get('added_endpoints', []))
    for old_path in removed:
        for new_path in added:
            # Compare methods
            old_methods = set(old_spec['paths'][old_path].keys())
            new_methods = set(new_spec['paths'][new_path].keys())
            if old_methods & new_methods:
                # Compare response property names for first common method
                method = list(old_methods & new_methods)[0]
                def get_props(spec, path, method):
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
                old_props = get_props(old_spec, old_path, method)
                new_props = get_props(new_spec, new_path, method)
                # If property overlap is high, treat as rename
                if old_props and new_props and len(old_props & new_props) >= max(1, min(len(old_props), len(new_props))//2):
                    renames[old_path] = new_path
    return renames

def _make_postman_request_for_endpoint(path, method, new_spec):
    """
    Create a basic Postman request item for a new endpoint.
    """
    url = {
        "raw": f"{{{{apiurl}}}}{path}",
        "host": ["{{apiurl}}"],
        "path": [p for p in path.strip("/").split("/") if p]
    }
    # Try to get response properties for test script
    responses = new_spec['paths'][path][method].get('responses', {})
    test_lines = []
    for code, resp in responses.items():
        content = resp.get('content', {})
        for ctype, cval in content.items():
            schema = cval.get('schema', {})
            if 'properties' in schema:
                for prop in schema['properties']:
                    test_lines.append(f"    pm.expect(jsonData).to.have.property('{prop}');")
    test_script = [
        "pm.test(\"Response has expected properties\", function () {",
        "    var jsonData = pm.response.json();"
    ] + test_lines + ["});"] if test_lines else []
    return {
        "name": f"{method.upper()} {path}",
        "request": {
            "method": method.upper(),
            "header": [],
            "url": url
        },
        "event": [{
            "listen": "test",
            "script": {
                "type": "text/javascript",
                "exec": test_script
            }
        }] if test_script else [],
        "response": []
    }

def fuzzy_match_path(old_path, new_paths):
    best_match = None
    best_ratio = 0.0
    for new_path in new_paths:
        ratio = difflib.SequenceMatcher(None, old_path, new_path).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = new_path
    return best_match if best_ratio > 0.7 else None  # Threshold

def heal_postman_collection(collection_path: str, diff: Dict[str, Any], openapi_new: Dict[str, Any], openai_model: Optional[str] = None, llm_key_var: str = "TOGETHER_API_KEY", output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Improved: Use fuzzy matching for endpoint renames, update test scripts, handle all body modes, and use LLM only for complex cases.
    """
    openai_model = _ensure_together_api_key_and_model(openai_model, llm_key_var)
    actions = []
    changed = False
    try:
        with open(collection_path, "r", encoding="utf-8") as f:
            collection = json.load(f)

        # Get available endpoints from new spec
        available_endpoints = set()
        for path in openapi_new.get('paths', {}).keys():
            available_endpoints.add(path)

        # Handle renamed endpoints using fuzzy matching
        renames = {item['from']: item['to'] for item in diff.get("renamed_endpoints", [])}
        
        # Auto-detect renames by comparing removed and added endpoints
        removed_endpoints = set(diff.get("removed_endpoints", []))
        added_endpoints = set(diff.get("added_endpoints", []))
        
        # Try to match removed endpoints with added endpoints using fuzzy matching
        for removed_endpoint in removed_endpoints:
            best_match = fuzzy_match_path(removed_endpoint, added_endpoints)
            if best_match:
                renames[removed_endpoint] = best_match
                actions.append({"request": removed_endpoint, "action": f"auto-detected-rename-to {best_match}"})

        # Process each request in the collection
        items_to_remove = []
        for i, item in enumerate(collection.get("item", [])):
            request = item.get("request", {})
            url = request.get("url", {})
            if not isinstance(url, dict):
                continue

            raw_path_full = url.get("raw", "")
            if not raw_path_full or not isinstance(raw_path_full, str):
                continue

            raw_path = raw_path_full.replace("{{apiurl}}", "")
            
            # Check if this endpoint was renamed
            if raw_path in renames:
                new_path = renames[raw_path]
                url["raw"] = f"{{{{apiurl}}}}{new_path}"
                url["path"] = [p for p in new_path.strip("/").split("/") if p]
                item["name"] = f"{request.get('method', 'GET')} {new_path}"
                changed = True
                actions.append({"request": raw_path, "action": f"renamed-to {new_path}"})
                
                # Update test scripts to match new endpoint response structure
                _update_test_scripts_for_endpoint(item, new_path, openapi_new)
                
            # Check if this endpoint was removed and should be deleted
            elif raw_path in removed_endpoints and raw_path not in available_endpoints:
                items_to_remove.append(i)
                actions.append({"request": raw_path, "action": "removed-deleted-endpoint"})
                changed = True
                
            # Check if this endpoint still exists but needs test script updates
            elif raw_path in available_endpoints:
                _update_test_scripts_for_endpoint(item, raw_path, openapi_new)
        
        # Remove deleted endpoints (in reverse order to maintain indices)
        for i in reversed(items_to_remove):
            collection["item"].pop(i)
        
        # Handle body property changes
        for item in collection.get("item", []):
            request = item.get("request", {})
            raw_path_full = request.get("url", {}).get("raw", "")
            raw_path = raw_path_full.replace("{{apiurl}}", "")
            
            if request.get('body') and request['body'].get('mode') == 'raw':
                body_raw = request['body'].get('raw')
                if body_raw and isinstance(body_raw, str):
                    try:
                        body_json = json.loads(body_raw)
                        body_changed = False
                        for prop_change in diff.get("property_changes", []):
                            if prop_change['path'] in raw_path_full and request.get("method", "").lower() == prop_change.get('method'):
                                for prop in prop_change.get("removed_properties", []):
                                    if prop in body_json:
                                        del body_json[prop]
                                        body_changed = True
                                for prop in prop_change.get("added_properties", []):
                                    body_json[prop] = "<patched>"
                                    body_changed = True
                        if body_changed:
                            request['body']['raw'] = json.dumps(body_json, indent=2)
                            changed = True
                            actions.append({"request": item.get("name", raw_path), "action": "patched-properties"})
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse raw body as JSON for request: {item.get('name')}")
                    except Exception as e:
                        actions.append({"request": item.get("name", raw_path), "action": "property-patch-failed", "error": str(e)})

        # At the end, write the healed collection back to the original file
        with open(collection_path, "w", encoding="utf-8") as f:
            json.dump(collection, f, indent=2)
    except Exception as e:
        logger.error(f"Error healing Postman collection {collection_path}: {e}")
        actions.append({"collection": collection_path, "action": "error", "error": str(e)})
    return {"healed_postman_requests": actions, "healed_collection": collection}

def _update_test_scripts_for_endpoint(item, endpoint_path, openapi_new):
    """
    Update test scripts for a specific endpoint based on the new OpenAPI spec.
    """
    try:
        # Get the endpoint definition from the new spec
        endpoint_def = openapi_new.get('paths', {}).get(endpoint_path, {})
        if not endpoint_def:
            return
            
        # Get the method (assume GET for now)
        method = 'get'
        if method not in endpoint_def:
            return
            
        # Get response schema
        responses = endpoint_def[method].get('responses', {})
        expected_properties = set()
        
        for code, resp in responses.items():
            content = resp.get('content', {})
            for ctype, cval in content.items():
                schema = cval.get('schema', {})
                if 'properties' in schema:
                    expected_properties.update(schema['properties'].keys())
        
        # Update test scripts
        for event in item.get("event", []):
            if event.get("listen") == "test":
                script = event.get("script", {})
                if script.get("type") == "text/javascript":
                    exec_lines = script.get("exec", [])
                    new_exec_lines = []
                    
                    for line in exec_lines:
                        # Replace old property expectations with new ones
                        if "pm.expect(jsonData).to.have.property(" in line:
                            # Extract the old property name
                            import re
                            match = re.search(r"pm\.expect\(jsonData\)\.to\.have\.property\('([^']+)'\)", line)
                            if match:
                                old_prop = match.group(1)
                                # If the old property is not in expected properties, replace it
                                if old_prop not in expected_properties and expected_properties:
                                    # Use the first expected property as replacement
                                    new_prop = list(expected_properties)[0]
                                    new_line = line.replace(f"'{old_prop}'", f"'{new_prop}'")
                                    new_exec_lines.append(new_line)
                                else:
                                    new_exec_lines.append(line)
                            else:
                                new_exec_lines.append(line)
                        else:
                            new_exec_lines.append(line)
                    
                    script["exec"] = new_exec_lines
    except Exception as e:
        logger.warning(f"Error updating test scripts for {endpoint_path}: {e}")

def heal_tests(test_type: str, test_path: str, affected: List[str], diff: Dict[str, Any], openapi_new: Dict[str, Any], openai_model: Optional[str] = None, llm_key_var: str = "TOGETHER_API_KEY") -> Dict[str, Any]:
    """
    Heal tests based on type and return healing actions.
    """
    if test_type == "pytest":
        return heal_pytest_files(affected, diff, openapi_new, openai_model, llm_key_var)
    elif test_type == "postman":
        return heal_postman_collection(test_path, diff, openapi_new, openai_model, llm_key_var)
    else:
        logger.error(f"Unknown test type: {test_type}")
        raise ValueError(f"Unknown test type: {test_type}")

# Example usage:
if __name__ == "__main__":
    import sys
    with open("diff.json") as f:
        diff = json.load(f)
    with open("new_openapi.yaml") as f:
        import yaml
        openapi_new = yaml.safe_load(f)
    affected = ["tests/test_sample.py"]
    actions = heal_tests("pytest", None, affected, diff, openapi_new, openai_model="deepseek-ai/DeepSeek-V3")
    print(json.dumps(actions, indent=2))