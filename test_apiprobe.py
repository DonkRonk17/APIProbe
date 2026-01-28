#!/usr/bin/env python3
"""
Comprehensive test suite for APIProbe.

Tests cover:
- Core functionality (list models, test models, config diff)
- Edge cases (missing keys, invalid providers)
- Error handling (network errors, malformed responses)
- Integration scenarios (full validation)
- Output formatting (table, JSON, markdown)

Run: python test_apiprobe.py
"""

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from apiprobe import (
    APIProbe,
    ValidationResult,
    ModelInfo,
    ConfigDiff,
    load_env_file,
    get_api_key,
    mask_api_key,
    list_models,
    test_model,
    config_diff,
    validate_all,
    format_table,
    format_result,
    format_json,
    format_markdown,
    MODEL_CORRECTIONS,
    FEATURE_SUPPORT,
)


class TestEnvFileLoading(unittest.TestCase):
    """Test environment file loading functionality."""
    
    def test_load_env_file_basic(self):
        """Test loading a basic .env file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("GOOGLE_API_KEY=test_key_123\n")
            f.write("ANTHROPIC_API_KEY=claude_key_456\n")
            f.name
        
        try:
            env_vars = load_env_file(Path(f.name))
            self.assertEqual(env_vars.get("GOOGLE_API_KEY"), "test_key_123")
            self.assertEqual(env_vars.get("ANTHROPIC_API_KEY"), "claude_key_456")
        finally:
            os.unlink(f.name)
    
    def test_load_env_file_with_quotes(self):
        """Test loading .env file with quoted values."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write('GOOGLE_API_KEY="quoted_key"\n')
            f.write("OPENAI_API_KEY='single_quoted'\n")
        
        try:
            env_vars = load_env_file(Path(f.name))
            self.assertEqual(env_vars.get("GOOGLE_API_KEY"), "quoted_key")
            self.assertEqual(env_vars.get("OPENAI_API_KEY"), "single_quoted")
        finally:
            os.unlink(f.name)
    
    def test_load_env_file_with_comments(self):
        """Test that comments are ignored."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("# This is a comment\n")
            f.write("GOOGLE_API_KEY=test_key\n")
            f.write("# Another comment\n")
        
        try:
            env_vars = load_env_file(Path(f.name))
            self.assertEqual(env_vars.get("GOOGLE_API_KEY"), "test_key")
            self.assertNotIn("#", str(env_vars))
        finally:
            os.unlink(f.name)
    
    def test_load_env_file_nonexistent(self):
        """Test loading nonexistent .env file returns empty dict."""
        env_vars = load_env_file(Path("/nonexistent/path/.env"))
        self.assertEqual(env_vars, {})
    
    def test_load_env_file_empty_lines(self):
        """Test that empty lines are handled."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("\n\nGOOGLE_API_KEY=test\n\n")
        
        try:
            env_vars = load_env_file(Path(f.name))
            self.assertEqual(env_vars.get("GOOGLE_API_KEY"), "test")
        finally:
            os.unlink(f.name)


