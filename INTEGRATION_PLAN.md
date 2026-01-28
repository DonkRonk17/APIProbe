# APIProbe - Integration Plan

## 🎯 INTEGRATION GOALS

This document outlines how APIProbe integrates with:
1. Team Brain agents (Forge, Atlas, Clio, Nexus, Bolt)
2. Existing Team Brain tools
3. BCH (Beacon Command Hub)
4. Logan's workflows

---

## 📦 BCH INTEGRATION

### Overview

APIProbe is **highly relevant** to BCH operations, as BCH uses multiple AI providers (Google Gemini, Anthropic Claude, OpenAI GPT, xAI Grok) for its multi-agent communication features.

### BCH Commands (Proposed)

```
@apiprobe list-models google
@apiprobe test gemini-2.0-flash
@apiprobe validate-all
@apiprobe config-check
```

### Implementation Steps

1. **Add APIProbe to BCH CLI Bridge**
   - Location: `BCHCLIBridge/bchclibridge.py`
   - Add apiprobe command handlers

2. **Create BCH Integration Module**
   ```python
   # bch_apiprobe.py
   from apiprobe import APIProbe, validate_all
   
   def bch_pre_startup_check():
       """Run before BCH starts to validate AI configs."""
       results = validate_all(
           env_path=Path("backend/.env"),
           db_path=Path("data/comms.db")
       )
       failed = [r for r in results if not r.success]
       if failed:
           raise ConfigurationError(f"API validation failed: {len(failed)} issues")
       return True
   ```

3. **Add to BCH Startup Sequence**
   - Run `apiprobe validate-all` before starting WebSocket server
   - Alert users if any provider is misconfigured
   - Prevent startup if critical providers fail

4. **Update BCH Documentation**
   - Add APIProbe to dependencies
   - Document pre-deployment validation workflow

### BCH Integration Priority: **HIGH**

APIProbe was born from BCH debugging - it should be the first tool integrated into BCH's startup validation.

---

## 🤖 AI AGENT INTEGRATION

### Integration Matrix

| Agent | Use Case | Integration Method | Priority |
|-------|----------|-------------------|----------|
| **Forge** | Pre-deployment validation, config reviews | Python API + CLI | HIGH |
| **Atlas** | Tool building with API dependencies | Python API | HIGH |
| **Clio** | Linux-based validation, CI/CD | CLI | MEDIUM |
| **Nexus** | Cross-platform testing | CLI + Python | MEDIUM |
| **Bolt** | Automated validation in free tier | CLI | LOW |

### Agent-Specific Workflows

#### Forge (Orchestrator / Reviewer)

**Primary Use Case:** Pre-deployment validation and configuration review

**Integration Steps:**
1. Add APIProbe to Forge's standard toolkit
2. Run validation before any BCH deployment recommendation
3. Include in code review checklists for AI integration PRs

**Example Workflow:**
```python
# Forge pre-deployment checklist
from apiprobe import APIProbe
from pathlib import Path

def forge_deployment_review():
    """Forge's deployment validation routine."""
    probe = APIProbe(env_path=Path(".env"))
    
    # Validate all AI providers
    results = probe.validate_all(
        db_path=Path("data/comms.db"),
        providers=["google", "anthropic", "openai"]
    )
    
    # Check for issues
    failed = [r for r in results if not r.success]
    if failed:
        print("⚠️ DEPLOYMENT BLOCKED: API configuration issues found")
        for r in failed:
            print(f"  - [{r.provider}] {r.message}")
        return False
    
    print("✅ API validation passed - safe to deploy")
    return True
```

**Forge Integration Checklist:**
- [ ] Add to deployment review workflow
- [ ] Include in tool building templates
- [ ] Document in Orchestration Protocol

#### Atlas (Executor / Builder)

**Primary Use Case:** Validate API configs when building tools that use AI providers

**Integration Steps:**
1. Run APIProbe before any API integration work
2. Verify model availability for new features
3. Test feature support before implementation

