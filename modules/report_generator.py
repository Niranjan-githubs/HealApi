import json
import logging
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_report(diff: Dict[str, Any], healing: Dict[str, Any], test_results: Dict[str, Any], output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate a summary report of the diff, healing actions, and test results.
    Optionally write to a file.
    """
    report = {
        "api_diff": diff,
        "healing_actions": healing,
        "test_results": test_results
    }
    if output_path:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            logger.info(f"Report written to {output_path}")
        except Exception as e:
            logger.error(f"Failed to write report to {output_path}: {e}")
    return report

def print_report(report: Dict[str, Any]):
    """
    Print the report in a readable format.
    """
    try:
        print("==== API Diff ====")
        print(json.dumps(report.get("api_diff", {}), indent=2))
        print("\n==== Healing Actions ====")
        print(json.dumps(report.get("healing_actions", {}), indent=2))
        print("\n==== Test Results ====")
        print(json.dumps(report.get("test_results", {}), indent=2))
    except Exception as e:
        logger.error(f"Error printing report: {e}")

# Example usage:
if __name__ == "__main__":
    with open("diff.json") as f:
        diff = json.load(f)
    with open("healing.json") as f:
        healing = json.load(f)
    with open("test_results.json") as f:
        test_results = json.load(f)
    report = generate_report(diff, healing, test_results)
    print_report(report)