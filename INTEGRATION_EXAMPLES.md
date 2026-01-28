# APIProbe - Integration Examples

## 🎯 INTEGRATION PHILOSOPHY

APIProbe is designed to work seamlessly with other Team Brain tools. This document provides **copy-paste-ready code examples** for common integration patterns.

---

## 📚 TABLE OF CONTENTS

1. [Pattern 1: APIProbe + AgentHealth](#pattern-1-apiprobe--agenthealth)
2. [Pattern 2: APIProbe + SynapseLink](#pattern-2-apiprobe--synapselink)
3. [Pattern 3: APIProbe + TaskQueuePro](#pattern-3-apiprobe--taskqueuepro)
4. [Pattern 4: APIProbe + MemoryBridge](#pattern-4-apiprobe--memorybridge)
5. [Pattern 5: APIProbe + SessionReplay](#pattern-5-apiprobe--sessionreplay)
6. [Pattern 6: APIProbe + ContextCompressor](#pattern-6-apiprobe--contextcompressor)
7. [Pattern 7: APIProbe + ConfigManager](#pattern-7-apiprobe--configmanager)
8. [Pattern 8: APIProbe + EnvGuard](#pattern-8-apiprobe--envguard)
9. [Pattern 9: Pre-Deployment Pipeline](#pattern-9-pre-deployment-pipeline)
10. [Pattern 10: Full Team Brain Stack](#pattern-10-full-team-brain-stack)

---

## Pattern 1: APIProbe + AgentHealth

**Use Case:** Track API validation status as part of agent health monitoring

**Why:** Correlate API configuration health with overall agent performance

**Code:**

```python
from agenthealth import AgentHealth
from apiprobe import APIProbe
from pathlib import Path

# Initialize both tools
health = AgentHealth()
probe = APIProbe(env_path=Path(".env"))

# Start health session
session_id = health.start_session("FORGE", task="API Validation Check")

try:
    # Run API validation
    results = probe.validate_all()
    
    passed = sum(1 for r in results if r.success)
    failed = len(results) - passed
    
    if failed > 0:
        # Log issues to health
        health.log_error(
            "FORGE",
            f"API validation failed: {failed} issues"
        )
        for r in results:
            if not r.success:
                health.log_error("FORGE", f"  {r.provider}: {r.message}")
    else:
        # Log success
        health.heartbeat(
            "FORGE",
            status="healthy",
            metadata={
                "api_validation": "passed",
                "providers_checked": len(results)
            }
        )
    
except Exception as e:
    health.log_error("FORGE", f"Validation error: {e}")
    
finally:
    health.end_session(
        "FORGE",
        session_id=session_id,
        status="success" if failed == 0 else "failed"
    )
```

**Result:** API validation status tracked in AgentHealth metrics

---

## Pattern 2: APIProbe + SynapseLink

**Use Case:** Alert team when API configuration issues are detected

**Why:** Keep team informed of configuration problems automatically

**Code:**

```python
from synapselink import quick_send
from apiprobe import APIProbe
from pathlib import Path

probe = APIProbe(env_path=Path(".env"))

# Run validation
results = probe.validate_all()
failed = [r for r in results if not r.success]

if failed:
    # Build message
    issues_text = "\n".join(
        f"- [{r.provider.upper()}] {r.message}"
        for r in failed
    )
    
    suggestions_text = ""
    for r in failed:
        if r.suggestions:
            suggestions_text += f"\n**{r.provider.upper()}:**\n"
            suggestions_text += "\n".join(f"  - {s}" for s in r.suggestions)
    
    # Send alert
    quick_send(
        "FORGE,LOGAN",
        "⚠️ API Configuration Issues Detected",
        f"APIProbe found {len(failed)} issues:\n\n"
        f"{issues_text}\n\n"
        f"**Suggestions:**{suggestions_text}\n\n"
        f"Run `apiprobe validate-all` for full details.",
        priority="HIGH"
    )
    
    print(f"Alert sent for {len(failed)} issues")
else:
    # Optional: Send success notification
    quick_send(
        "TEAM",
        "[OK] API Validation Passed",
        "All AI provider configurations validated successfully.",
        priority="LOW"
    )
```

**Result:** Team receives instant notification of configuration issues

---

## Pattern 3: APIProbe + TaskQueuePro

**Use Case:** Automatically create tasks for API configuration issues

**Why:** Track resolution of configuration problems in task queue

**Code:**

```python
from taskqueuepro import TaskQueuePro
from apiprobe import APIProbe
from pathlib import Path

queue = TaskQueuePro()
probe = APIProbe(env_path=Path(".env"))

# Run validation
results = probe.validate_all()
failed = [r for r in results if not r.success]

# Create tasks for each failure
for result in failed:
    # Determine priority based on provider importance
    priority_map = {
        "google": 1,      # Critical - main AI provider
        "anthropic": 1,   # Critical - backup AI provider
        "openai": 2,      # High
        "xai": 3,         # Medium
    }
    priority = priority_map.get(result.provider, 3)
    
    # Build task description
    description = f"""
**Issue:** {result.message}

**Provider:** {result.provider.upper()}
**Check Type:** {result.check_type}

**Suggestions:**
"""
    for suggestion in result.suggestions:
        description += f"- {suggestion}\n"
    
    description += f"""
**To Fix:**
1. Review the suggestion above
2. Update configuration as needed
3. Run `apiprobe test-model --provider {result.provider}` to verify
4. Mark this task complete
"""
    
    # Create task
    task_id = queue.create_task(
        title=f"Fix API Config: {result.provider.upper()} - {result.check_type}",
        description=description,
        agent="FORGE",  # Assign to orchestrator for review
        priority=priority,
        tags=["api-config", "validation", result.provider, "auto-generated"]
    )
    
    print(f"Created task {task_id} for {result.provider}")

if failed:
    print(f"\nCreated {len(failed)} tasks for API configuration issues")
else:
    print("No issues found - no tasks created")
```

**Result:** Actionable tasks created for each configuration issue

---

## Pattern 4: APIProbe + MemoryBridge

**Use Case:** Persist validation history for trend analysis

**Why:** Track configuration health over time

**Code:**

```python
from memorybridge import MemoryBridge
from apiprobe import APIProbe
from datetime import datetime
from pathlib import Path

memory = MemoryBridge()
probe = APIProbe(env_path=Path(".env"))

# Load existing history
history = memory.get("apiprobe_validation_history", default=[])

# Run validation
results = probe.validate_all()
passed = sum(1 for r in results if r.success)
failed = len(results) - passed

# Create history entry
entry = {
    "timestamp": datetime.now().isoformat(),
    "passed": passed,
    "failed": failed,
    "total": len(results),
    "issues": [
        {
            "provider": r.provider,
            "check_type": r.check_type,
            "message": r.message
        }
        for r in results if not r.success
    ]
}

# Append to history
history.append(entry)

# Keep last 100 validations
history = history[-100:]

# Save to memory
memory.set("apiprobe_validation_history", history)
memory.sync()

# Print trend analysis
print("=== Validation History ===")
print(f"Current: {passed}/{len(results)} passed")

if len(history) >= 2:
    prev = history[-2]
    if entry["failed"] > prev["failed"]:
        print(f"⚠️ TREND: Issues increased ({prev['failed']} → {entry['failed']})")
    elif entry["failed"] < prev["failed"]:
        print(f"✅ TREND: Issues decreased ({prev['failed']} → {entry['failed']})")
    else:
        print(f"→ TREND: Issues unchanged ({entry['failed']})")

print(f"\nTotal validations recorded: {len(history)}")
```

**Result:** Validation history persisted with trend analysis

---

## Pattern 5: APIProbe + SessionReplay

**Use Case:** Record validation process for debugging replay

**Why:** Understand what was validated when issues arise later

**Code:**

```python
from sessionreplay import SessionReplay
from apiprobe import APIProbe
from pathlib import Path

replay = SessionReplay()
probe = APIProbe(env_path=Path(".env"))

# Start recording session
session_id = replay.start_session(
    "ATLAS",
    task="Pre-deployment API Validation"
)

try:
    # Log start
    replay.log_input(session_id, "Starting API validation...")
    
    # List models first
    replay.log_input(session_id, "Querying available models...")
    
    for provider in ["google", "anthropic", "openai"]:
        try:
            models = probe.list_models(provider)
            replay.log_output(
                session_id,
                f"[OK] {provider}: {len(models)} models available"
            )
        except ValueError as e:
            replay.log_output(session_id, f"[X] {provider}: {e}")
    
    # Run full validation
    replay.log_input(session_id, "Running full validation...")
    
    results = probe.validate_all()
    
    for result in results:
        status = "[OK]" if result.success else "[X]"
        replay.log_output(
            session_id,
            f"{status} [{result.provider}] {result.check_type}: {result.message}"
        )
        if result.suggestions:
            for suggestion in result.suggestions:
                replay.log_output(session_id, f"    Suggestion: {suggestion}")
    
    # Summary
    passed = sum(1 for r in results if r.success)
    failed = len(results) - passed
    replay.log_output(session_id, f"\nSummary: {passed} passed, {failed} failed")
    
    # Set final status
    final_status = "COMPLETED" if failed == 0 else "COMPLETED_WITH_ISSUES"
    replay.end_session(session_id, status=final_status)
    
except Exception as e:
    replay.log_error(session_id, f"Validation error: {e}")
    replay.end_session(session_id, status="FAILED")

print(f"Session recorded: {session_id}")
```

**Result:** Full validation session recorded for replay

---

## Pattern 6: APIProbe + ContextCompressor

**Use Case:** Compress validation reports before sharing in chat

**Why:** Save tokens when sharing detailed reports

**Code:**

```python
from contextcompressor import ContextCompressor
from apiprobe import APIProbe, format_markdown
from pathlib import Path

compressor = ContextCompressor()
probe = APIProbe(env_path=Path(".env"))

# Generate full validation report
results = probe.validate_all()
full_report = format_markdown(results)

print(f"Full report: {len(full_report)} characters")

# Compress for sharing
compressed = compressor.compress_text(
    full_report,
    query="validation summary and failures",
    method="summary"
)

print(f"Compressed: {len(compressed.compressed_text)} characters")
print(f"Reduction: {(1 - len(compressed.compressed_text)/len(full_report))*100:.1f}%")

# Use compressed version in chat/messages
print("\n=== Compressed Report ===")
print(compressed.compressed_text)

# Keep full report for records
with open("full_validation_report.md", "w") as f:
    f.write(full_report)
print("\nFull report saved to: full_validation_report.md")
```

**Result:** Token-efficient reports for sharing

---

## Pattern 7: APIProbe + ConfigManager

**Use Case:** Centralize APIProbe configuration

**Why:** Share settings across agents and sessions

**Code:**

```python
from configmanager import ConfigManager
from apiprobe import APIProbe
from pathlib import Path

config = ConfigManager()

# Load or create default APIProbe config
apiprobe_config = config.get("apiprobe", {
    "env_path": ".env",
    "default_providers": ["google", "anthropic", "openai", "xai"],
    "timeout": 30,
    "output_format": "table",
    "alert_on_failure": True,
    "history_retention": 100
})

# Initialize with config
probe = APIProbe(env_path=Path(apiprobe_config["env_path"]))

# Run validation with configured providers
results = probe.validate_all(
    providers=apiprobe_config["default_providers"]
)

# Update config based on results
failed = [r for r in results if not r.success]

if failed:
    # Track last failure time
    apiprobe_config["last_failure"] = datetime.now().isoformat()
    apiprobe_config["last_failure_count"] = len(failed)
    
config.set("apiprobe", apiprobe_config)
config.save()

print(f"Configuration saved with {len(failed)} failures logged")
```

**Result:** Centralized, persistent APIProbe configuration

---

## Pattern 8: APIProbe + EnvGuard

**Use Case:** Two-stage validation - .env file then API endpoints

**Why:** Catch configuration issues at multiple levels

**Code:**

```python
from envguard import EnvGuard
from apiprobe import APIProbe
from pathlib import Path

env_path = Path(".env")

# Stage 1: Validate .env file structure (EnvGuard)
print("=== Stage 1: .env File Validation ===")
guard = EnvGuard()
env_issues = guard.scan(env_path)

if env_issues:
    print("[X] .env file has issues:")
    for issue in env_issues:
        print(f"  - {issue}")
    print("\nFix .env issues before proceeding!")
else:
    print("[OK] .env file structure is valid")
    
    # Stage 2: Validate API endpoints (APIProbe)
    print("\n=== Stage 2: API Endpoint Validation ===")
    probe = APIProbe(env_path=env_path)
    results = probe.validate_all()
    
    for r in results:
        status = "[OK]" if r.success else "[X]"
        print(f"{status} {r.provider}: {r.message}")
    
    passed = sum(1 for r in results if r.success)
    failed = len(results) - passed
    
    print(f"\n=== Summary ===")
    print(f"Stage 1 (.env): {'PASSED' if not env_issues else 'FAILED'}")
    print(f"Stage 2 (APIs): {passed}/{len(results)} passed")
    print(f"Overall: {'READY TO DEPLOY' if not env_issues and failed == 0 else 'FIX ISSUES FIRST'}")
```

**Result:** Comprehensive configuration validation at multiple levels

---

## Pattern 9: Pre-Deployment Pipeline

**Use Case:** Complete pre-deployment validation workflow

**Why:** Ensure all configurations are correct before deploying

**Code:**

```python
"""
Pre-Deployment Validation Pipeline
Run this before every deployment!
"""

from pathlib import Path
from datetime import datetime
import sys

# Import Team Brain tools
from apiprobe import APIProbe
from envguard import EnvGuard
from synapselink import quick_send

def run_pre_deployment_validation():
    """Complete pre-deployment validation."""
    
    print("=" * 60)
    print("PRE-DEPLOYMENT VALIDATION PIPELINE")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)
    
    issues = []
    
    # Step 1: Validate .env files
    print("\n[1/3] Validating .env files...")
    guard = EnvGuard()
    for env_file in [".env", "backend/.env"]:
        if Path(env_file).exists():
            env_issues = guard.scan(Path(env_file))
            if env_issues:
                issues.extend([f".env: {i}" for i in env_issues])
                print(f"  [X] {env_file}: {len(env_issues)} issues")
            else:
                print(f"  [OK] {env_file}")
    
    # Step 2: Validate API configurations
    print("\n[2/3] Validating API configurations...")
    probe = APIProbe(env_path=Path(".env"))
    results = probe.validate_all()
    
    for r in results:
        if r.success:
            print(f"  [OK] {r.provider}: {r.message}")
        else:
            issues.append(f"API: {r.provider} - {r.message}")
            print(f"  [X] {r.provider}: {r.message}")
    
    # Step 3: Check for config drift
    print("\n[3/3] Checking for config drift...")
    if Path("data/comms.db").exists():
        diffs = probe.config_diff(Path("data/comms.db"))
        for diff in diffs:
            if diff.severity == "error":
                issues.append(f"Drift: {diff.field} - {diff.message}")
                print(f"  [X] {diff.field}: {diff.message}")
            else:
                print(f"  [!] {diff.field}: {diff.message}")
    else:
        print("  [!] No database found, skipping drift check")
    
    # Summary
    print("\n" + "=" * 60)
    if issues:
        print(f"VALIDATION FAILED: {len(issues)} issues found")
        print("=" * 60)
        for issue in issues:
            print(f"  - {issue}")
        
        # Send alert
        quick_send(
            "FORGE,LOGAN",
            "⛔ Pre-Deployment Validation Failed",
            f"Found {len(issues)} blocking issues:\n\n" +
            "\n".join(f"- {i}" for i in issues),
            priority="HIGH"
        )
        
        return False
    else:
        print("VALIDATION PASSED: Ready to deploy!")
        print("=" * 60)
        
        quick_send(
            "TEAM",
            "✅ Pre-Deployment Validation Passed",
            "All configuration checks passed. Safe to deploy.",
            priority="LOW"
        )
        
        return True

if __name__ == "__main__":
    success = run_pre_deployment_validation()
    sys.exit(0 if success else 1)
```

**Result:** Complete, automated pre-deployment validation

---

## Pattern 10: Full Team Brain Stack

**Use Case:** Ultimate integration - all tools working together

**Why:** Production-grade agent operation with full instrumentation

**Code:**

```python
"""
Full Team Brain Stack Integration
APIProbe + AgentHealth + SessionReplay + TaskQueuePro + SynapseLink
"""

from pathlib import Path
from datetime import datetime

# Import all tools
from apiprobe import APIProbe
from agenthealth import AgentHealth
from sessionreplay import SessionReplay
from taskqueuepro import TaskQueuePro
from synapselink import quick_send
from memorybridge import MemoryBridge

def full_stack_validation(agent_name: str = "FORGE"):
    """
    Run API validation with full Team Brain instrumentation.
    
    - Health tracking
    - Session recording
    - Task creation
    - Team notification
    - History persistence
    """
    
    # Initialize all tools
    health = AgentHealth()
    replay = SessionReplay()
    queue = TaskQueuePro()
    memory = MemoryBridge()
    probe = APIProbe(env_path=Path(".env"))
    
    # Start tracking
    session_id = replay.start_session(agent_name, task="Full Stack API Validation")
    health.start_session(agent_name, session_id=session_id)
    
    try:
        # Log start
        replay.log_input(session_id, "Starting full stack API validation")
        health.heartbeat(agent_name, status="validating")
        
        # Run validation
        results = probe.validate_all()
        
        # Log results
        for r in results:
            status = "[OK]" if r.success else "[X]"
            replay.log_output(session_id, f"{status} {r.provider}: {r.message}")
        
        # Analyze results
        passed = sum(1 for r in results if r.success)
        failed_results = [r for r in results if not r.success]
        
        # Save to history
        history = memory.get("validation_history", default=[])
        history.append({
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "passed": passed,
            "failed": len(failed_results),
            "session_id": session_id
        })
        memory.set("validation_history", history[-100:])
        memory.sync()
        
        if failed_results:
            # Create tasks for failures
            for r in failed_results:
                queue.create_task(
                    title=f"Fix: {r.provider} - {r.check_type}",
                    description=r.message,
                    agent=agent_name,
                    priority=2,
                    tags=["api-config", r.provider]
                )
            
            # Log health issue
            health.log_error(
                agent_name,
                f"API validation: {len(failed_results)} failures"
            )
            
            # Send alert
            quick_send(
                "FORGE,LOGAN",
                f"⚠️ API Validation: {len(failed_results)} Issues",
                "\n".join(f"- {r.provider}: {r.message}" for r in failed_results),
                priority="HIGH"
            )
            
            replay.end_session(session_id, status="COMPLETED_WITH_ISSUES")
        else:
            # Success
            health.heartbeat(
                agent_name,
                status="healthy",
                metadata={"api_validation": "passed"}
            )
            
            quick_send(
                "TEAM",
                "✅ API Validation Passed",
                f"All {passed} checks passed.",
                priority="LOW"
            )
            
            replay.end_session(session_id, status="COMPLETED")
        
        return {
            "passed": passed,
            "failed": len(failed_results),
            "session_id": session_id
        }
        
    except Exception as e:
        # Handle errors
        health.log_error(agent_name, f"Validation error: {e}")
        replay.log_error(session_id, str(e))
        replay.end_session(session_id, status="FAILED")
        
        quick_send(
            "FORGE,LOGAN",
            "⛔ API Validation Error",
            f"Error: {e}",
            priority="HIGH"
        )
        
        raise
        
    finally:
        health.end_session(agent_name, session_id=session_id)

if __name__ == "__main__":
    result = full_stack_validation()
    print(f"\nValidation complete: {result}")
```

**Result:** Fully instrumented, production-grade validation with complete Team Brain integration

---

## 📊 RECOMMENDED INTEGRATION PRIORITY

**Week 1 (Essential):**
1. ✅ SynapseLink - Alert team on failures
2. ✅ EnvGuard - Two-stage validation
3. ✅ Pre-deployment pipeline

**Week 2 (Tracking):**
4. ☐ AgentHealth - Health correlation
5. ☐ MemoryBridge - History persistence
6. ☐ SessionReplay - Debug recording

**Week 3 (Automation):**
7. ☐ TaskQueuePro - Task creation
8. ☐ ConfigManager - Centralized config
9. ☐ Full stack integration

---

## 🔧 TROUBLESHOOTING INTEGRATIONS

**Import Errors:**
```python
# Ensure all tools are in Python path
import sys
from pathlib import Path
sys.path.append(str(Path.home() / "OneDrive/Documents/AutoProjects"))

# Then import
from apiprobe import APIProbe
```

**Version Conflicts:**
```bash
# Check versions
python apiprobe.py --version

# Update if needed
cd AutoProjects/APIProbe
git pull origin main
```

**Configuration Issues:**
```python
# Verify .env file exists
from pathlib import Path
env_path = Path(".env")
if not env_path.exists():
    print("Create .env file with API keys first!")
```

---

**Last Updated:** January 28, 2026  
**Maintained By:** Forge (Team Brain)
