#!/usr/bin/env python3
"""
APIProbe - API Configuration Validator

Validates AI provider configurations BEFORE deployment disasters. Tests actual
API endpoints, lists available models, validates feature support, and detects
configuration drift between code and database.

Born from a 2+ hour Gemini debugging nightmare where the root causes were:
1. Database cached old model name (code changes don't update existing DB records)
2. Wrong model name for API version (gemini-1.5-flash not in v1beta)
3. API version mismatch (v1 doesn't support systemInstruction/tools)

One apiprobe command would have found all three issues in seconds.

Author: Forge (Team Brain)
For: Logan Smith / Metaphy LLC
Version: 1.0
Date: January 28, 2026
License: MIT
"""

import argparse
import json
import os
import re
import sqlite3
import ssl
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


# ============================================================================
# CONSTANTS
# ============================================================================

VERSION = "1.0.0"
TOOL_NAME = "APIProbe"

# Provider API endpoints
PROVIDER_ENDPOINTS = {
    "google": {
        "v1": "https://generativelanguage.googleapis.com/v1",
        "v1beta": "https://generativelanguage.googleapis.com/v1beta",
    },
    "anthropic": {
        "v1": "https://api.anthropic.com/v1",
    },
    "openai": {
        "v1": "https://api.openai.com/v1",
    },
    "xai": {
        "v1": "https://api.x.ai/v1",
    }
}

# Default API versions per provider
DEFAULT_API_VERSIONS = {
    "google": "v1beta",
    "anthropic": "v1",
    "openai": "v1",
    "xai": "v1",
}

# Model name patterns for each provider
MODEL_PATTERNS = {
    "google": r"gemini[\w\-\.]*",
    "anthropic": r"claude[\w\-\.]*",
    "openai": r"gpt[\w\-\.]*|o1[\w\-\.]*|chatgpt[\w\-\.]*",
    "xai": r"grok[\w\-\.]*",
}

# Feature support by provider/version (known constraints)
FEATURE_SUPPORT = {
    "google": {
        "v1": {
            "systemInstruction": False,
            "tools": False,
            "generationConfig": True,
        },
        "v1beta": {
            "systemInstruction": True,
            "tools": True,
            "generationConfig": True,
        }
    },
    "anthropic": {
        "v1": {
            "system": True,
            "tools": True,
            "max_tokens": True,
        }
    },
    "openai": {
        "v1": {
            "system": True,
            "functions": True,
            "tools": True,
            "response_format": True,
        }
    },
    "xai": {
        "v1": {
            "system": True,
            "tools": False,  # Limited tool support
        }
    }
}

# Known model aliases and corrections
MODEL_CORRECTIONS = {
    "google": {
        "gemini-2.0-flash-exp": "gemini-2.0-flash",
        "gemini-3-flash-preview": "gemini-1.5-flash",  # Common mistake
    }
}


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ValidationResult:
    """Result of a validation check."""
    success: bool
    provider: str
    check_type: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "provider": self.provider,
            "check_type": self.check_type,
            "message": self.message,
            "details": self.details,
            "suggestions": self.suggestions,
        }


@dataclass
class ModelInfo:
    """Information about an AI model."""
    name: str
    provider: str
    display_name: str = ""
    description: str = ""
    input_token_limit: int = 0
    output_token_limit: int = 0
    supported_features: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "provider": self.provider,
            "display_name": self.display_name or self.name,
            "description": self.description,
            "input_token_limit": self.input_token_limit,
            "output_token_limit": self.output_token_limit,
            "supported_features": self.supported_features,
        }


@dataclass
class ConfigDiff:
    """Represents a configuration difference."""
    field: str
    db_value: Any
    code_value: Any
    severity: str  # "info", "warning", "error"
    message: str
    
    def to_dict(self) -> Dict:
        return {
            "field": self.field,
            "db_value": self.db_value,
            "code_value": self.code_value,
            "severity": self.severity,
            "message": self.message,
        }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def load_env_file(env_path: Path) -> Dict[str, str]:
    """Load environment variables from a .env file."""
    env_vars = {}
    if not env_path.exists():
        return env_vars
    
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            # Handle KEY=VALUE format
            if '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                env_vars[key] = value
    return env_vars


