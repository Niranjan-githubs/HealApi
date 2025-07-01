from typing import Dict, Any, Optional
import json
import os

def run_newman(collection_path: str, environment_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Run a Postman collection using Newman and return results as a dict.
    """
    # Allow override via environment variable
    newman_path = os.environ.get('NEWMAN_PATH', r'C:\Users\niran\AppData\Roaming\npm\newman.cmd')
    print("DEBUG: Using newman path:", newman_path)
    # Use shell=True for .cmd files on Windows
    use_shell = newman_path.lower().endswith('.cmd')
    if use_shell:
        cmd = f'"{newman_path}" run "{collection_path}" --reporters json --reporter-json-export newman_report.json'
        if environment_path:
            cmd += f' --environment "{environment_path}"'
        print("DEBUG: Full command (shell=True):", cmd)
    else:
        cmd = [newman_path, "run", collection_path, "--reporters", "json", "--reporter-json-export", "newman_report.json"]
        if environment_path:
            cmd += ["--environment", environment_path]
        print("DEBUG: Full command (shell=False):", cmd)
    try:
        import subprocess
        if use_shell:
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        report_path = "newman_report.json"
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                report = json.load(f)
            logger.info(f"Newman run completed for {collection_path}")
            return report
        else:
            report = {"error": "newman report not found", "stdout": result.stdout, "stderr": result.stderr}
            logger.info(f"Newman run completed for {collection_path}")
            return report
    except Exception as e:
        logger.error(f"Error running newman for {collection_path}: {e}")
        return {"type": "newman", "error": str(e)} 