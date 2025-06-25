import json
import re
from typing import List, Dict, Any

def heal_pytest_files(affected_files: List[str], diff: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attempt to auto-fix pytest files based on API diff.
    Returns a dict with healing actions.
    """
    actions = []
    for file_path in affected_files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        original_content = content
        # Example: update removed endpoints to new ones if possible
        for change in diff.get("changed_endpoints", []):
            old_path = change["path"]
            # This is a placeholder for more advanced logic
            if old_path in content:
                content = content.replace(old_path, old_path)  # No-op, replace with real logic
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            actions.append({"file": file_path, "action": "patched"})
        else:
            actions.append({"file": file_path, "action": "no_change"})
    return {"healed_pytest_files": actions}

def heal_postman_collection(collection_path: str, diff: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attempt to auto-fix Postman collection based on API diff.
    Returns a dict with healing actions.
    """
    with open(collection_path, "r", encoding="utf-8") as f:
        collection = json.load(f)
    actions = []
    changed = False
    for item in collection.get("item", []):
        request = item.get("request", {})
        url = request.get("url", {})
        raw_path = url.get("raw", "")
        for change in diff.get("changed_endpoints", []):
            old_path = change["path"]
            # Placeholder for more advanced logic
            if old_path in raw_path:
                # Example: no-op, replace with real logic
                actions.append({"request": item.get("name", raw_path), "action": "no_change"})
                changed = True
    if changed:
        with open(collection_path, "w", encoding="utf-8") as f:
            json.dump(collection, f, indent=2)
    return {"healed_postman_requests": actions}

def heal_tests(test_type: str, test_path: str, affected: List[str], diff: Dict[str, Any]) -> Dict[str, Any]:
    """
    Heal tests based on type and return healing actions.
    """
    if test_type == "pytest":
        return heal_pytest_files(affected, diff)
    elif test_type == "postman":
        return heal_postman_collection(test_path, diff)
    else:
        raise ValueError(f"Unknown test type: {test_type}")

# Example usage:
if __name__ == "__main__":
    with open("diff.json") as f:
        diff = json.load(f)
    affected = ["tests/test_sample.py"]
    actions = heal_tests("pytest", None, affected, diff)
    print(json.dumps(actions, indent=2))