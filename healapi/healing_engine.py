# ...existing code from modules/healing_engine.py...
import json
import re
import logging
import os
from typing import List, Dict, Any, Optional
from together import Together
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional, but recommended

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set Together API key and default model if not already set
def _ensure_together_api_key_and_model(openai_model: Optional[str]) -> str:
    if not os.environ.get("TOGETHER_API_KEY"):
        logger.error("TOGETHER_API_KEY not set. Please create a .env file with TOGETHER_API_KEY=your-key or set it in your environment.")
        raise RuntimeError("TOGETHER_API_KEY not set. Please create a .env file with TOGETHER_API_KEY=your-key or set it in your environment.")
    if not openai_model:
        openai_model = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
        logger.info("Set Together model to meta-llama/Llama-3.3-70B-Instruct-Turbo-Free by default.")
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

def heal_pytest_files(affected_files: List[str], diff: Dict[str, Any], openapi_new: Dict[str, Any], openai_model: Optional[str] = None) -> Dict[str, Any]:
    """
    Attempt to auto-fix pytest files based on API diff.
    Uses LLM (Together API) if simple rules can't fix.
    Returns a dict with healing actions.
    """
    openai_model = _ensure_together_api_key_and_model(openai_model)
    actions = []
    for file_path in affected_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            original_content = content
            # Example: update method or endpoint if changed
            for change in diff.get("changed_endpoints", []):
                old_path = change["path"]
                # If method changed, try to update
                if "old_methods" in change and "new_methods" in change:
                    for method in change["old_methods"]:
                        if re.search(rf"\\b{method}\\b", content, re.IGNORECASE):
                            # Replace with new method (pick first for demo)
                            content = re.sub(rf"\\b{method}\\b", change["new_methods"][0], content, flags=re.IGNORECASE)
            # If new required property in schema, use LLM to suggest fix
            if openai_model:
                # Only call LLM if content unchanged by rules
                if content == original_content:
                    prompt = f"""The following pytest test is broken due to these OpenAPI changes: {json.dumps(diff)}\nHere is the test code:\n{content}\nHere is the new OpenAPI schema:\n{json.dumps(openapi_new)}\nPlease suggest a fixed version that will pass with the new API spec."""
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
                            content = new_content
                    except Exception as e:
                        logger.error(f"LLM healing failed for {file_path}: {e}")
            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
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