**Example Workflow:**
```python
# Atlas tool building with API validation
from apiprobe import APIProbe

def atlas_ai_feature_implementation():
    """Atlas validates before implementing AI features."""
    probe = APIProbe()
    
    # Check if target model supports required features
    result = probe.test_model(
        provider="google",
        model="gemini-2.0-flash",
        features=["systemInstruction", "tools"]
    )
    
    if not result.success:
        print(f"Cannot implement: {result.message}")
        for suggestion in result.suggestions:
            print(f"  Suggestion: {suggestion}")
        return
    
    print("Model supports all required features - proceeding with implementation")
```

#### Clio (Linux / Ubuntu Agent)

**Primary Use Case:** CI/CD pipeline validation, Linux-based testing

**Platform Considerations:**
- Works natively on Linux (Python stdlib)
- Can be added to systemd service startup checks
- Integrates with bash scripts

**Example:**
```bash
#!/bin/bash
# Clio CI/CD validation script

# Run validation
python /home/clio/tools/APIProbe/apiprobe.py validate-all \
  --env /home/clio/.env \
  --format json > /tmp/api_validation.json

# Check results
FAILED=$(jq '[.[] | select(.success == false)] | length' /tmp/api_validation.json)

if [ "$FAILED" -gt 0 ]; then
    echo "❌ API validation failed: $FAILED issues"
    jq '.[] | select(.success == false) | .message' /tmp/api_validation.json
    exit 1
fi

echo "✅ API validation passed"
```

#### Nexus (Multi-Platform Agent)

**Primary Use Case:** Cross-platform validation, multi-environment testing

**Cross-Platform Notes:**
- Works on Windows, Linux, macOS
- No platform-specific dependencies
- Same commands work everywhere

**Example:**
```python
# Nexus cross-platform validation
import platform
from apiprobe import APIProbe

def nexus_platform_validation():
    """Validate across platforms."""
    print(f"Platform: {platform.system()}")
    
    probe = APIProbe()
    results = probe.validate_all()
    
    # Generate platform-specific report
    report = {
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "validation_results": [r.to_dict() for r in results]
    }
    
    return report
```

#### Bolt (Cline / Free Executor)

**Primary Use Case:** Automated validation without API costs

**Cost Considerations:**
- APIProbe uses minimal API calls (one test per provider)
- Validation is much cheaper than debugging
- Can be run in --dry-run mode for zero-cost checks

**Example:**
```bash
# Bolt cost-efficient validation
python apiprobe.py list-models --provider google  # One API call
python apiprobe.py config-diff --db data/comms.db  # Zero API calls (local only)
```

---

## 🔗 INTEGRATION WITH OTHER TEAM BRAIN TOOLS

### With AgentHealth

**Correlation Use Case:** Track API validation status as part of agent health

**Integration Pattern:**
```python
from agenthealth import AgentHealth
from apiprobe import APIProbe

health = AgentHealth()
probe = APIProbe()

# Start session
session_id = health.start_session("FORGE", task="API Validation")

# Run validation
results = probe.validate_all()
passed = sum(1 for r in results if r.success)
failed = len(results) - passed

# Log to health
if failed > 0:
    health.log_error("FORGE", f"API validation: {failed} issues found")
else:
    health.heartbeat("FORGE", status="healthy", 
                     metadata={"api_validation": "passed"})

health.end_session("FORGE", session_id=session_id)
```

### With SynapseLink

**Notification Use Case:** Alert team when validation fails

**Integration Pattern:**
```python
from synapselink import quick_send
from apiprobe import APIProbe

probe = APIProbe()
results = probe.validate_all()

failed = [r for r in results if not r.success]

if failed:
    quick_send(
        "FORGE,LOGAN",
        "⚠️ API Configuration Issues Detected",
        f"APIProbe found {len(failed)} issues:\n\n" +
        "\n".join(f"- [{r.provider}] {r.message}" for r in failed) +
        "\n\nRun 'apiprobe validate-all' for full details.",
        priority="HIGH"
    )
```

### With TaskQueuePro

**Task Management Use Case:** Create tasks for failed validations

**Integration Pattern:**
```python
from taskqueuepro import TaskQueuePro
from apiprobe import APIProbe

queue = TaskQueuePro()
probe = APIProbe()

# Run validation
results = probe.validate_all()
failed = [r for r in results if not r.success]

# Create tasks for each failure
for result in failed:
    task_id = queue.create_task(
        title=f"Fix API Config: {result.provider}",
        description=f"{result.message}\n\nSuggestions:\n" +
                    "\n".join(f"- {s}" for s in result.suggestions),
        agent="FORGE",
        priority=2 if result.provider in ["google", "anthropic"] else 3,
        tags=["api-config", "validation", result.provider]
    )
    print(f"Created task {task_id} for {result.provider}")
```

