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
def _ensure_together_api_key_and_model(openai_model: Optional[str], llm_key_var: str = "TOGETHER_API_KEY") -> str:
    if not os.environ.get(llm_key_var):
        logger.error(f"{llm_key_var} not set. Please create a .env file with {llm_key_var}=your-key or set it in your environment.")
        raise RuntimeError(f"{llm_key_var} not set. Please create a .env file with {llm_key_var}=your-key or set it in your environment.")
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

def heal_pytest_files(affected_files: List[str], diff: Dict[str, Any], openapi_new: Dict[str, Any], openai_model: Optional[str] = None, llm_key_var: str = "TOGETHER_API_KEY") -> Dict[str, Any]:
    """
    Attempt to auto-fix pytest files based on API diff.
    Uses LLM (Together API) if simple rules can't fix.
    Returns a dict with healing actions.
    """
    openai_model = _ensure_together_api_key_and_model(openai_model, llm_key_var)
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

def heal_postman_collection(collection_path: str, diff: Dict[str, Any], openapi_new: Dict[str, Any], openai_model: Optional[str] = None, llm_key_var: str = "TOGETHER_API_KEY") -> Dict[str, Any]:
    """
    Attempt to auto-fix Postman collection based on API diff.
    Uses LLM (Together API) if simple rules can't fix.
    Returns a dict with healing actions.
    """
    openai_model = _ensure_together_api_key_and_model(openai_model, llm_key_var)
    actions = []
    changed = False
    try:
        with open(collection_path, "r", encoding="utf-8") as f:
            collection = json.load(f)
        for item in collection.get("item", []):
            request = item.get("request", {})
            url = request.get("url", {})
            raw_path = url.get("raw", "")
            # Patch for property changes
            for prop_change in diff.get("property_changes", []):
                if prop_change['path'] in raw_path and request.get("method", "").lower() == prop_change['method']:
                    # Patch request body for removed/added properties
                    if request.get('body', {}).get('mode') == 'raw':
                        try:
                            body_json = json.loads(request['body']['raw'])
                            # Remove properties that were removed
                            for prop in prop_change['removed_properties']:
                                if prop in body_json:
                                    del body_json[prop]
                            # Add properties that were added (with dummy value)
                            for prop in prop_change['added_properties']:
                                body_json[prop] = "<patched>"
                            request['body']['raw'] = json.dumps(body_json)
                            changed = True
                            actions.append({"request": item.get("name", raw_path), "action": "patched-properties"})
                        except Exception as e:
                            actions.append({"request": item.get("name", raw_path), "action": "property-patch-failed", "error": str(e)})
                    # You can also patch test scripts/assertions here if needed
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
        if changed:
            with open(collection_path, "w", encoding="utf-8") as f:
                json.dump(collection, f, indent=2)
            logger.info(f"Patched Postman collection {collection_path}")
    except Exception as e:
        logger.error(f"Error healing Postman collection {collection_path}: {e}")
        actions.append({"collection": collection_path, "action": "error", "error": str(e)})
    return {"healed_postman_requests": actions}

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