def get_api_key(provider: str, env_path: Optional[Path] = None) -> Optional[str]:
    """Get API key for a provider from environment or .env file."""
    key_names = {
        "google": ["GOOGLE_API_KEY", "GEMINI_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
        "openai": ["OPENAI_API_KEY"],
        "xai": ["XAI_API_KEY", "GROK_API_KEY"],
    }
    
    # Load from .env file if provided
    env_vars = {}
    if env_path:
        env_vars = load_env_file(env_path)
    
    # Try each possible key name
    for key_name in key_names.get(provider, []):
        # Check environment first
        value = os.environ.get(key_name)
        if value:
            return value
        # Check .env file
        value = env_vars.get(key_name)
        if value:
            return value
    
    return None


def make_api_request(url: str, method: str = "GET", 
                     headers: Optional[Dict] = None,
                     data: Optional[Dict] = None,
                     timeout: int = 30) -> Tuple[int, Dict]:
    """Make an HTTP request to an API endpoint."""
    headers = headers or {}
    
    # Create SSL context that handles certificates
    ctx = ssl.create_default_context()
    
    request_data = None
    if data:
        request_data = json.dumps(data).encode('utf-8')
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'
    
    req = urllib.request.Request(url, data=request_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            body = response.read().decode('utf-8')
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else ""
        try:
            error_data = json.loads(body) if body else {"error": str(e)}
        except json.JSONDecodeError:
            error_data = {"error": body or str(e)}
        return e.code, error_data
    except urllib.error.URLError as e:
        return 0, {"error": f"Connection failed: {str(e.reason)}"}
    except Exception as e:
        return 0, {"error": str(e)}


def mask_api_key(key: str, visible_chars: int = 4) -> str:
    """Mask an API key for display, showing only first/last few characters."""
    if not key or len(key) <= visible_chars * 2:
        return "***"
    return f"{key[:visible_chars]}...{key[-visible_chars:]}"


# ============================================================================
# PROVIDER-SPECIFIC FUNCTIONS
# ============================================================================

def list_google_models(api_key: str, api_version: str = "v1beta") -> List[ModelInfo]:
    """List available models from Google Gemini API."""
    models = []
    base_url = PROVIDER_ENDPOINTS["google"].get(api_version)
    if not base_url:
        return models
    
    url = f"{base_url}/models?key={api_key}"
    status, response = make_api_request(url)
    
    if status == 200 and "models" in response:
        for model in response["models"]:
            name = model.get("name", "").replace("models/", "")
            models.append(ModelInfo(
                name=name,
                provider="google",
                display_name=model.get("displayName", name),
                description=model.get("description", ""),
                input_token_limit=model.get("inputTokenLimit", 0),
                output_token_limit=model.get("outputTokenLimit", 0),
                supported_features=model.get("supportedGenerationMethods", []),
            ))
    
    return models


def list_anthropic_models(api_key: str) -> List[ModelInfo]:
    """List available models from Anthropic API."""
    # Anthropic doesn't have a models endpoint, so we return known models
    known_models = [
        ModelInfo(name="claude-opus-4-20250514", provider="anthropic",
                  display_name="Claude Opus 4", input_token_limit=200000),
        ModelInfo(name="claude-sonnet-4-20250514", provider="anthropic",
                  display_name="Claude Sonnet 4", input_token_limit=200000),
        ModelInfo(name="claude-3-5-sonnet-20241022", provider="anthropic",
                  display_name="Claude 3.5 Sonnet", input_token_limit=200000),
        ModelInfo(name="claude-3-5-haiku-20241022", provider="anthropic",
                  display_name="Claude 3.5 Haiku", input_token_limit=200000),
        ModelInfo(name="claude-3-opus-20240229", provider="anthropic",
                  display_name="Claude 3 Opus", input_token_limit=200000),
    ]
    
    # Verify API key works by making a simple request
    url = f"{PROVIDER_ENDPOINTS['anthropic']['v1']}/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    data = {
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "Hi"}]
    }
    
    status, _ = make_api_request(url, method="POST", headers=headers, data=data)
    
    if status in (200, 201):
        return known_models
    elif status == 401:
        return []  # Invalid API key
    else:
        return known_models  # Return known models anyway