def heal_postman_collection(collection_path: str, diff: Dict[str, Any], openapi_new: Dict[str, Any], openai_model: Optional[str] = None, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Attempt to auto-fix Postman collection based on API diff.
    Uses LLM (Together API) if simple rules can't fix.
    Returns a dict with healing actions.
    Only operates in-memory, does not write to disk.
    """
    openai_model = _ensure_together_api_key_and_model(openai_model)
    actions = []
    changed = False
    try:
        with open(collection_path, "r", encoding="utf-8") as f:
            collection = json.load(f)
        # --- Renames logic ---
        import copy
        from healapi import diff_engine
        old_spec = None
        # Try to infer old_spec path from diff or collection_path
        # For now, assume old_spec is collection_path.replace('dummy_collection.json', 'old_openapi.yaml')
        old_spec_path = collection_path.replace('dummy_collection.json', 'old_openapi.yaml')
        try:
            old_spec = diff_engine.load_spec(old_spec_path)
        except Exception:
            old_spec = None
        renames = _find_renamed_endpoints(diff, old_spec, openapi_new) if old_spec else {}
        # Remove requests matching removed_endpoints (unless renamed)
        removed_endpoints = set()
        for ep in diff.get("removed_endpoints", []):
            if isinstance(ep, str):
                removed_endpoints.add((ep.strip("/"), None))
            elif isinstance(ep, dict):
                removed_endpoints.add((ep.get("path", "").strip("/"), ep.get("method", None)))
        new_items = []
        for item in collection.get("item", []):
            request = item.get("request", {})
            url = request.get("url", {})
            # Try to get the path as string
            path = None
            if isinstance(url, dict):
                if "raw" in url:
                    raw = url["raw"]
                    if raw.startswith("{{apiurl}}/"):
                        path = raw[len("{{apiurl}}/"):].strip("/")
                    else:
                        path = raw.strip("/")
                elif "path" in url:
                    path = "/".join(url["path"]).strip("/")
            method = request.get("method", None)
            # Check for rename
            full_path = f"/{path}" if path and not path.startswith("/") else path
            if full_path in renames:
                # Update path and name
                new_path = renames[full_path]
                new_method = method.lower() if method else "get"
                new_item = _make_postman_request_for_endpoint(new_path, new_method, openapi_new)
                new_items.append(new_item)
                changed = True
                actions.append({"request": item.get("name", path), "action": f"renamed-to {new_path}"})
                continue
            # Remove if not renamed and is a removed endpoint
            should_remove = False
            for ep_path, ep_method in removed_endpoints:
                if path == ep_path and (ep_method is None or (method and method.lower() == ep_method.lower())):
                    should_remove = True
                    break
            if should_remove:
                changed = True
                actions.append({"request": item.get("name", path), "action": "removed-endpoint"})
                continue
            new_items.append(item)
        collection["item"] = new_items
        # Add new requests for new endpoints
        new_paths = set(openapi_new.get('paths', {}).keys())
        old_paths = set(old_spec.get('paths', {}).keys()) if old_spec else set()
        for path in new_paths - old_paths:
            for method in openapi_new['paths'][path].keys():
                new_item = _make_postman_request_for_endpoint(path, method, openapi_new)
                collection["item"].append(new_item)
                changed = True
                actions.append({"request": f"{method.upper()} {path}", "action": "added-new-endpoint"})
        # Patch for property changes
        for item in collection.get("item", []):
            request = item.get("request", {})
            url = request.get("url", {})
            raw_path = url.get("raw", "")
            # Patch for property changes
            for prop_change in diff.get("property_changes", []):
                if prop_change['path'] in raw_path and request.get("method", "").lower() == prop_change['method']:
                    if request.get('body', {}).get('mode') == 'raw':
                        try:
                            body_json = json.loads(request['body']['raw'])
                            for prop in prop_change['removed_properties']:
                                if prop in body_json:
                                    del body_json[prop]
                            for prop in prop_change['added_properties']:
                                body_json[prop] = "<patched>"
                            request['body']['raw'] = json.dumps(body_json)
                            changed = True
                            actions.append({"request": item.get("name", raw_path), "action": "patched-properties"})
                        except Exception as e:
                            actions.append({"request": item.get("name", raw_path), "action": "property-patch-failed", "error": str(e)})
            # If new required property in schema, use LLM to suggest fix
            if openai_model and not changed:
                prompt = f"""The following Postman request is broken due to these OpenAPI changes: {json.dumps(diff)}\nHere is the request JSON:\n{json.dumps(request)}\nHere is the new OpenAPI schema:\n{json.dumps(openapi_new)}\nPlease suggest a fixed version that will pass with the new API spec. Only output the fixed request as a JSON object, no explanation."""
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
                    logger.debug(f"Raw LLM response for request '{item.get('name', raw_path)}': {new_content}")
                    print(f"[DEBUG] Raw LLM response for request '{item.get('name', raw_path)}':\n{new_content}\n")
                    if new_content.strip():
                        try:
                            json_str = _extract_json_from_llm_response(new_content)
                            request = json.loads(json_str)
                            changed = True
                            actions.append({"request": item.get("name", raw_path), "action": "patched-llm"})
                        except Exception as e:
                            actions.append({"request": item.get("name", raw_path), "action": "llm_failed", "error": str(e)})
                            logger.error(f"LLM output parse failed for {item.get('name', raw_path)}: {e}")
                except Exception as e:
                    actions.append({"request": item.get("name", raw_path), "action": "llm_failed", "error": str(e)})
                    logger.error(f"LLM healing failed for {item.get('name', raw_path)}: {e}")
        # At the end, write the healed collection back to the original file
        with open(collection_path, "w", encoding="utf-8") as f:
            json.dump(collection, f, indent=2)
    except Exception as e:
        logger.error(f"Error healing Postman collection {collection_path}: {e}")
        actions.append({"collection": collection_path, "action": "error", "error": str(e)})
    return {"healed_postman_requests": actions, "healed_collection": collection}

def heal_tests(test_type: str, test_path: str, affected: List[str], diff: Dict[str, Any], openapi_new: Dict[str, Any], openai_model: Optional[str] = None) -> Dict[str, Any]:
    """
    Heal tests based on type and return healing actions.
    """
    if test_type == "pytest":
        return heal_pytest_files(affected, diff, openapi_new, openai_model)
    elif test_type == "postman":
        return heal_postman_collection(test_path, diff, openapi_new, openai_model)
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