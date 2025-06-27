# ...existing code from modules/report_generator.py...
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

def summarize_report(report: Dict[str, Any]) -> str:
    """
    Generate a human-readable summary of the report for quick review.
    """
    summary = []
    api_diff = report.get("api_diff", {})
    healing = report.get("healing_actions", {})
    test_results = report.get("test_results", {})

    # API Diff summary
    summary.append("[SUMMARY] API Diff:")
    if api_diff:
        changed_endpoints = api_diff.get("changed_endpoints", [])
        added_endpoints = api_diff.get("added_endpoints", [])
        removed_endpoints = api_diff.get("removed_endpoints", [])
        property_changes = api_diff.get("property_changes", [])
        summary.append(f"  Added endpoints: {len(added_endpoints)}")
        summary.append(f"  Removed endpoints: {len(removed_endpoints)}")
        summary.append(f"  Changed endpoints: {len(changed_endpoints)}")
        summary.append(f"  Property changes: {len(property_changes)}")
        if property_changes:
            summary.append("    Path         | Method | Added Properties | Removed Properties")
            summary.append("    ------------------------------------------------------------")
            for prop in property_changes:
                added = ','.join(prop.get('added_properties', []))
                removed = ','.join(prop.get('removed_properties', []))
                summary.append(f"    {prop.get('path',''):<13} | {prop.get('method',''):<6} | {added:<15} | {removed}")
    else:
        summary.append("  No differences detected.")

    # Healing summary
    summary.append("[SUMMARY] Healing Actions:")
    if healing:
        for k, v in healing.items():
            summary.append(f"  {k}: {len(v) if hasattr(v, '__len__') else v}")
    else:
        summary.append("  No healing actions performed.")

    # Test results summary (tabular)
    summary.append("[SUMMARY] Test Results:")
    stats = None
    if test_results and 'report' in test_results and 'run' in test_results['report']:
        stats = test_results['report']['run']['stats']
    if stats:
        table = []
        table.append("┌─────────────────────────┬──────────┬──────────┐")
        table.append("│                         │ executed │   failed │")
        table.append("├─────────────────────────┼──────────┼──────────┤")
        for key, label in zip(["iterations", "items", "requests", "testScripts", "prerequestScripts", "assertions"],
                              ["iterations", "requests", "requests", "test-scripts", "prerequest-scripts", "assertions"]):
            executed = stats.get(key, {}).get("total", 0)
            failed = stats.get(key, {}).get("failed", 0)
            table.append(f"│{label:>25} │{executed:>9} │{failed:>9} │")
            table.append("├─────────────────────────┼──────────┼──────────┤")
        table[-1] = "├─────────────────────────┴──────────┴──────────┤"
        # Duration and data
        timings = test_results['report']['run'].get('timings', {})
        duration = timings.get('completed', 0) - timings.get('started', 0)
        table.append(f"│ total run duration: {duration}ms{' ' * (25 - len(str(duration)))}│")
        table.append("├───────────────────────────────────────────────┤")
        table.append(f"│ total data received: 0B (approx)              │")
        table.append("└──────────────────────────────────────────")
        summary.extend(table)
    else:
        summary.append("  No test results available.")

    # Print errors for each request if available
    if test_results and 'report' in test_results and 'run' in test_results['report']:
        failures = test_results['report']['run'].get('failures', [])
        for fail in failures:
            item = fail.get('source', {})
            name = item.get('name', 'Unknown')
            method = item.get('request', {}).get('method', '')
            url = item.get('request', {}).get('url', {}).get('host', [''])[0] + '/' + '/'.join(item.get('request', {}).get('url', {}).get('path', []))
            error = fail.get('error', {}).get('message', '')
            summary.append(f"\n{name}\n  {method} {url} [errored]\n     {error}")

    # Add per-endpoint test pass/fail table
    summary.append(summarize_test_pass_fail(report))
    return "\n".join(summary)

def summarize_test_pass_fail(report: dict) -> str:
    """
    Add a table of test pass/fail per endpoint to the summary.
    """
    test_results = report.get("test_results", {})
    endpoint_results = []
    # Try to extract per-request results from newman report
    if test_results and 'report' in test_results and 'run' in test_results['report']:
        executions = test_results['report']['run'].get('executions', [])
        for exec in executions:
            name = exec.get('item', {}).get('name', 'Unknown')
            assertions = exec.get('assertions', [])
            if not assertions:
                status = 'Not tested'
            elif any(a.get('error') for a in assertions):
                status = 'Fail'
            else:
                status = 'Pass'
            endpoint_results.append((name, status))
    if not endpoint_results:
        return "No per-endpoint test results available."
    # Build table
    lines = ["\n[SUMMARY] Test Pass/Fail by Endpoint:",
             "| Endpoint/Test        | Result |",
             "|----------------------|--------|"]
    for name, status in endpoint_results:
        lines.append(f"| {name:<20} | {status:<6} |")
    return "\n".join(lines)

def generate_natural_summary(report: Dict[str, Any]) -> str:
    """
    Generate a natural language, paragraph-style summary of the report for easy reading.
    """
    api_diff = report.get("api_diff", {})
    healing = report.get("healing_actions", {})
    test_results = report.get("test_results", {})

    # API Diff
    added = len(api_diff.get("added_endpoints", [])) if api_diff else 0
    removed = len(api_diff.get("removed_endpoints", [])) if api_diff else 0
    changed = len(api_diff.get("changed_endpoints", [])) if api_diff else 0

    # Healing
    total_heal = len(healing) if healing else 0
    heal_details = []
    if isinstance(healing, dict):
        for k, v in healing.items():
            heal_details.append(f"{k}: {len(v) if hasattr(v, '__len__') else v}")
    heal_str = ", ".join(heal_details) if heal_details else "No healing actions performed."

    # Test Results
    passed = 0
    failed = 0
    if test_results and 'report' in test_results and 'run' in test_results['report']:
        executions = test_results['report']['run'].get('executions', [])
        for exec in executions:
            assertions = exec.get('assertions', [])
            for a in assertions:
                if a.get('error'):
                    failed += 1
                else:
                    passed += 1
    summary = (
        f"In this HealAPI run, {added} endpoints were added, {removed} endpoints were removed, and {changed} endpoints were changed in your API. "
        f"A total of {total_heal} healing actions were performed ({heal_str}). "
        f"After healing, {passed} tests passed and {failed} tests failed. "
        "For more details, please refer to the full report above or the JSON file if you specified --report-path."
    )
    return summary

# Example usage:
if __name__ == "__main__":
    with open("diff.json") as f:
        diff = json.load(f)
    with open("healing.json") as f:
        healing = json.load(f)
    with open("test_results.json") as f:
        test_results = json.load(f)
    report = generate_report(diff, healing, test_results)
    print(generate_natural_summary(report))