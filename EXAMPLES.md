# APIProbe - Usage Examples

Quick navigation:
- [Example 1: Basic Model Listing](#example-1-basic-model-listing)
- [Example 2: Testing a Specific Model](#example-2-testing-a-specific-model)
- [Example 3: Feature Validation](#example-3-feature-validation)
- [Example 4: Detecting Deprecated Models](#example-4-detecting-deprecated-models)
- [Example 5: Configuration Drift Detection](#example-5-configuration-drift-detection)
- [Example 6: Full Validation Pipeline](#example-6-full-validation-pipeline)
- [Example 7: JSON Output for Automation](#example-7-json-output-for-automation)
- [Example 8: Python API Integration](#example-8-python-api-integration)
- [Example 9: Pre-Deployment Validation](#example-9-pre-deployment-validation)
- [Example 10: Multi-Provider Comparison](#example-10-multi-provider-comparison)

---

## Example 1: Basic Model Listing

**Scenario:** First time using APIProbe - discover what models are available.

**Steps:**
```bash
# Set your API key
export GOOGLE_API_KEY=your_key_here

# List all available models
python apiprobe.py list-models --provider google
```

**Expected Output:**
```
GOOGLE Models (15 found):

Model Name                    | Display Name                  | Input Limit
------------------------------+-------------------------------+------------
gemini-2.0-flash              | Gemini 2.0 Flash              | 1048576
gemini-2.0-flash-exp          | Gemini 2.0 Flash Experimental | 1048576
gemini-1.5-pro                | Gemini 1.5 Pro                | 2097152
gemini-1.5-flash              | Gemini 1.5 Flash              | 1048576
gemini-1.5-flash-latest       | Gemini 1.5 Flash Latest       | 1048576
gemini-1.0-pro                | Gemini 1.0 Pro                | 30720
text-embedding-004            | Text Embedding 004            | 2048
embedding-001                 | Embedding 001                 | 2048
...
```

**What You Learned:**
- How to query available models
- Model naming conventions
- Token limits for each model

---

## Example 2: Testing a Specific Model

**Scenario:** Verify a model works before using it in production.

**Steps:**
```bash
# Test the gemini-2.0-flash model
python apiprobe.py test-model --provider google --model gemini-2.0-flash
```

**Expected Output (Success):**
```
[OK] [GOOGLE] Model 'gemini-2.0-flash' is working correctly
```

**Expected Output (Failure):**
```
[X] [GOOGLE] Model 'gemini-nonexistent' not found
    Suggestions:
      - Run 'apiprobe list-models --provider google' to see available models
      - Check if the model name is spelled correctly
```

**What You Learned:**
- How to validate a specific model
- Clear error messages with actionable suggestions

---

## Example 3: Feature Validation

**Scenario:** Ensure a model supports required features (system instructions, tools).

**Steps:**
```bash
# Test model with specific features
python apiprobe.py test-model --provider google --model gemini-2.0-flash \
  --features systemInstruction,tools

# Test with wrong API version (v1 doesn't support these features)
python apiprobe.py test-model --provider google --model gemini-2.0-flash \
  --features systemInstruction,tools --api-version v1
```

**Expected Output (v1beta - Success):**
```
[OK] [GOOGLE] Model 'gemini-2.0-flash' is working correctly
```

**Expected Output (v1 - Failure):**
```
[X] [GOOGLE] Features not supported in v1: systemInstruction, tools
    Suggestions:
      - Use a different API version (e.g., v1beta for Google)
      - Remove unsupported features: systemInstruction, tools
```

**What You Learned:**
- API version affects feature availability
- Always use v1beta for Google Gemini's full feature set

---

## Example 4: Detecting Deprecated Models

**Scenario:** Catch common model name mistakes before they cause 404 errors.

**Steps:**
```bash
# Try a deprecated/incorrect model name
python apiprobe.py test-model --provider google --model gemini-3-flash-preview
```

**Expected Output:**
```
[X] [GOOGLE] Model name 'gemini-3-flash-preview' is incorrect or deprecated
    Suggestions:
      - Use 'gemini-1.5-flash' instead of 'gemini-3-flash-preview'
```

**What You Learned:**
- APIProbe knows common model name mistakes
- Instant suggestions without API calls for known issues

---

## Example 5: Configuration Drift Detection

**Scenario:** Database has cached old configuration that differs from code.

**Setup:**
```bash
# Create a test database with an old model name
python -c "
import sqlite3
conn = sqlite3.connect('test.db')
conn.execute('CREATE TABLE ai_config (model_name TEXT)')
conn.execute('INSERT INTO ai_config VALUES (\"gemini-2.0-flash-exp\")')
conn.commit()
conn.close()
"
```

**Steps:**
```bash
# Check for configuration drift
python apiprobe.py config-diff --db test.db
```

**Expected Output:**
```
Configuration Differences Found (1):

[ERROR] ai_config.model_name
    DB value:   gemini-2.0-flash-exp
    Code value: gemini-2.0-flash
    Deprecated/incorrect model name in database
```

**Cleanup:**
```bash
rm test.db
```

**What You Learned:**
- How to detect DB vs code mismatches
- Configuration drift causes runtime errors

---

## Example 6: Full Validation Pipeline

**Scenario:** Pre-deployment validation of entire AI configuration.

**Setup (.env file):**
```env
GOOGLE_API_KEY=AIza...
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

**Steps:**
```bash
# Full validation with .env and database
python apiprobe.py validate-all --env .env --db data/comms.db
```

**Expected Output:**
```
============================================================
  APIProbe Validation Report
============================================================

[OK] [GOOGLE] Found 15 models for google
[OK] [GOOGLE] Model 'gemini-2.0-flash' is working correctly
[OK] [ANTHROPIC] Found 5 models for anthropic
[OK] [ANTHROPIC] Model 'claude-opus-4-20250514' is working correctly
[OK] [OPENAI] Found 23 models for openai
[OK] [OPENAI] Model 'gpt-4o' is working correctly
[X] [XAI] No API key found for xai
    Suggestions:
      - Set XAI_API_KEY environment variable
      - Or provide a .env file with the API key

============================================================
  Summary: 6 passed, 1 failed
============================================================
```

**What You Learned:**
- One command validates entire AI stack
- Clear summary shows deployment readiness

---

## Example 7: JSON Output for Automation

**Scenario:** Integrate APIProbe into CI/CD pipeline.

**Steps:**
```bash
# Get JSON output for parsing
python apiprobe.py validate-all --env .env --format json > validation.json

# Check results programmatically
python -c "
import json
with open('validation.json') as f:
    results = json.load(f)
    
failed = [r for r in results if not r['success']]
if failed:
    print(f'FAILED: {len(failed)} issues found')
    for r in failed:
        print(f'  - {r[\"provider\"]}: {r[\"message\"]}')
    exit(1)
else:
    print('PASSED: All validations successful')
"
```

**Expected Output:**
```json
[
  {
    "success": true,
    "provider": "google",
    "check_type": "list_models",
    "message": "Found 15 models for google",
    "details": {"model_count": 15, "models": ["gemini-2.0-flash", ...]},
    "suggestions": []
  },
  ...
]
```

**What You Learned:**
- JSON output for automation/scripting
- Easy to integrate into CI/CD

---

## Example 8: Python API Integration

**Scenario:** Use APIProbe in your Python application.

**Steps:**
```python
from pathlib import Path
from apiprobe import APIProbe

# Initialize with .env file
probe = APIProbe(env_path=Path(".env"))

# List models for Google
print("=== Available Google Models ===")
try:
    models = probe.list_models("google")
    for model in models[:5]:  # Show first 5
        print(f"  {model.name}: {model.input_token_limit} tokens")
except ValueError as e:
    print(f"Error: {e}")

# Test a specific model
print("\n=== Testing gemini-2.0-flash ===")
result = probe.test_model(
    provider="google",
    model="gemini-2.0-flash",
    features=["systemInstruction"]
)
print(f"  Success: {result.success}")
print(f"  Message: {result.message}")

# Full validation
print("\n=== Full Validation ===")
results = probe.validate_all(providers=["google", "anthropic"])
passed = sum(1 for r in results if r.success)
failed = len(results) - passed
print(f"  Passed: {passed}, Failed: {failed}")
```

**Expected Output:**
```
=== Available Google Models ===
  gemini-2.0-flash: 1048576 tokens
  gemini-1.5-pro: 2097152 tokens
  gemini-1.5-flash: 1048576 tokens
  gemini-1.0-pro: 30720 tokens
  text-embedding-004: 2048 tokens

=== Testing gemini-2.0-flash ===
  Success: True
  Message: Model 'gemini-2.0-flash' is working correctly

=== Full Validation ===
  Passed: 4, Failed: 0
```

**What You Learned:**
- Programmatic access via Python API
- Easy integration into existing code

---

## Example 9: Pre-Deployment Validation

**Scenario:** Validate before every deployment (make it a habit).

**Create a validation script (`validate_before_deploy.sh`):**
```bash
#!/bin/bash
set -e

echo "=========================================="
echo "  Pre-Deployment API Validation"
echo "=========================================="

# Run validation
python apiprobe.py validate-all --env .env --db data/comms.db --format json > /tmp/validation.json

# Check for failures
FAILED=$(python -c "
import json
with open('/tmp/validation.json') as f:
    results = json.load(f)
failed = [r for r in results if not r['success']]
print(len(failed))
")

if [ "$FAILED" -gt 0 ]; then
    echo ""
    echo "[X] VALIDATION FAILED: $FAILED issues found"
    echo ""
    python apiprobe.py validate-all --env .env --db data/comms.db
    echo ""
    echo "Fix the above issues before deploying!"
    exit 1
fi

echo ""
echo "[OK] All validations passed!"
echo "Safe to deploy."
```

**Usage:**
```bash
chmod +x validate_before_deploy.sh
./validate_before_deploy.sh && ./deploy.sh
```

**What You Learned:**
- Make validation part of deployment process
- Block deploys when issues detected

---

## Example 10: Multi-Provider Comparison

**Scenario:** Compare model availability across providers.

**Steps:**
```bash
# Create comparison script
python -c "
from apiprobe import APIProbe, get_api_key
from pathlib import Path

probe = APIProbe(env_path=Path('.env'))

providers = ['google', 'anthropic', 'openai', 'xai']
print('Provider Comparison')
print('=' * 60)

for provider in providers:
    key = get_api_key(provider, Path('.env'))
    if not key:
        print(f'{provider.upper():15} | No API key configured')
        continue
    
    try:
        models = probe.list_models(provider)
        print(f'{provider.upper():15} | {len(models):3} models available')
        for model in models[:3]:
            print(f'                  | - {model.name}')
    except Exception as e:
        print(f'{provider.upper():15} | Error: {e}')
    print()
"
```

**Expected Output:**
```
Provider Comparison
============================================================
GOOGLE          |  15 models available
                  | - gemini-2.0-flash
                  | - gemini-1.5-pro
                  | - gemini-1.5-flash

ANTHROPIC       |   5 models available
                  | - claude-opus-4-20250514
                  | - claude-sonnet-4-20250514
                  | - claude-3-5-sonnet-20241022

OPENAI          |  23 models available
                  | - gpt-4o
                  | - gpt-4-turbo
                  | - gpt-3.5-turbo

XAI             |   2 models available
                  | - grok-beta
                  | - grok-2
```

**What You Learned:**
- Quick overview of all configured providers
- Easy to spot missing configurations

---

## Troubleshooting Examples

### API Key Issues

```bash
# Wrong: API key not found
$ python apiprobe.py list-models --provider google
[X] No API key found for google
    Set GOOGLE_API_KEY or use --api-key

# Fix: Use --env flag
$ python apiprobe.py list-models --provider google --env .env
GOOGLE Models (15 found):
...
```

### Network Errors

```bash
# If you get connection errors, check your network:
$ python apiprobe.py list-models --provider google 2>&1 | head -5

# Or increase timeout:
$ python apiprobe.py validate-all --timeout 60
```

### Debugging Output

```bash
# Get verbose JSON output for debugging
$ python apiprobe.py validate-all --format json 2>&1 | python -m json.tool
```

---

**Next Steps:**
- See [CHEAT_SHEET.txt](CHEAT_SHEET.txt) for quick command reference
- See [INTEGRATION_EXAMPLES.md](INTEGRATION_EXAMPLES.md) for Team Brain integration
- See [README.md](README.md) for full documentation