def list_openai_models(api_key: str) -> List[ModelInfo]:
    """List available models from OpenAI API."""
    models = []
    url = f"{PROVIDER_ENDPOINTS['openai']['v1']}/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    status, response = make_api_request(url, headers=headers)
    
    if status == 200 and "data" in response:
        for model in response["data"]:
            model_id = model.get("id", "")
            # Filter to relevant models (GPT, o1, etc.)
            if any(pattern in model_id.lower() for pattern in ["gpt", "o1", "chatgpt"]):
                models.append(ModelInfo(
                    name=model_id,
                    provider="openai",
                    display_name=model_id,
                ))
    
    return models


def list_xai_models(api_key: str) -> List[ModelInfo]:
    """List available models from xAI API."""
    models = []
    url = f"{PROVIDER_ENDPOINTS['xai']['v1']}/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    status, response = make_api_request(url, headers=headers)
    
    if status == 200 and "data" in response:
        for model in response["data"]:
            model_id = model.get("id", "")
            models.append(ModelInfo(
                name=model_id,
                provider="xai",
                display_name=model_id,
            ))
    elif status == 200 and isinstance(response, list):
        for model in response:
            if isinstance(model, dict):
                model_id = model.get("id", model.get("name", ""))
                models.append(ModelInfo(
                    name=model_id,
                    provider="xai",
                    display_name=model_id,
                ))
    
    # If no models returned, provide known models
    if not models:
        models = [
            ModelInfo(name="grok-beta", provider="xai", display_name="Grok Beta"),
            ModelInfo(name="grok-2", provider="xai", display_name="Grok 2"),
        ]
    
    return models


# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def list_models(provider: str, api_key: str, 
                api_version: Optional[str] = None) -> List[ModelInfo]:
    """List available models for a provider."""
    provider = provider.lower()
    api_version = api_version or DEFAULT_API_VERSIONS.get(provider, "v1")
    
    if provider == "google":
        return list_google_models(api_key, api_version)
    elif provider == "anthropic":
        return list_anthropic_models(api_key)
    elif provider == "openai":
        return list_openai_models(api_key)
    elif provider == "xai":
        return list_xai_models(api_key)
    else:
        return []


def test_model(provider: str, model: str, api_key: str,
               features: Optional[List[str]] = None,
               api_version: Optional[str] = None) -> ValidationResult:
    """Test a model with optional feature validation."""
    provider = provider.lower()
    api_version = api_version or DEFAULT_API_VERSIONS.get(provider, "v1")
    features = features or []
    
    # Check for known model corrections
    corrections = MODEL_CORRECTIONS.get(provider, {})
    if model in corrections:
        corrected = corrections[model]
        return ValidationResult(
            success=False,
            provider=provider,
            check_type="model_test",
            message=f"Model name '{model}' is incorrect or deprecated",
            details={"requested_model": model, "corrected_model": corrected},
            suggestions=[f"Use '{corrected}' instead of '{model}'"]
        )
    
    # Check feature support based on known constraints
    feature_support = FEATURE_SUPPORT.get(provider, {}).get(api_version, {})
    unsupported_features = []
    for feature in features:
        if feature in feature_support and not feature_support[feature]:
            unsupported_features.append(feature)
    
    if unsupported_features:
        return ValidationResult(
            success=False,
            provider=provider,
            check_type="feature_validation",
            message=f"Features not supported in {api_version}: {', '.join(unsupported_features)}",
            details={
                "requested_features": features,
                "unsupported_features": unsupported_features,
                "api_version": api_version,
            },
            suggestions=[
                f"Use a different API version (e.g., v1beta for Google)",
                f"Remove unsupported features: {', '.join(unsupported_features)}"
            ]
        )
    
    # Make actual API test request
    if provider == "google":
        return _test_google_model(model, api_key, api_version, features)
    elif provider == "anthropic":
        return _test_anthropic_model(model, api_key, features)
    elif provider == "openai":
        return _test_openai_model(model, api_key, features)
    elif provider == "xai":
        return _test_xai_model(model, api_key, features)
    else:
        return ValidationResult(
            success=False,
            provider=provider,
            check_type="model_test",
            message=f"Unknown provider: {provider}",
            suggestions=["Supported providers: google, anthropic, openai, xai"]
        )


