import json
import re
import logging
from typing import List, Dict, Any, Optional
from together import Together

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def heal_pytest_files(affected_files: List[str], diff: Dict[str, Any], openapi_new: Dict[str, Any], openai_model: Optional[str] = None) -> Dict[str, Any]:
    """
    Attempt to auto-fix pytest files based on API diff.
    Uses LLM (Together API) if simple rules can't fix.
    Returns a dict with healing actions.
    """
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

def heal_postman_collection(collection_path: str, diff: Dict[str, Any], openapi_new: Dict[str, Any], openai_model: Optional[str] = None) -> Dict[str, Any]:
    """
    Attempt to auto-fix Postman collection based on API diff.
    Uses LLM (Together API) if simple rules can't fix.
    Returns a dict with healing actions.
    """
    actions = []
    changed = False
    try:
        with open(collection_path, "r", encoding="utf-8") as f:
            collection = json.load(f)
        for item in collection.get("item", []):
            request = item.get("request", {})
            url = request.get("url", {})
            raw_path = url.get("raw", "")
            for change in diff.get("changed_endpoints", []):
                old_path = change["path"]
                if old_path in raw_path:
                    # Example: update method if changed
                    if "old_methods" in change and "new_methods" in change:
                        if request.get("method", "").upper() in [m.upper() for m in change["old_methods"]]:
                            request["method"] = change["new_methods"][0].upper()
                            changed = True
                            actions.append({"request": item.get("name", raw_path), "action": "patched-method"})
            # If new required property in schema, use LLM to suggest fix
            if openai_model and not changed:
                prompt = f"""The following Postman request is broken due to these OpenAPI changes: {json.dumps(diff)}\nHere is the request JSON:\n{json.dumps(request)}\nHere is the new OpenAPI schema:\n{json.dumps(openapi_new)}\nPlease suggest a fixed version that will pass with the new API spec."""
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
                        try:
                            request = json.loads(new_content)
                            changed = True
                            actions.append({"request": item.get("name", raw_path), "action": "patched-llm"})
                        except Exception as e:
                            actions.append({"request": item.get("name", raw_path), "action": "llm_failed", "error": str(e)})
                            logger.error(f"LLM output parse failed for {item.get('name', raw_path)}: {e}")
                except Exception as e:
                    actions.append({"request": item.get("name", raw_path), "action": "llm_failed", "error": str(e)})
                    logger.error(f"LLM healing failed for {item.get('name', raw_path)}: {e}")
        if changed:
            with open(collection_path, "w", encoding="utf-8") as f:
                json.dump(collection, f, indent=2)
            logger.info(f"Patched Postman collection {collection_path}")
    except Exception as e:
        logger.error(f"Error healing Postman collection {collection_path}: {e}")
        actions.append({"collection": collection_path, "action": "error", "error": str(e)})
    return {"healed_postman_requests": actions}

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