### With MemoryBridge

**Context Persistence Use Case:** Store validation history

**Integration Pattern:**
```python
from memorybridge import MemoryBridge
from apiprobe import APIProbe
from datetime import datetime

memory = MemoryBridge()
probe = APIProbe()

# Load history
history = memory.get("apiprobe_history", default=[])

# Run validation
results = probe.validate_all()
passed = sum(1 for r in results if r.success)
failed = len(results) - passed

# Save to history
history.append({
    "timestamp": datetime.now().isoformat(),
    "passed": passed,
    "failed": failed,
    "details": [r.to_dict() for r in results if not r.success]
})

# Keep last 30 validations
history = history[-30:]
memory.set("apiprobe_history", history)
memory.sync()
```

### With SessionReplay

**Debugging Use Case:** Record validation in session for replay

**Integration Pattern:**
```python
from sessionreplay import SessionReplay
from apiprobe import APIProbe

replay = SessionReplay()
probe = APIProbe()

# Start session
session_id = replay.start_session("ATLAS", task="Pre-deployment validation")

# Log validation steps
replay.log_input(session_id, "Running API validation...")

results = probe.validate_all()

for result in results:
    status = "[OK]" if result.success else "[X]"
    replay.log_output(session_id, f"{status} {result.provider}: {result.message}")

# End session
status = "COMPLETED" if all(r.success for r in results) else "FAILED"
replay.end_session(session_id, status=status)
```

### With ContextCompressor

**Token Optimization Use Case:** Compress validation reports before sharing

**Integration Pattern:**
```python
from contextcompressor import ContextCompressor
from apiprobe import APIProbe, format_markdown

compressor = ContextCompressor()
probe = APIProbe()

# Generate full validation report
results = probe.validate_all()
full_report = format_markdown(results)

# Compress for sharing
compressed = compressor.compress_text(
    full_report,
    query="validation summary",
    method="summary"
)

print(f"Original: {len(full_report)} chars")
print(f"Compressed: {len(compressed.compressed_text)} chars")
print(f"Savings: {compressed.estimated_token_savings} tokens")
```

### With ConfigManager

**Configuration Use Case:** Centralize APIProbe settings

**Integration Pattern:**
```python
from configmanager import ConfigManager
from apiprobe import APIProbe
from pathlib import Path

config = ConfigManager()

# Load shared config
apiprobe_config = config.get("apiprobe", {
    "env_path": ".env",
    "default_providers": ["google", "anthropic", "openai"],
    "timeout": 30,
    "output_format": "table"
})

# Initialize with config
probe = APIProbe(env_path=Path(apiprobe_config["env_path"]))

# Run validation with configured providers
results = probe.validate_all(
    providers=apiprobe_config["default_providers"]
)
```

### With EnvGuard

**Complementary Use Case:** EnvGuard validates .env files, APIProbe validates API endpoints

**Integration Pattern:**
```python
from envguard import EnvGuard
from apiprobe import APIProbe
from pathlib import Path

# Step 1: Validate .env file structure
guard = EnvGuard()
env_issues = guard.scan(Path(".env"))

if env_issues:
    print("Fix .env file issues first:")
    for issue in env_issues:
        print(f"  - {issue}")
else:
    # Step 2: Validate API configurations work
    probe = APIProbe(env_path=Path(".env"))
    results = probe.validate_all()
    
    for r in results:
        status = "[OK]" if r.success else "[X]"
        print(f"{status} {r.provider}: {r.message}")
```

---

## 🚀 ADOPTION ROADMAP

### Phase 1: Core Adoption (Week 1)

**Goal:** All agents aware and can use basic features

**Steps:**
1. ✓ Tool deployed to GitHub
2. ☐ Quick-start guides sent via Synapse
3. ☐ Each agent tests basic workflow
4. ☐ Feedback collected

**Success Criteria:**
- All 5 agents have used tool at least once
- No blocking issues reported

### Phase 2: BCH Integration (Week 2)

**Goal:** APIProbe integrated into BCH startup and deployment