def _test_google_model(model: str, api_key: str, api_version: str,
                       features: List[str]) -> ValidationResult:
    """Test a Google Gemini model."""
    base_url = PROVIDER_ENDPOINTS["google"].get(api_version)
    url = f"{base_url}/models/{model}:generateContent?key={api_key}"
    
    # Build request with optional features
    request_data: Dict[str, Any] = {
        "contents": [{"parts": [{"text": "Say 'test successful'"}]}]
    }
    
    if "systemInstruction" in features:
        request_data["systemInstruction"] = {"parts": [{"text": "You are a test assistant."}]}
    
    if "tools" in features:
        request_data["tools"] = [{"functionDeclarations": [
            {"name": "test_function", "description": "A test function"}
        ]}]
    
    status, response = make_api_request(url, method="POST", data=request_data)
    
    if status == 200:
        return ValidationResult(
            success=True,
            provider="google",
            check_type="model_test",
            message=f"Model '{model}' is working correctly",
            details={"model": model, "api_version": api_version, "features_tested": features}
        )
    elif status == 404:
        return ValidationResult(
            success=False,
            provider="google",
            check_type="model_test",
            message=f"Model '{model}' not found",
            details={"error": response, "api_version": api_version},
            suggestions=[
                "Run 'apiprobe list-models --provider google' to see available models",
                f"Check if the model name is spelled correctly"
            ]
        )
    elif status == 400:
        error_msg = response.get("error", {}).get("message", str(response))
        return ValidationResult(
            success=False,
            provider="google",
            check_type="model_test",
            message=f"Bad request: {error_msg}",
            details={"error": response, "api_version": api_version, "features": features},
            suggestions=[
                "Check if the API version supports the requested features",
                "Try with api_version='v1beta' for full feature support"
            ]
        )
    else:
        return ValidationResult(
            success=False,
            provider="google",
            check_type="model_test",
            message=f"API error (status {status})",
            details={"error": response, "status": status}
        )


def _test_anthropic_model(model: str, api_key: str,
                          features: List[str]) -> ValidationResult:
    """Test an Anthropic Claude model."""
    url = f"{PROVIDER_ENDPOINTS['anthropic']['v1']}/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    
    request_data: Dict[str, Any] = {
        "model": model,
        "max_tokens": 10,
        "messages": [{"role": "user", "content": "Say 'test successful'"}]
    }
    
    if "system" in features:
        request_data["system"] = "You are a test assistant."
    
    if "tools" in features:
        request_data["tools"] = [{
            "name": "test_function",
            "description": "A test function",
            "input_schema": {"type": "object", "properties": {}}
        }]
    
    status, response = make_api_request(url, method="POST", headers=headers, data=request_data)
    
    if status in (200, 201):
        return ValidationResult(
            success=True,
            provider="anthropic",
            check_type="model_test",
            message=f"Model '{model}' is working correctly",
            details={"model": model, "features_tested": features}
        )
    elif status == 404:
        return ValidationResult(
            success=False,
            provider="anthropic",
            check_type="model_test",
            message=f"Model '{model}' not found",
            details={"error": response},
            suggestions=["Check the Anthropic documentation for available models"]
        )
    else:
        error_msg = response.get("error", {}).get("message", str(response))
        return ValidationResult(
            success=False,
            provider="anthropic",
            check_type="model_test",
            message=f"API error: {error_msg}",
            details={"error": response, "status": status}
        )


