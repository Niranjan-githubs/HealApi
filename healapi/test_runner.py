# ...existing code from modules/test_runner.py...
import subprocess
import json
import os
import logging
from typing import Dict, Any, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_pytest(test_dir: str, extra_args: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Run pytest on the given directory and return results as a dict.
    """
    cmd = ["pytest", test_dir, "--json-report", "--json-report-file=pytest_report.json"]
    if extra_args:
        cmd.extend(extra_args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        report_path = os.path.join(test_dir, "pytest_report.json")
        if os.path.exists(report_path):
            with open(report_path, "r") as f:
                report = json.load(f)
            os.remove(report_path)
        else:
            report = {"error": "pytest report not found", "stdout": result.stdout, "stderr": result.stderr}
        logger.info(f"Pytest run completed for {test_dir}")
        return {
            "type": "pytest",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "report": report
        }
    except Exception as e:
        logger.error(f"Error running pytest for {test_dir}: {e}")
        return {"type": "pytest", "error": str(e)}

def run_newman(collection_path: str, environment_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Run a Postman collection using Newman and return results as a dict.
    """
    newman_path = os.environ.get('NEWMAN_PATH', r'C:\Users\niran\AppData\Roaming\npm\newman.cmd')
    is_cmd = newman_path.lower().endswith('.cmd')
    cmd_list = [newman_path, "run", collection_path, "--reporters", "json", "--reporter-json-export", "newman_report.json"]
    if environment_path:
        cmd_list.extend(["--environment", environment_path])
    if is_cmd:
        # Use cmd.exe /c to run the .cmd file
        cmd = ['cmd.exe', '/c'] + cmd_list
        shell = False
    else:
        cmd = cmd_list
        shell = False
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=shell)
        report_path = "newman_report.json"
        if os.path.exists(report_path):
            with open(report_path, "r") as f:
                report = json.load(f)
            os.remove(report_path)
        else:
            report = {"error": "newman report not found", "stdout": result.stdout, "stderr": result.stderr}
        logger.info(f"Newman run completed for {collection_path}")
        return {
            "type": "newman",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "report": report
        }
    except Exception as e:
        logger.error(f"Error running newman for {collection_path}: {e}")
        return {"type": "newman", "error": str(e)}

def run_tests(test_type: str, test_path: str, **kwargs) -> Dict[str, Any]:
    """
    Run tests based on type ('pytest' or 'postman') and return results.
    """
    if test_type == "pytest":
        return run_pytest(test_path, kwargs.get("extra_args"))
    elif test_type == "postman":
        return run_newman(test_path, kwargs.get("environment_path"))
    else:
        logger.error(f"Unknown test type: {test_type}")
        return {"error": f"Unknown test type: {test_type}"}

# Example usage:
if __name__ == "__main__":
    # Example: Run pytest tests in 'tests/' directory
    pytest_results = run_tests("pytest", "tests")
    print(json.dumps(pytest_results, indent=2))

    # Example: Run Postman collection (uncomment and set path)
    # postman_results = run_tests("postman", "collection.json", environment_path="env.json")
    # print(json.dumps(postman_results, indent=2))