class TestAPIKeyRetrieval(unittest.TestCase):
    """Test API key retrieval functionality."""
    
    def test_get_api_key_from_env(self):
        """Test getting API key from environment variable."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "env_key_123"}):
            key = get_api_key("google")
            self.assertEqual(key, "env_key_123")
    
    def test_get_api_key_fallback_names(self):
        """Test fallback API key names."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "gemini_fallback"}):
            key = get_api_key("google")
            self.assertEqual(key, "gemini_fallback")
    
    def test_get_api_key_not_found(self):
        """Test when no API key is found."""
        with patch.dict(os.environ, {}, clear=True):
            key = get_api_key("google")
            self.assertIsNone(key)
    
    def test_get_api_key_from_env_file(self):
        """Test getting API key from .env file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("ANTHROPIC_API_KEY=file_key_789\n")
        
        try:
            with patch.dict(os.environ, {}, clear=True):
                key = get_api_key("anthropic", Path(f.name))
                self.assertEqual(key, "file_key_789")
        finally:
            os.unlink(f.name)


class TestMaskAPIKey(unittest.TestCase):
    """Test API key masking functionality."""
    
    def test_mask_api_key_normal(self):
        """Test normal API key masking."""
        masked = mask_api_key("sk-1234567890abcdef")
        self.assertTrue(masked.startswith("sk-1"))
        self.assertTrue(masked.endswith("cdef"))
        self.assertIn("...", masked)
    
    def test_mask_api_key_short(self):
        """Test masking short API key."""
        masked = mask_api_key("short")
        self.assertEqual(masked, "***")
    
    def test_mask_api_key_empty(self):
        """Test masking empty API key."""
        masked = mask_api_key("")
        self.assertEqual(masked, "***")
    
    def test_mask_api_key_none(self):
        """Test masking None API key."""
        masked = mask_api_key(None)
        self.assertEqual(masked, "***")


class TestValidationResult(unittest.TestCase):
    """Test ValidationResult data class."""
    
    def test_validation_result_creation(self):
        """Test creating a ValidationResult."""
        result = ValidationResult(
            success=True,
            provider="google",
            check_type="model_test",
            message="Test passed"
        )
        self.assertTrue(result.success)
        self.assertEqual(result.provider, "google")
    
    def test_validation_result_to_dict(self):
        """Test converting ValidationResult to dict."""
        result = ValidationResult(
            success=False,
            provider="anthropic",
            check_type="api_key",
            message="Key not found",
            suggestions=["Set API key"]
        )
        d = result.to_dict()
        self.assertFalse(d["success"])
        self.assertEqual(d["suggestions"], ["Set API key"])


class TestModelInfo(unittest.TestCase):
    """Test ModelInfo data class."""
    
    def test_model_info_creation(self):
        """Test creating a ModelInfo."""
        model = ModelInfo(
            name="gemini-2.0-flash",
            provider="google",
            display_name="Gemini 2.0 Flash",
            input_token_limit=1000000
        )
        self.assertEqual(model.name, "gemini-2.0-flash")
        self.assertEqual(model.provider, "google")
    
    def test_model_info_to_dict(self):
        """Test converting ModelInfo to dict."""
        model = ModelInfo(name="gpt-4", provider="openai")
        d = model.to_dict()
        self.assertEqual(d["name"], "gpt-4")
        self.assertEqual(d["display_name"], "gpt-4")  # Falls back to name


class TestConfigDiff(unittest.TestCase):
    """Test ConfigDiff data class."""
    
    def test_config_diff_creation(self):
        """Test creating a ConfigDiff."""
        diff = ConfigDiff(
            field="model_name",
            db_value="old_model",
            code_value="new_model",
            severity="warning",
            message="Configuration drift"
        )
        self.assertEqual(diff.field, "model_name")
        self.assertEqual(diff.severity, "warning")
    
    def test_config_diff_to_dict(self):
        """Test converting ConfigDiff to dict."""
        diff = ConfigDiff(
            field="api_version",
            db_value="v1",
            code_value="v1beta",
            severity="error",
            message="Version mismatch"
        )
        d = diff.to_dict()
        self.assertEqual(d["db_value"], "v1")
        self.assertEqual(d["code_value"], "v1beta")


class TestModelCorrections(unittest.TestCase):
    """Test model name correction detection."""
    
    def test_known_corrections_exist(self):
        """Test that known corrections are defined."""
        self.assertIn("google", MODEL_CORRECTIONS)
        self.assertIn("gemini-2.0-flash-exp", MODEL_CORRECTIONS["google"])
    
    def test_deprecated_model_detected(self):
        """Test that deprecated model names are caught."""
        # Mock the API request to avoid actual calls
        with patch('apiprobe.make_api_request') as mock_request:
            mock_request.return_value = (200, {"candidates": []})
            
            result = test_model("google", "gemini-2.0-flash-exp", "fake_key")
            self.assertFalse(result.success)
            self.assertIn("incorrect or deprecated", result.message)
            self.assertIn("suggestions", dir(result))


class TestFeatureSupport(unittest.TestCase):
    """Test feature support validation."""
    
    def test_google_v1_limitations(self):
        """Test that Google v1 API limitations are known."""
        v1_features = FEATURE_SUPPORT["google"]["v1"]
        self.assertFalse(v1_features["systemInstruction"])
        self.assertFalse(v1_features["tools"])
    
    def test_google_v1beta_features(self):
        """Test that Google v1beta API has full features."""
        v1beta_features = FEATURE_SUPPORT["google"]["v1beta"]
        self.assertTrue(v1beta_features["systemInstruction"])
        self.assertTrue(v1beta_features["tools"])
    
    def test_unsupported_feature_detection(self):
        """Test detection of unsupported features."""
        with patch('apiprobe.make_api_request') as mock_request:
            mock_request.return_value = (200, {"candidates": []})
            
            result = test_model(
                "google", "gemini-2.0-flash", "fake_key",
                features=["systemInstruction", "tools"],
                api_version="v1"  # v1 doesn't support these
            )
            self.assertFalse(result.success)
            self.assertIn("not supported", result.message)


class TestConfigDiffFunction(unittest.TestCase):
    """Test configuration diff functionality."""
    
    def test_config_diff_nonexistent_db(self):
        """Test config diff with nonexistent database."""
        diffs = config_diff(Path("/nonexistent/db.sqlite"))
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].severity, "error")
        self.assertIn("not found", diffs[0].message)
    
    def test_config_diff_empty_db(self):
        """Test config diff with empty database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = Path(f.name)
        
        try:
            # Create empty database
            conn = sqlite3.connect(str(db_path))
            conn.close()
            
            diffs = config_diff(db_path)
            # Should return empty list for empty DB (no config found)
            self.assertIsInstance(diffs, list)
        finally:
            os.unlink(str(db_path))
    
    def test_config_diff_with_model_data(self):
        """Test config diff finds incorrect model names in DB."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = Path(f.name)
        
        try:
            # Create database with provider config
            conn = sqlite3.connect(str(db_path))
            conn.execute("""
                CREATE TABLE ai_provider_config (
                    id INTEGER PRIMARY KEY,
                    model_name TEXT
                )
            """)
            conn.execute(
                "INSERT INTO ai_provider_config (model_name) VALUES (?)",
                ("gemini-2.0-flash-exp",)  # Known incorrect name
            )
            conn.commit()
            conn.close()
            
            diffs = config_diff(db_path)
            # Should detect the incorrect model name
            self.assertGreater(len(diffs), 0)
        finally:
            os.unlink(str(db_path))


class TestFormatTable(unittest.TestCase):
    """Test table formatting."""
    
    def test_format_table_basic(self):
        """Test basic table formatting."""
        headers = ["Name", "Value"]
        rows = [["test", "123"], ["hello", "world"]]
        table = format_table(headers, rows)
        
        self.assertIn("Name", table)
        self.assertIn("Value", table)
        self.assertIn("test", table)
        self.assertIn("123", table)
    
    def test_format_table_empty(self):
        """Test formatting empty table."""
        table = format_table(["A", "B"], [])
        self.assertEqual(table, "No data")
    
    def test_format_table_long_values(self):
        """Test table with long values (should be truncated)."""
        headers = ["Name"]
        rows = [["a" * 100]]  # Very long value
        table = format_table(headers, rows)
        
        # Should not exceed 50 chars per column
        lines = table.split('\n')
        for line in lines:
            self.assertLessEqual(len(line), 100)


class TestFormatResult(unittest.TestCase):
    """Test result formatting."""
    
    def test_format_result_success(self):
        """Test formatting successful result."""
        result = ValidationResult(
            success=True,
            provider="google",
            check_type="test",
            message="All good"
        )
        formatted = format_result(result, use_color=False)
        
        self.assertIn("[OK]", formatted)
        self.assertIn("GOOGLE", formatted)
        self.assertIn("All good", formatted)
    
    def test_format_result_failure(self):
        """Test formatting failed result."""
        result = ValidationResult(
            success=False,
            provider="anthropic",
            check_type="api_key",
            message="Key missing",
            suggestions=["Set the key"]
        )
        formatted = format_result(result, use_color=False)
        
        self.assertIn("[X]", formatted)
        self.assertIn("ANTHROPIC", formatted)
        self.assertIn("Suggestions", formatted)
        self.assertIn("Set the key", formatted)


class TestFormatJSON(unittest.TestCase):
    """Test JSON formatting."""
    
    def test_format_json_single_result(self):
        """Test JSON formatting of single result."""
        result = ValidationResult(
            success=True,
            provider="openai",
            check_type="test",
            message="OK"
        )
        json_str = format_json(result)
        data = json.loads(json_str)
        
        self.assertTrue(data["success"])
        self.assertEqual(data["provider"], "openai")
    
    def test_format_json_list(self):
        """Test JSON formatting of list."""
        results = [
            ValidationResult(success=True, provider="a", check_type="t", message="m"),
            ValidationResult(success=False, provider="b", check_type="t", message="m"),
        ]
        json_str = format_json(results)
        data = json.loads(json_str)
        
        self.assertEqual(len(data), 2)
        self.assertTrue(data[0]["success"])
        self.assertFalse(data[1]["success"])


class TestFormatMarkdown(unittest.TestCase):
    """Test Markdown formatting."""
    
    def test_format_markdown_report(self):
        """Test Markdown report generation."""
        results = [
            ValidationResult(
                success=True,
                provider="google",
                check_type="model_test",
                message="Test passed"
            ),
            ValidationResult(
                success=False,
                provider="anthropic",
                check_type="api_key",
                message="Missing key",
                suggestions=["Set ANTHROPIC_API_KEY"]
            ),
        ]
        md = format_markdown(results)
        
        self.assertIn("# APIProbe Validation Report", md)
        self.assertIn("## Summary", md)
        self.assertIn("**Passed:** 1", md)
        self.assertIn("**Failed:** 1", md)
        self.assertIn("[OK]", md)
        self.assertIn("[X]", md)


class TestAPIProbeClass(unittest.TestCase):
    """Test the main APIProbe class."""
    
    def test_apiprobe_initialization(self):
        """Test APIProbe initialization."""
        probe = APIProbe()
        self.assertIsNone(probe.env_path)
        
        probe2 = APIProbe(env_path=Path(".env"))
        self.assertEqual(probe2.env_path, Path(".env"))
    
    def test_apiprobe_list_models_no_key(self):
        """Test list_models raises error without API key."""
        probe = APIProbe()
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                probe.list_models("google")
    
    def test_apiprobe_test_model_no_key(self):
        """Test test_model raises error without API key."""
        probe = APIProbe()
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                probe.test_model("google", "gemini-2.0-flash")


class TestValidateAll(unittest.TestCase):
    """Test full validation functionality."""
    
    def test_validate_all_no_keys(self):
        """Test validate_all reports missing API keys."""
        with patch.dict(os.environ, {}, clear=True):
            results = validate_all()
            
            # Should have failure results for each provider without keys
            failed = [r for r in results if not r.success]
            self.assertGreater(len(failed), 0)
            
            # Check that suggestions are provided
            for result in failed:
                if result.check_type == "api_key":
                    self.assertGreater(len(result.suggestions), 0)
    
    @patch('apiprobe.list_models')
    @patch('apiprobe.test_model')
    def test_validate_all_with_mocked_apis(self, mock_test, mock_list):
        """Test validate_all with mocked API responses."""
        mock_list.return_value = [
            ModelInfo(name="test-model", provider="google")
        ]
        mock_test.return_value = ValidationResult(
            success=True,
            provider="google",
            check_type="model_test",
            message="OK"
        )
        
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "fake_key"}):
            results = validate_all(providers=["google"])
            
            # Should have successful results
            passed = [r for r in results if r.success]
            self.assertGreater(len(passed), 0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def test_unknown_provider(self):
        """Test handling of unknown provider."""
        result = test_model("unknown_provider", "model", "key")
        self.assertFalse(result.success)
        self.assertIn("Unknown provider", result.message)
    
    def test_empty_model_name(self):
        """Test handling of empty model name."""
        with patch('apiprobe.make_api_request') as mock_request:
            mock_request.return_value = (404, {"error": "Not found"})
            result = test_model("google", "", "key")
            # Should still process (API will reject)
            self.assertIsInstance(result, ValidationResult)
    
    def test_special_characters_in_model_name(self):
        """Test handling of special characters in model name."""
        with patch('apiprobe.make_api_request') as mock_request:
            mock_request.return_value = (404, {"error": "Not found"})
            result = test_model("google", "model/with/slashes", "key")
            self.assertIsInstance(result, ValidationResult)


class TestIntegrationScenarios(unittest.TestCase):
    """Test realistic integration scenarios."""
    
    @patch('apiprobe.make_api_request')
    def test_google_404_scenario(self, mock_request):
        """Test the exact scenario that triggered APIProbe creation."""
        # Simulate 404 for wrong model name
        mock_request.return_value = (404, {
            "error": {"message": "Model not found: gemini-3-flash-preview"}
        })
        
        result = test_model("google", "gemini-3-flash-preview", "fake_key")
        
        # Should detect this is a known incorrect name
        self.assertFalse(result.success)
        # Should suggest correction
        self.assertTrue(
            any("gemini-1.5-flash" in s for s in result.suggestions) or
            "incorrect or deprecated" in result.message
        )
    
    @patch('apiprobe.make_api_request')
    def test_feature_mismatch_scenario(self, mock_request):
        """Test feature support mismatch detection."""
        mock_request.return_value = (400, {
            "error": {"message": "systemInstruction not supported"}
        })
        
        # Try to use v1 API with systemInstruction
        result = test_model(
            "google", "gemini-2.0-flash", "fake_key",
            features=["systemInstruction"],
            api_version="v1"
        )
        
        self.assertFalse(result.success)


def run_tests():
    """Run all tests with nice output."""
    print("=" * 70)
    print("TESTING: APIProbe v1.0")
    print("=" * 70)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestEnvFileLoading))
    suite.addTests(loader.loadTestsFromTestCase(TestAPIKeyRetrieval))
    suite.addTests(loader.loadTestsFromTestCase(TestMaskAPIKey))
    suite.addTests(loader.loadTestsFromTestCase(TestValidationResult))
    suite.addTests(loader.loadTestsFromTestCase(TestModelInfo))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigDiff))
    suite.addTests(loader.loadTestsFromTestCase(TestModelCorrections))
    suite.addTests(loader.loadTestsFromTestCase(TestFeatureSupport))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigDiffFunction))
    suite.addTests(loader.loadTestsFromTestCase(TestFormatTable))
    suite.addTests(loader.loadTestsFromTestCase(TestFormatResult))
    suite.addTests(loader.loadTestsFromTestCase(TestFormatJSON))
    suite.addTests(loader.loadTestsFromTestCase(TestFormatMarkdown))
    suite.addTests(loader.loadTestsFromTestCase(TestAPIProbeClass))
    suite.addTests(loader.loadTestsFromTestCase(TestValidateAll))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationScenarios))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 70)
    print(f"RESULTS: {result.testsRun} tests")
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"[OK] Passed: {passed}")
    if result.failures:
        print(f"[X] Failed: {len(result.failures)}")
    if result.errors:
        print(f"[X] Errors: {len(result.errors)}")
    print("=" * 70)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