def _test_openai_model(model: str, api_key: str,
                       features: List[str]) -> ValidationResult:
    """Test an OpenAI model."""
    url = f"{PROVIDER_ENDPOINTS['openai']['v1']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    request_data: Dict[str, Any] = {
        "model": model,
        "max_tokens": 10,
        "messages": [{"role": "user", "content": "Say 'test successful'"}]
    }
    
    if "system" in features:
        request_data["messages"].insert(0, {"role": "system", "content": "You are a test assistant."})
    
    if "tools" in features:
        request_data["tools"] = [{
            "type": "function",
            "function": {
                "name": "test_function",
                "description": "A test function",
                "parameters": {"type": "object", "properties": {}}
            }
        }]
    
    status, response = make_api_request(url, method="POST", headers=headers, data=request_data)
    
    if status == 200:
        return ValidationResult(
            success=True,
            provider="openai",
            check_type="model_test",
            message=f"Model '{model}' is working correctly",
            details={"model": model, "features_tested": features}
        )
    else:
        error_msg = response.get("error", {}).get("message", str(response))
        return ValidationResult(
            success=False,
            provider="openai",
            check_type="model_test",
            message=f"API error: {error_msg}",
            details={"error": response, "status": status}
        )


def _test_xai_model(model: str, api_key: str,
                    features: List[str]) -> ValidationResult:
    """Test an xAI Grok model."""
    url = f"{PROVIDER_ENDPOINTS['xai']['v1']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    request_data: Dict[str, Any] = {
        "model": model,
        "max_tokens": 10,
        "messages": [{"role": "user", "content": "Say 'test successful'"}]
    }
    
    if "system" in features:
        request_data["messages"].insert(0, {"role": "system", "content": "You are a test assistant."})
    
    status, response = make_api_request(url, method="POST", headers=headers, data=request_data)
    
    if status == 200:
        return ValidationResult(
            success=True,
            provider="xai",
            check_type="model_test",
            message=f"Model '{model}' is working correctly",
            details={"model": model, "features_tested": features}
        )
    else:
        error_msg = response.get("error", {}).get("message", str(response))
        return ValidationResult(
            success=False,
            provider="xai",
            check_type="model_test",
            message=f"API error: {error_msg}",
            details={"error": response, "status": status}
        )


def config_diff(db_path: Path, code_path: Optional[Path] = None,
                table_name: str = "ai_providers") -> List[ConfigDiff]:
    """Compare database configuration vs code defaults."""
    diffs = []
    
    if not db_path.exists():
        return [ConfigDiff(
            field="database",
            db_value=None,
            code_value=str(db_path),
            severity="error",
            message=f"Database file not found: {db_path}"
        )]
    
    # Read database configuration
    db_config = {}
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Try to find configuration table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Look for provider/model configuration
        config_tables = [t for t in tables if any(
            kw in t.lower() for kw in ["provider", "model", "ai", "config"]
        )]
        
        for table in config_tables:
            try:
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                for row in rows:
                    row_dict = dict(row)
                    # Look for model name fields
                    for key, value in row_dict.items():
                        if any(kw in key.lower() for kw in ["model", "name"]):
                            db_config[f"{table}.{key}"] = value
            except sqlite3.Error:
                continue
        
        conn.close()
    except sqlite3.Error as e:
        return [ConfigDiff(
            field="database",
            db_value=None,
            code_value=str(db_path),
            severity="error",
            message=f"Database error: {e}"
        )]
    
    # Check for known model name issues
    for field, value in db_config.items():
        if isinstance(value, str):
            for provider, corrections in MODEL_CORRECTIONS.items():
                if value in corrections:
                    diffs.append(ConfigDiff(
                        field=field,
                        db_value=value,
                        code_value=corrections[value],
                        severity="error",
                        message=f"Deprecated/incorrect model name in database"
                    ))
    
    # If code path provided, compare against it
    if code_path and code_path.exists():
        code_config = _extract_config_from_code(code_path)
        
        # Find discrepancies
        for field, db_value in db_config.items():
            field_name = field.split('.')[-1]
            for code_field, code_value in code_config.items():
                if field_name.lower() in code_field.lower():
                    if db_value != code_value:
                        diffs.append(ConfigDiff(
                            field=field,
                            db_value=db_value,
                            code_value=code_value,
                            severity="warning",
                            message=f"Configuration drift detected"
                        ))
    
    return diffs


