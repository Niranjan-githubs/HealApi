# healapi

## Self-Healing API Test Automation System

HealAPI is a robust CLI tool for detecting and healing breaking changes in APIs using OpenAPI specs and Postman collections. It is designed to be beginner-friendly and easy to set up for testers and developers.

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.8+** must be installed. [Download Python](https://www.python.org/downloads/)
- (Recommended) Create and activate a virtual environment:
  - **Windows:**
    ```sh
    python -m venv newenv
    newenv\Scripts\activate
    ```
  - **Mac/Linux:**
    ```sh
    python3 -m venv newenv
    source newenv/bin/activate
    ```

### 2. Install HealAPI
From the project root directory:
- **Windows/Mac/Linux:**
  ```sh
  pip install -e .
  ```

---

## 📝 What You Need

HealAPI requires **two files** to run:
1. **Postman Collection** (your API tests, exported as JSON)
2. **OpenAPI Spec** (YAML or JSON)

### How to Get These Files

#### 1. Postman Collection
- Create or open your API tests in Postman.
- Click the collection name > Export > Choose JSON format.
- [Step-by-step guide](https://learning.postman.com/docs/getting-started/creating-the-first-collection/)

#### 2. OpenAPI Spec
If you do not have an OpenAPI spec, generate one from your Postman collection using one of these methods:
- **Postman App**: Import your collection, then use the 'Export OpenAPI' feature. [Guide](https://learning.postman.com/docs/integrations/available-integrations/working-with-openAPI/)
- **Online Tool**: [APIMatic Converter](https://www.apimatic.io/postman-to-openapi-converter)
- **CLI Tool**: [postman2openapi](https://github.com/joolfe/postman-to-openapi) (requires Node.js)

**You must have both files before running HealAPI.**

---

## 🏃 How to Run HealAPI

### Basic Command
- **Windows/Mac/Linux:**
  ```sh
  healapi --old-spec path/to/old_openapi.yaml --new-spec path/to/new_openapi.yaml --test-type postman --test-path path/to/collection.json --report-path path/to/report.json
  ```

### Arguments Explained
- `--old-spec`: Path to your old OpenAPI spec (YAML/JSON)
- `--new-spec`: Path to your new OpenAPI spec (YAML/JSON)
- `--test-type`: `postman` (for Postman collections) or `pytest` (for pytest tests)
- `--test-path`: Path to your Postman collection JSON or pytest directory
- `--env-path`: (Optional) Path to Postman environment file
- `--report-path`: (Optional) Path to save the final report (JSON)
- `--llm-model`: (Optional) LLM model name for advanced healing

### Example
- **Windows:**
  ```sh
  healapi --old-spec project\old_openapi.yaml --new-spec project\new_openapi.yaml --test-type postman --test-path project\dummy_collection.json --env-path project\dummy_env.json --report-path healapi_report.json
  ```
- **Mac/Linux:**
  ```sh
  healapi --old-spec project/old_openapi.yaml --new-spec project/new_openapi.yaml --test-type postman --test-path project/dummy_collection.json --env-path project/dummy_env.json --report-path healapi_report.json
  ```

---

## 📄 Output Files & Reports

When you run HealAPI, it generates a detailed report (JSON) summarizing:
- API differences (added/removed/changed endpoints)
- Healing actions taken
- Test results (passed/failed)

### Where to Find the Report
- **Terminal Output:**
  - A quick summary, a natural language paragraph, and the full report are printed in your terminal after each run.
- **Report File:**
  - If you use `--report-path`, the full report is saved as a JSON file at the path you specify (e.g., `--report-path healapi_report.json`).
  - Open this file in any text editor or JSON viewer for in-depth analysis.

### Report Summary & Natural Language Explanation
- **Summary:**
  - Shows counts of endpoints added/removed/changed, healing actions, and test results.
- **Natural Language Summary:**
  - A paragraph-style explanation is printed for easy reading, summarizing the main results in plain English.

**Tip:** Use the summary and natural language explanation for a quick overview, and refer to the full report for debugging or audit purposes.

---

## 🧪 Running Tests Directly (Without HealAPI)

If you want to see how your tests behave before healing, you can run your Postman collection directly with Newman:

```sh
newman run project/dummy_collection.json --env-var "apiurl=localhost:5000" --reporters cli
```

- Replace `localhost:5000` with your actual API host and port.
- This will show you any failures due to breaking changes in your API.

## 🩺 Healing and Running with HealAPI

After running HealAPI, you can:
- Review the summary and tabular test results in your terminal.
- (If you used `--healed-collection-path`) Run the healed collection with:

```sh
newman run project/healed_collection.json --env-var "apiurl=localhost:5000" --reporters cli
```

## 🔄 What Changed in HealAPI
- Added robust summary and tabular reporting for API diffs, property changes, and test results.
- Added support for saving a healed Postman collection with `--healed-collection-path`.
- Improved error reporting for missing environment variables (like `apiurl`).
- The README now includes clear instructions for both direct and healed test runs.

---

## 🛠️ Troubleshooting & Tips
- If you see `command not found: healapi`, try `python -m healapi.cli ...` (or `python3 -m healapi.cli ...` on Mac/Linux) instead.
- Make sure your virtual environment is activated if you installed locally.
- If you get file not found errors, double-check your file paths and extensions.
- For Windows users, use backslashes (`\`) in paths or wrap paths in quotes if they contain spaces.
- For Mac/Linux users, use forward slashes (`/`) in paths and check file permissions if you get access errors.

---

## 👩‍💻 For Developers
- All source code is in the `healapi/` package.
- CLI entry point: `healapi/cli.py`
- To test locally: `pip install -e .`
- To contribute, fork the repo and submit a pull request.

---

## 📚 Resources
- [Postman Collection Docs](https://learning.postman.com/docs/getting-started/creating-the-first-collection/)
- [OpenAPI Spec Docs](https://swagger.io/specification/)
- [APIMatic Converter](https://www.apimatic.io/postman-to-openapi-converter)
- [postman2openapi CLI](https://github.com/joolfe/postman-to-openapi)

---

## 💬 Need Help?
If you have questions or need help, please open an issue or contact the maintainer.