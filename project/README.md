# Dummy API Project for HealAPI Testing

## Files
- `old_openapi.yaml`: OpenAPI spec with `/hello` endpoint (returns `{ "message": "Hello, world!" }`).
- `new_openapi.yaml`: Breaking change – response property renamed to `greeting`.
- `dummy_collection.json`: Postman collection for `/hello` using `{{apiurl}}`.
- `dummy_env.json`: Postman environment with `apiurl` set to `http://localhost:5000`.
- `dummy_api.py`: Simple Flask API for `/hello`.

## How to Run

1. **Install dependencies** (in your virtual environment):
   ```powershell
   pip install flask
   ```
2. **Start the API:**
   ```powershell
   python dummy_api.py
   ```
3. **Test with HealAPI:**
   Use the following arguments:
   - `--old-spec old_openapi.yaml`
   - `--new-spec new_openapi.yaml`
   - `--collection dummy_collection.json`
   - `--env-path dummy_env.json`

   Example:
   ```powershell
   python ..\..\main.py --old-spec old_openapi.yaml --new-spec new_openapi.yaml --collection dummy_collection.json --env-path dummy_env.json
   ```

4. **Expected:**
   - Old spec: `/hello` returns `{ "message": "Hello, world!" }`
   - New spec: `/hello` returns `{ "greeting": ... }` (breaking change)
   - HealAPI should detect the breaking change and run the Postman test.
