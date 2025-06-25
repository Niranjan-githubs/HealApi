import json
import os
import logging
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_pytest_files(test_dir: str, diff: Dict[str, Any]) -> List[str]:
    """
    Analyze pytest files to find tests impacted by API changes.
    Returns a list of affected test file paths.
    """
    affected = []
    changed_paths = set(diff.get("added_endpoints", []) + diff.get("removed_endpoints", []))
    changed_paths.update([c["path"] for c in diff.get("changed_endpoints", [])])
    for root, _, files in os.walk(test_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        for path in changed_paths:
                            if path in content:
                                affected.append(file_path)
                                break
                except Exception as e:
                    logger.error(f"Error reading {file_path}: {e}")
    return affected

def _traverse_postman_items(items, changed_paths, affected):
    for item in items:
        if "item" in item:
            # Folder, recurse
            _traverse_postman_items(item["item"], changed_paths, affected)
        else:
            request = item.get("request", {})
            url = request.get("url", {})
            raw_path = url.get("raw", "")
            for path in changed_paths:
                if path in raw_path:
                    affected.append(item.get("name", raw_path))
                    break

def analyze_postman_collection(collection_path: str, diff: Dict[str, Any]) -> List[str]:
    """
    Analyze a Postman collection to find requests impacted by API changes.
    Returns a list of affected request names.
    """
    affected = []
    changed_paths = set(diff.get("added_endpoints", []) + diff.get("removed_endpoints", []))
    changed_paths.update([c["path"] for c in diff.get("changed_endpoints", [])])
    try:
        with open(collection_path, "r", encoding="utf-8") as f:
            collection = json.load(f)
        items = collection.get("item", [])
        _traverse_postman_items(items, changed_paths, affected)
    except Exception as e:
        logger.error(f"Error reading or parsing Postman collection {collection_path}: {e}")
    return affected

def analyze_tests(test_type: str, test_path: str, diff: Dict[str, Any]) -> List[str]:
    """
    Analyze tests based on type and return a list of affected tests.
    """
    if test_type == "pytest":
        return analyze_pytest_files(test_path, diff)
    elif test_type == "postman":
        return analyze_postman_collection(test_path, diff)
    else:
        logger.error(f"Unknown test type: {test_type}")
        raise ValueError(f"Unknown test type: {test_type}")

# Example usage:
if __name__ == "__main__":
    with open("diff.json") as f:
        diff = json.load(f)
    affected_pytests = analyze_tests("pytest", "tests", diff)
    print("Affected pytest files:", affected_pytests)
    # affected_postman = analyze_tests("postman", "collection.json", diff)
    # print("Affected Postman requests:", affected_postman)