**Steps:**
1. ☐ Add to BCH pre-startup checks
2. ☐ Integrate with BCH CLI Bridge
3. ☐ Update BCH documentation
4. ☐ Test with production configs

**Success Criteria:**
- BCH validates all AI providers on startup
- Config issues caught before runtime

### Phase 3: CI/CD Integration (Week 3)

**Goal:** Automated validation in pipelines

**Steps:**
1. ☐ Add to GitHub Actions workflows
2. ☐ Create pre-commit hooks
3. ☐ Document CI/CD patterns
4. ☐ Test with real deployments

**Success Criteria:**
- Deployments blocked if validation fails
- Zero post-deployment API config issues

### Phase 4: Full Ecosystem (Week 4+)

**Goal:** Deep integration with all Team Brain tools

**Steps:**
1. ☐ AgentHealth integration
2. ☐ SynapseLink notifications
3. ☐ TaskQueuePro task creation
4. ☐ Memory Core history tracking

**Success Criteria:**
- Seamless tool interoperability
- Comprehensive validation history

---

## 📊 SUCCESS METRICS

**Adoption Metrics:**
- Number of agents using tool: Target 5/5
- Daily usage count: Track
- Integration with other tools: Target 5+

**Efficiency Metrics:**
- Time saved per validation: 2-6 hours
- Debugging sessions prevented: Track
- API errors in production: Target 0

**Quality Metrics:**
- Bug reports: Track
- Feature requests: Track
- User satisfaction: Qualitative

---

## 🛠️ TECHNICAL INTEGRATION DETAILS

### Import Paths

```python
# Standard import
from apiprobe import APIProbe

# Specific imports
from apiprobe import (
    APIProbe,
    ValidationResult,
    ModelInfo,
    ConfigDiff,
    list_models,
    test_model,
    config_diff,
    validate_all,
)
```

### Configuration Integration

**Config File:** None required (uses environment variables)

**Environment Variables:**
```bash
GOOGLE_API_KEY=...
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
XAI_API_KEY=...
```

**Shared Config with ConfigManager:**
```json
{
  "apiprobe": {
    "env_path": ".env",
    "default_providers": ["google", "anthropic", "openai"],
    "timeout": 30,
    "output_format": "table"
  }
}
```

### Error Handling Integration

**Standardized Error Codes:**
- 0: Success (all validations passed)
- 1: Validation failed (one or more issues)
- 2: Configuration error (missing API key, etc.)
- 130: User cancelled (Ctrl+C)

### Logging Integration

**Log Format:** Compatible with Team Brain standard

**Example Log Output:**
```
2026-01-28 12:00:00 INFO [APIProbe] Starting validation...
2026-01-28 12:00:01 INFO [APIProbe] google: 15 models found
2026-01-28 12:00:02 WARN [APIProbe] anthropic: API key not found
2026-01-28 12:00:02 INFO [APIProbe] Validation complete: 3 passed, 1 failed
```

---

## 🔧 MAINTENANCE & SUPPORT

### Update Strategy

- Minor updates (v1.x): As needed
- Major updates (v2.0+): Quarterly review
- Security patches: Immediate

### Support Channels

- GitHub Issues: Bug reports, feature requests
- Synapse: Team Brain discussions
- Direct to Builder: Complex issues

### Known Limitations

1. **API Rate Limits:** Multiple validations may hit rate limits
2. **Network Required:** Cannot validate without internet
3. **Provider Changes:** API endpoints may change

### Planned Improvements

1. **Caching:** Cache model lists to reduce API calls
2. **Offline Mode:** Validate against cached data
3. **More Providers:** Add support for additional AI providers
4. **Web UI:** Simple web interface for validation

---

## 📚 ADDITIONAL RESOURCES

- Main Documentation: [README.md](README.md)
- Examples: [EXAMPLES.md](EXAMPLES.md)
- Quick Start Guides: [QUICK_START_GUIDES.md](QUICK_START_GUIDES.md)
- Integration Examples: [INTEGRATION_EXAMPLES.md](INTEGRATION_EXAMPLES.md)
- GitHub: https://github.com/DonkRonk17/APIProbe

---

**Last Updated:** January 28, 2026  
**Maintained By:** Forge (Team Brain)
