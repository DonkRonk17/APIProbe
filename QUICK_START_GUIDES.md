# APIProbe - Quick Start Guides

## 📖 ABOUT THESE GUIDES

Each Team Brain agent has a **5-minute quick-start guide** tailored to their role and workflows.

**Choose your guide:**
- [Forge (Orchestrator)](#forge-quick-start)
- [Atlas (Executor)](#atlas-quick-start)
- [Clio (Linux Agent)](#clio-quick-start)
- [Nexus (Multi-Platform)](#nexus-quick-start)
- [Bolt (Free Executor)](#bolt-quick-start)

---

## 🔥 FORGE QUICK START

**Role:** Orchestrator / Reviewer  
**Time:** 5 minutes  
**Goal:** Learn to use APIProbe for pre-deployment validation and code reviews

### Step 1: Installation Check

```bash
# Verify APIProbe is available
cd C:\Users\logan\OneDrive\Documents\AutoProjects\APIProbe
python apiprobe.py --version

# Expected: APIProbe v1.0.0
```

### Step 2: First Use - Pre-Deployment Validation

```bash
# Set API keys (if not in .env)
set GOOGLE_API_KEY=your_key_here

# Run full validation
python apiprobe.py validate-all --env .env
```

**Expected Output:**
```
============================================================
  APIProbe Validation Report
============================================================

[OK] [GOOGLE] Found 15 models for google
[OK] [GOOGLE] Model 'gemini-2.0-flash' is working correctly
...
============================================================
  Summary: 6 passed, 0 failed
============================================================
```

### Step 3: Integration with Forge Workflows

**Use Case 1: Before recommending BCH deployment**
```python
# In Forge's deployment review
from apiprobe import APIProbe

probe = APIProbe(env_path=Path("D:/BEACON_HQ/PROJECTS/00_ACTIVE/BCH_APPS/backend/.env"))
results = probe.validate_all(db_path=Path("D:/BEACON_HQ/PROJECTS/00_ACTIVE/BCH_APPS/data/comms.db"))

if any(not r.success for r in results):
    print("⚠️ HOLD DEPLOYMENT: API validation failed")
else:
    print("✅ Clear for deployment")
```

**Use Case 2: Code review for AI integrations**
```bash
# Check what models are available for a feature request
python apiprobe.py list-models --provider google --format table

# Verify the proposed model supports required features
python apiprobe.py test-model --provider google --model gemini-2.0-flash \
  --features systemInstruction,tools
```

### Step 4: Common Forge Commands

```bash
# Full validation (before any deployment)
python apiprobe.py validate-all --env .env --db data/comms.db

# Check for config drift
python apiprobe.py config-diff --db data/comms.db --code backend/

# Generate report for team
python apiprobe.py validate-all --format markdown > validation_report.md
```

### Next Steps for Forge

1. Add to deployment review checklist
2. Run before every BCH recommendation
3. Include in tool building specs (require API validation)
4. Review [INTEGRATION_PLAN.md](INTEGRATION_PLAN.md) - Forge section

---

## ⚡ ATLAS QUICK START

**Role:** Executor / Builder  
**Time:** 5 minutes  
**Goal:** Learn to use APIProbe when building tools with AI provider integrations

### Step 1: Installation Check

```bash
python -c "from apiprobe import APIProbe; print('APIProbe ready!')"
```

### Step 2: First Use - Model Discovery

```python
# In your Atlas session
from apiprobe import APIProbe
from pathlib import Path

probe = APIProbe(env_path=Path(".env"))

# See what models are available
models = probe.list_models("google")
print(f"Found {len(models)} models:")
for m in models[:5]:
    print(f"  - {m.name}: {m.input_token_limit} tokens")
```

### Step 3: Integration with Build Workflows

**During Tool Creation:**
```python
# Before implementing AI features, verify support
from apiprobe import APIProbe

probe = APIProbe()

# Check if model supports what you need
result = probe.test_model(
    provider="google",
    model="gemini-2.0-flash",
    features=["systemInstruction", "tools"]
)

if result.success:
    print("✅ Proceeding with implementation")
else:
    print(f"❌ {result.message}")
    for s in result.suggestions:
        print(f"   Fix: {s}")
```

**In Tool Test Suites:**
```python
# Add to your test_*.py
import unittest
from apiprobe import test_model

class TestAPIConfiguration(unittest.TestCase):
    def test_google_model_available(self):
        """Verify the Google model we use is available."""
        result = test_model("google", "gemini-2.0-flash", "test_key")
        # Note: Will need actual key for live test
        self.assertIsNotNone(result)
```

### Step 4: Common Atlas Commands

```bash
# Check what's available before building
python apiprobe.py list-models --provider google

# Verify model before hardcoding
python apiprobe.py test-model --provider google --model gemini-2.0-flash

# Check feature support for API version
python apiprobe.py test-model --provider google --model gemini-2.0-flash \
  --features systemInstruction --api-version v1beta
```

### Next Steps for Atlas

1. Run `list-models` before any AI integration work
2. Add APIProbe validation to tool test suites
3. Document model requirements in tool READMEs
4. Review [INTEGRATION_EXAMPLES.md](INTEGRATION_EXAMPLES.md)

---

## 🐧 CLIO QUICK START

**Role:** Linux / Ubuntu Agent  
**Time:** 5 minutes  
**Goal:** Learn to use APIProbe in Linux environment and CI/CD pipelines

### Step 1: Linux Installation

```bash
# Clone from GitHub
git clone https://github.com/DonkRonk17/APIProbe.git
cd APIProbe

# Verify (no install needed - zero dependencies!)
python3 apiprobe.py --version
# APIProbe v1.0.0

# Create alias (optional)
alias apiprobe='python3 ~/tools/APIProbe/apiprobe.py'
```

### Step 2: First Use - CI/CD Validation

```bash
# Set API keys
export GOOGLE_API_KEY=your_key
export ANTHROPIC_API_KEY=your_key

# Run validation
python3 apiprobe.py validate-all --format json > /tmp/validation.json

# Check results
jq '.[] | select(.success == false) | .message' /tmp/validation.json
```

### Step 3: Integration with Clio Workflows

**Shell Script for CI/CD:**
```bash
#!/bin/bash
# validate_apis.sh - Run before deployment

set -e

echo "=== Running API Validation ==="

# Run validation
python3 /home/clio/tools/APIProbe/apiprobe.py validate-all \
  --env /home/clio/.env \
  --format json > /tmp/api_check.json

# Count failures
FAILED=$(jq '[.[] | select(.success == false)] | length' /tmp/api_check.json)

if [ "$FAILED" -gt 0 ]; then
    echo "❌ FAILED: $FAILED API configuration issues"
    jq '.[] | select(.success == false)' /tmp/api_check.json
    exit 1
fi

echo "✅ PASSED: All API configurations valid"
exit 0
```

**Systemd Service Pre-Start Check:**
```ini
# /etc/systemd/system/bch-backend.service
[Unit]
Description=BCH Backend
After=network.target

[Service]
Type=simple
ExecStartPre=/home/clio/tools/APIProbe/validate_apis.sh
ExecStart=/usr/bin/python3 /opt/bch/backend/main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### Step 4: Common Clio Commands

```bash
# Quick validation
apiprobe validate-all --env ~/.env

# JSON output for parsing
apiprobe validate-all --format json | jq .

# Config drift check (local, no API calls)
apiprobe config-diff --db /opt/bch/data/comms.db

# Markdown report for documentation
apiprobe validate-all --format markdown > ~/reports/api_validation.md
```

### Next Steps for Clio

1. Add to ABIOS startup sequence
2. Create systemd pre-start hooks
3. Integrate with existing CI/CD pipelines
4. Set up scheduled validation cron jobs

---

## 🌐 NEXUS QUICK START

**Role:** Multi-Platform Agent  
**Time:** 5 minutes  
**Goal:** Learn cross-platform usage of APIProbe

### Step 1: Platform Detection

```python
import platform
from apiprobe import APIProbe

print(f"Running on: {platform.system()} {platform.release()}")
probe = APIProbe()
# Works the same on Windows, Linux, and macOS!
```

### Step 2: First Use - Cross-Platform Validation

```python
# Platform-agnostic validation
from apiprobe import APIProbe
from pathlib import Path

# Path handling works on all platforms
env_path = Path.home() / ".env"  # ~/. env on all platforms

probe = APIProbe(env_path=env_path)
results = probe.validate_all()

for r in results:
    status = "[OK]" if r.success else "[X]"
    print(f"{status} {r.provider}: {r.message}")
```

### Step 3: Platform-Specific Considerations

**Windows:**
```batch
REM Set API key (Windows)
set GOOGLE_API_KEY=your_key

REM Run validation
python apiprobe.py validate-all
```

**Linux/macOS:**
```bash
# Set API key (Unix)
export GOOGLE_API_KEY=your_key

# Run validation
python3 apiprobe.py validate-all
```

**Cross-Platform Script:**
```python
import os
import platform
from apiprobe import APIProbe

def get_env_path():
    """Get .env path based on platform."""
    if platform.system() == "Windows":
        return Path(os.environ.get("USERPROFILE", ".")) / ".env"
    else:
        return Path.home() / ".env"

probe = APIProbe(env_path=get_env_path())
results = probe.validate_all()
```

### Step 4: Common Nexus Commands

```bash
# Works on all platforms
python apiprobe.py validate-all
python apiprobe.py list-models --provider google
python apiprobe.py test-model --provider anthropic --model claude-3-5-sonnet-20241022
```

### Next Steps for Nexus

1. Test on all 3 platforms (Windows, Linux, macOS)
2. Create platform-specific documentation if needed
3. Report any platform-specific issues
4. Add to multi-platform test suites

---

## 🆓 BOLT QUICK START

**Role:** Free Executor (Cline + Grok)  
**Time:** 5 minutes  
**Goal:** Learn to use APIProbe without incurring API costs

### Step 1: Verify Free Access

```bash
# No API key required for these operations!
python apiprobe.py --help  # Free
python apiprobe.py --version  # Free
```

### Step 2: First Use - Cost-Free Operations

```bash
# Config diff - ZERO API CALLS (reads local database only)
python apiprobe.py config-diff --db data/comms.db

# This is completely free - no API calls made!
```

### Step 3: Integration with Bolt Workflows

**Minimal API Usage:**
```bash
# Only ONE API call to list models
python apiprobe.py list-models --provider google

# Then use cached knowledge for validation logic
# (APIProbe knows common model name mistakes without calling APIs)
```

**Cost-Free Validation Pattern:**
```python
from apiprobe import config_diff, MODEL_CORRECTIONS
from pathlib import Path

# Check for known issues WITHOUT API calls
diffs = config_diff(Path("data/comms.db"))

for diff in diffs:
    print(f"{diff.severity}: {diff.field}")
    print(f"  DB: {diff.db_value}")
    print(f"  Expected: {diff.code_value}")
```

### Step 4: Common Bolt Commands

```bash
# FREE - No API calls
python apiprobe.py config-diff --db data/comms.db
python apiprobe.py --help
python apiprobe.py --version

# MINIMAL COST - One API call
python apiprobe.py list-models --provider google

# SOME COST - One API call per test
python apiprobe.py test-model --provider google --model gemini-2.0-flash
```

### Cost Comparison

| Operation | API Calls | Cost |
|-----------|-----------|------|
| --help, --version | 0 | Free |
| config-diff | 0 | Free |
| list-models (per provider) | 1 | ~$0.0001 |
| test-model (per model) | 1 | ~$0.0001 |
| validate-all (4 providers) | 8 | ~$0.001 |

### Next Steps for Bolt

1. Use config-diff for zero-cost validation
2. Run list-models once and cache results
3. Only use test-model when necessary
4. Add to Cline automated workflows

---

## 📚 ADDITIONAL RESOURCES

**For All Agents:**
- Full Documentation: [README.md](README.md)
- Examples: [EXAMPLES.md](EXAMPLES.md)
- Integration Plan: [INTEGRATION_PLAN.md](INTEGRATION_PLAN.md)
- Cheat Sheet: [CHEAT_SHEET.txt](CHEAT_SHEET.txt)

**Support:**
- GitHub Issues: https://github.com/DonkRonk17/APIProbe/issues
- Synapse: Post in THE_SYNAPSE/active/
- Direct: Message Forge

---

**Last Updated:** January 28, 2026  
**Maintained By:** Forge (Team Brain)
