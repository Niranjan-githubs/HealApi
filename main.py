import argparse
import os
import json
import logging
from modules import diff_engine, test_analyzer, healing_engine, test_runner, report_generator
from modules import openapi_typo_linter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="HealAPI: Self-Healing API Test Automation System")
    parser.add_argument('--old-spec', required=True, help='Path to old OpenAPI spec (YAML/JSON)')
    parser.add_argument('--new-spec', required=True, help='Path to new OpenAPI spec (YAML/JSON)')
    parser.add_argument('--test-type', required=True, choices=['pytest', 'postman'], help='Type of tests to analyze and run')
    parser.add_argument('--test-path', required=True, help='Path to test directory (pytest) or Postman collection (postman)')
    parser.add_argument('--env-path', help='Path to Postman environment file (optional, for postman only)')
    parser.add_argument('--report-path', help='Path to save the final report (optional)')
    parser.add_argument('--llm-model', help='LLM model name for advanced healing (optional)')
    parser.add_argument('--healed-collection-path', help='(Postman only) Path to save the healed Postman collection (optional)')
    parser.add_argument('--llm-key-var', default='TOGETHER_API_KEY', help='Environment variable for LLM API key (optional, default: TOGETHER_API_KEY)')
    args = parser.parse_args()

    # Typo linting step before diff
    print("[0/5] Linting OpenAPI specs for typos...")
    old_typos = openapi_typo_linter.find_typos_in_yaml(args.old_spec)
    new_typos = openapi_typo_linter.find_typos_in_yaml(args.new_spec)
    if old_typos or new_typos:
        print("Possible typos found in OpenAPI specs:")
        if old_typos:
            print(f"- {args.old_spec}:")
            for t in old_typos:
                print(f"  {t['path']}: '{t['typo']}' -> '{t['suggestion']}'")
        if new_typos:
            print(f"- {args.new_spec}:")
            for t in new_typos:
                print(f"  {t['path']}: '{t['typo']}' -> '{t['suggestion']}'")
        print("[WARNING] Typos detected. Please fix them for best results.")

    try:
        print("[1/5] Running OpenAPI diff engine...")
        old_spec = diff_engine.load_spec(args.old_spec)
        new_spec = diff_engine.load_spec(args.new_spec)
        diff = diff_engine.diff_specs(old_spec, new_spec)
        print(json.dumps(diff, indent=2))
    except Exception as e:
        logger.error(f"Failed during OpenAPI diff: {e}")
        print(f"[ERROR] Failed during OpenAPI diff: {e}")
        return

    try:
        print("[2/5] Analyzing tests for impact...")
        affected = test_analyzer.analyze_tests(args.test_type, args.test_path, diff)
        print(f"Affected tests: {affected}")
    except Exception as e:
        logger.error(f"Failed during test analysis: {e}")
        print(f"[ERROR] Failed during test analysis: {e}")
        return

    try:
        print("[3/5] Healing affected tests...")
        healing = healing_engine.heal_tests(
            args.test_type, args.test_path, affected, diff, new_spec, args.llm_model, args.llm_key_var
        )
        print(json.dumps(healing, indent=2))
    except Exception as e:
        logger.error(f"Failed during healing: {e}")
        print(f"[ERROR] Failed during healing: {e}")
        return

    try:
        print("[4/5] Running healed tests...")
        if args.test_type == 'pytest':
            test_results = test_runner.run_tests('pytest', args.test_path)
        else:
            test_results = test_runner.run_tests('postman', args.test_path, environment_path=args.env_path)
        print(json.dumps(test_results, indent=2))
    except Exception as e:
        logger.error(f"Failed during test execution: {e}")
        print(f"[ERROR] Failed during test execution: {e}")
        return

    try:
        print("[5/5] Generating report...")
        report = report_generator.generate_report(diff, healing, test_results, output_path=args.report_path)
        report_generator.print_report(report)
    except Exception as e:
        logger.error(f"Failed during report generation: {e}")
        print(f"[ERROR] Failed during report generation: {e}")
        return

if __name__ == "__main__":
    main()