def _extract_config_from_code(code_path: Path) -> Dict[str, str]:
    """Extract configuration values from code files."""
    config = {}
    
    if code_path.is_file():
        files = [code_path]
    else:
        files = list(code_path.glob("**/*.py"))
    
    # Patterns to match configuration
    patterns = [
        r'model\s*[=:]\s*["\']([^"\']+)["\']',
        r'MODEL\s*[=:]\s*["\']([^"\']+)["\']',
        r'default_model\s*[=:]\s*["\']([^"\']+)["\']',
        r'model_name\s*[=:]\s*["\']([^"\']+)["\']',
    ]
    
    for file_path in files:
        try:
            content = file_path.read_text(encoding='utf-8')
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    config[f"{file_path.name}:model"] = match
        except Exception:
            continue
    
    return config


def validate_all(env_path: Optional[Path] = None,
                 db_path: Optional[Path] = None,
                 providers: Optional[List[str]] = None) -> List[ValidationResult]:
    """Full validation of all configured providers."""
    results = []
    providers = providers or ["google", "anthropic", "openai", "xai"]
    
    for provider in providers:
        api_key = get_api_key(provider, env_path)
        
        if not api_key:
            results.append(ValidationResult(
                success=False,
                provider=provider,
                check_type="api_key",
                message=f"No API key found for {provider}",
                suggestions=[
                    f"Set {provider.upper()}_API_KEY environment variable",
                    "Or provide a .env file with the API key"
                ]
            ))
            continue
        
        # Test listing models
        models = list_models(provider, api_key)
        if models:
            results.append(ValidationResult(
                success=True,
                provider=provider,
                check_type="list_models",
                message=f"Found {len(models)} models for {provider}",
                details={"model_count": len(models), "models": [m.name for m in models[:5]]}
            ))
            
            # Test the first model
            if models:
                test_result = test_model(provider, models[0].name, api_key)
                results.append(test_result)
        else:
            results.append(ValidationResult(
                success=False,
                provider=provider,
                check_type="list_models",
                message=f"Could not list models for {provider}",
                suggestions=["Check API key validity", "Check network connection"]
            ))
    
    # Check for config drift if database provided
    if db_path and db_path.exists():
        diffs = config_diff(db_path)
        for diff in diffs:
            results.append(ValidationResult(
                success=diff.severity != "error",
                provider="database",
                check_type="config_diff",
                message=diff.message,
                details=diff.to_dict()
            ))
    
    return results


# ============================================================================
# CLI OUTPUT FORMATTERS
# ============================================================================

def format_table(headers: List[str], rows: List[List[str]], 
                 column_widths: Optional[List[int]] = None) -> str:
    """Format data as an ASCII table."""
    if not rows:
        return "No data"
    
    # Calculate column widths
    if not column_widths:
        column_widths = []
        for i, header in enumerate(headers):
            max_width = len(header)
            for row in rows:
                if i < len(row):
                    max_width = max(max_width, len(str(row[i])))
            column_widths.append(min(max_width, 50))  # Cap at 50 chars
    
    # Build header
    header_line = " | ".join(
        header.ljust(column_widths[i]) for i, header in enumerate(headers)
    )
    separator = "-+-".join("-" * w for w in column_widths)
    
    # Build rows
    row_lines = []
    for row in rows:
        row_str = " | ".join(
            str(row[i] if i < len(row) else "").ljust(column_widths[i])[:column_widths[i]]
            for i in range(len(headers))
        )
        row_lines.append(row_str)
    
    return f"{header_line}\n{separator}\n" + "\n".join(row_lines)


def format_result(result: ValidationResult, use_color: bool = True) -> str:
    """Format a validation result for display."""
    status = "[OK]" if result.success else "[X]"
    if use_color:
        status_color = "\033[92m" if result.success else "\033[91m"
        reset = "\033[0m"
        status = f"{status_color}{status}{reset}"
    
    output = f"{status} [{result.provider.upper()}] {result.message}"
    
    if result.suggestions:
        output += "\n    Suggestions:"
        for suggestion in result.suggestions:
            output += f"\n      - {suggestion}"
    
    return output


