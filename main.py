import argparse
import os
import json
from modules import diff_engine, test_analyzer, healing_engine, test_runner, report_generator

def main():
    parser = argparse.ArgumentParser(description="HealAPI: Self-Healing API Test Automation System")
    parser.add_argument('--old-spec', required=True, help='Path to old OpenAPI spec (YAML/JSON)')
    parser.add_argument('--new-spec', required=True, help='Path to new OpenAPI spec (YAML/JSON)')
    parser.add_argument('--test-type', required=True, choices=['pytest', 'postman'], help='Type of tests to analyze and run')
    parser.add_argument('--test-path', required=True, help='Path to test directory (pytest) or Postman collection (postman)')
    parser.add_argument('--env-path', help='Path to Postman environment file (optional, for postman only)')
    parser.add_argument('--report-path', help='Path to save the final report (optional)')
    args = parser.parse_args()

    print("[1/5] Running OpenAPI diff engine...")
    old_spec = diff_engine.load_spec(args.old_spec)
    new_spec = diff_engine.load_spec(args.new_spec)
    diff = diff_engine.diff_specs(old_spec, new_spec)
    print(json.dumps(diff, indent=2))

    print("[2/5] Analyzing tests for impact...")
    affected = test_analyzer.analyze_tests(args.test_type, args.test_path, diff)
    print(f"Affected tests: {affected}")

    print("[3/5] Healing affected tests...")
    healing = healing_engine.heal_tests(args.test_type, args.test_path, affected, diff)
    print(json.dumps(healing, indent=2))

    print("[4/5] Running healed tests...")
    if args.test_type == 'pytest':
        test_results = test_runner.run_tests('pytest', args.test_path)
    else:
        test_results = test_runner.run_tests('postman', args.test_path, environment_path=args.env_path)
    print(json.dumps(test_results, indent=2))

    print("[5/5] Generating report...")
    report = report_generator.generate_report(diff, healing, test_results, output_path=args.report_path)
    report_generator.print_report(report)

if __name__ == "__main__":
    main()