def format_json(data: Any) -> str:
    """Format data as JSON."""
    if hasattr(data, 'to_dict'):
        data = data.to_dict()
    elif isinstance(data, list):
        data = [item.to_dict() if hasattr(item, 'to_dict') else item for item in data]
    return json.dumps(data, indent=2)


def format_markdown(results: List[ValidationResult]) -> str:
    """Format results as Markdown."""
    lines = ["# APIProbe Validation Report", ""]
    lines.append(f"**Generated:** {datetime.now().isoformat()}")
    lines.append("")
    
    # Summary
    passed = sum(1 for r in results if r.success)
    failed = len(results) - passed
    lines.append("## Summary")
    lines.append(f"- **Passed:** {passed}")
    lines.append(f"- **Failed:** {failed}")
    lines.append(f"- **Total:** {len(results)}")
    lines.append("")
    
    # Details
    lines.append("## Details")
    for result in results:
        status = "[OK]" if result.success else "[X]"
        lines.append(f"### {status} {result.provider.upper()} - {result.check_type}")
        lines.append(f"{result.message}")
        if result.suggestions:
            lines.append("**Suggestions:**")
            for s in result.suggestions:
                lines.append(f"- {s}")
        lines.append("")
    
    return "\n".join(lines)


# ============================================================================
# CLI INTERFACE
# ============================================================================

class APIProbe:
    """Main APIProbe class for programmatic access."""
    
    def __init__(self, env_path: Optional[Path] = None):
        """Initialize APIProbe with optional .env file path."""
        self.env_path = env_path
    
    def list_models(self, provider: str, 
                    api_version: Optional[str] = None) -> List[ModelInfo]:
        """List available models for a provider."""
        api_key = get_api_key(provider, self.env_path)
        if not api_key:
            raise ValueError(f"No API key found for {provider}")
        return list_models(provider, api_key, api_version)
    
    def test_model(self, provider: str, model: str,
                   features: Optional[List[str]] = None,
                   api_version: Optional[str] = None) -> ValidationResult:
        """Test a specific model."""
        api_key = get_api_key(provider, self.env_path)
        if not api_key:
            raise ValueError(f"No API key found for {provider}")
        return test_model(provider, model, api_key, features, api_version)
    
    def config_diff(self, db_path: Path,
                    code_path: Optional[Path] = None) -> List[ConfigDiff]:
        """Compare database config vs code defaults."""
        return config_diff(db_path, code_path)
    
    def validate_all(self, db_path: Optional[Path] = None,
                     providers: Optional[List[str]] = None) -> List[ValidationResult]:
        """Full validation of all configured providers."""
        return validate_all(self.env_path, db_path, providers)


def main():
    """CLI entry point."""
    # Fix Windows console encoding for Unicode
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass
    
    parser = argparse.ArgumentParser(
        description=f'{TOOL_NAME} v{VERSION} - API Configuration Validator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list-models --provider google
  %(prog)s test-model --provider google --model gemini-2.0-flash
  %(prog)s test-model --provider google --model gemini-2.0-flash --features systemInstruction,tools
  %(prog)s config-diff --db data/comms.db --code backend/
  %(prog)s validate-all --env .env --db data/comms.db

Supported Providers:
  google     - Google Gemini (API key: GOOGLE_API_KEY)
  anthropic  - Anthropic Claude (API key: ANTHROPIC_API_KEY)
  openai     - OpenAI GPT (API key: OPENAI_API_KEY)
  xai        - xAI Grok (API key: XAI_API_KEY)

For more information: https://github.com/DonkRonk17/APIProbe
        """
    )
    
    parser.add_argument('--version', action='version', version=f'{TOOL_NAME} v{VERSION}')
    parser.add_argument('--env', type=Path, help='Path to .env file with API keys')
    parser.add_argument('--format', choices=['table', 'json', 'markdown'], 
                       default='table', help='Output format (default: table)')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # list-models command
    list_parser = subparsers.add_parser('list-models', help='List available models')
    list_parser.add_argument('--provider', required=True,
                            choices=['google', 'anthropic', 'openai', 'xai'],
                            help='AI provider')
    list_parser.add_argument('--api-version', help='API version (e.g., v1, v1beta)')
    list_parser.add_argument('--api-key', help='API key (overrides environment)')
    
    # test-model command
    test_parser = subparsers.add_parser('test-model', help='Test a specific model')
    test_parser.add_argument('--provider', required=True,
                            choices=['google', 'anthropic', 'openai', 'xai'],
                            help='AI provider')
    test_parser.add_argument('--model', required=True, help='Model name to test')
    test_parser.add_argument('--features', help='Comma-separated features to test')
    test_parser.add_argument('--api-version', help='API version (e.g., v1, v1beta)')
    test_parser.add_argument('--api-key', help='API key (overrides environment)')
    
    # config-diff command
    diff_parser = subparsers.add_parser('config-diff', help='Compare DB vs code config')
    diff_parser.add_argument('--db', type=Path, required=True, help='Database file path')
    diff_parser.add_argument('--code', type=Path, help='Code directory or file')
    
    # validate-all command
    validate_parser = subparsers.add_parser('validate-all', help='Full validation')
    validate_parser.add_argument('--db', type=Path, help='Database file path')
    validate_parser.add_argument('--providers', help='Comma-separated list of providers')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    use_color = not args.no_color and sys.stdout.isatty()
    
    try:
        if args.command == 'list-models':
            api_key = args.api_key or get_api_key(args.provider, args.env)
            if not api_key:
                print(f"[X] No API key found for {args.provider}")
                print(f"    Set {args.provider.upper()}_API_KEY or use --api-key")
                return 1
            
            models = list_models(args.provider, api_key, args.api_version)
            
            if args.format == 'json':
                print(format_json(models))
            else:
                if models:
                    headers = ["Model Name", "Display Name", "Input Limit"]
                    rows = [[m.name, m.display_name, str(m.input_token_limit) or "N/A"] 
                           for m in models]
                    print(f"\n{args.provider.upper()} Models ({len(models)} found):\n")
                    print(format_table(headers, rows))
                else:
                    print(f"[!] No models found for {args.provider}")
        
        elif args.command == 'test-model':
            api_key = args.api_key or get_api_key(args.provider, args.env)
            if not api_key:
                print(f"[X] No API key found for {args.provider}")
                return 1
            
            features = args.features.split(',') if args.features else []
            result = test_model(args.provider, args.model, api_key, 
                              features, args.api_version)
            
            if args.format == 'json':
                print(format_json(result))
            else:
                print(format_result(result, use_color))
            
            return 0 if result.success else 1
        
        elif args.command == 'config-diff':
            diffs = config_diff(args.db, args.code)
            
            if args.format == 'json':
                print(format_json(diffs))
            else:
                if diffs:
                    print(f"\nConfiguration Differences Found ({len(diffs)}):\n")
                    for diff in diffs:
                        severity = diff.severity.upper()
                        print(f"[{severity}] {diff.field}")
                        print(f"    DB value:   {diff.db_value}")
                        print(f"    Code value: {diff.code_value}")
                        print(f"    {diff.message}\n")
                    return 1 if any(d.severity == "error" for d in diffs) else 0
                else:
                    print("[OK] No configuration differences found")
        
        elif args.command == 'validate-all':
            providers = args.providers.split(',') if args.providers else None
            results = validate_all(args.env, args.db, providers)
            
            if args.format == 'json':
                print(format_json(results))
            elif args.format == 'markdown':
                print(format_markdown(results))
            else:
                print(f"\n{'='*60}")
                print(f"  {TOOL_NAME} Validation Report")
                print(f"{'='*60}\n")
                
                for result in results:
                    print(format_result(result, use_color))
                    print()
                
                passed = sum(1 for r in results if r.success)
                failed = len(results) - passed
                
                print(f"{'='*60}")
                print(f"  Summary: {passed} passed, {failed} failed")
                print(f"{'='*60}")
                
                return 0 if failed == 0 else 1
    
    except KeyboardInterrupt:
        print("\n[!] Operation cancelled")
        return 130
    except Exception as e:
        print(f"[X] Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
