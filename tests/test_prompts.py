"""
Tests for AI prompts.

Validates that prompts are properly constructed and follow best practices.
"""

import pytest

from cars_bot.ai.prompts import (
    CLASSIFY_POST_SYSTEM_PROMPT,
    CLASSIFY_POST_USER_PROMPT_TEMPLATE,
    CLASSIFICATION_FEW_SHOT_EXAMPLES,
    EXTRACT_DATA_SYSTEM_PROMPT,
    EXTRACT_DATA_USER_PROMPT_TEMPLATE,
    EXTRACTION_FEW_SHOT_EXAMPLES,
    GENERATE_DESCRIPTION_SYSTEM_PROMPT,
    GENERATE_DESCRIPTION_USER_PROMPT_TEMPLATE,
    GENERATION_FEW_SHOT_EXAMPLES,
    VALIDATION_SYSTEM_PROMPT,
    VALIDATION_USER_PROMPT_TEMPLATE,
    build_classification_prompt,
    build_extraction_prompt,
    build_generation_prompt,
    build_validation_prompt,
)


# =============================================================================
# PROMPT CONTENT TESTS
# =============================================================================

class TestPromptContent:
    """Test that prompts contain required elements."""
    
    def test_classification_prompt_has_russian_instructions(self):
        """Classification prompt should have Russian instructions."""
        assert "Ты эксперт" in CLASSIFY_POST_SYSTEM_PROMPT
        assert "ЗАДАЧА" in CLASSIFY_POST_SYSTEM_PROMPT
        assert "Классифицируй" in CLASSIFY_POST_USER_PROMPT_TEMPLATE
    
    def test_classification_prompt_has_output_format(self):
        """Classification prompt should specify JSON output format."""
        assert "JSON" in CLASSIFY_POST_SYSTEM_PROMPT
        assert "is_selling_post" in CLASSIFY_POST_SYSTEM_PROMPT
        assert "confidence" in CLASSIFY_POST_SYSTEM_PROMPT
        assert "reasoning" in CLASSIFY_POST_SYSTEM_PROMPT
    
    def test_classification_prompt_has_criteria(self):
        """Classification prompt should have clear criteria."""
        assert "КРИТЕРИИ" in CLASSIFY_POST_SYSTEM_PROMPT
        assert "марка" in CLASSIFY_POST_SYSTEM_PROMPT
        assert "модель" in CLASSIFY_POST_SYSTEM_PROMPT
        assert "цена" in CLASSIFY_POST_SYSTEM_PROMPT.lower()
    
    def test_extraction_prompt_has_field_guidelines(self):
        """Extraction prompt should define all fields."""
        required_fields = [
            "brand",
            "model",
            "engine_volume",
            "transmission",
            "year",
            "owners_count",
            "mileage",
            "autoteka_status",
            "equipment",
            "price",
            "market_price",
            "price_justification",
        ]
        
        for field in required_fields:
            assert field in EXTRACT_DATA_SYSTEM_PROMPT, f"Missing field: {field}"
    
    def test_extraction_prompt_has_transmission_types(self):
        """Extraction prompt should specify transmission types."""
        transmission_types = ["automatic", "manual", "robot", "variator"]
        
        for trans_type in transmission_types:
            assert trans_type in EXTRACT_DATA_SYSTEM_PROMPT
    
    def test_extraction_prompt_has_autoteka_statuses(self):
        """Extraction prompt should specify autoteka statuses."""
        statuses = ["green", "has_accidents", "unknown"]
        
        for status in statuses:
            assert status in EXTRACT_DATA_SYSTEM_PROMPT
    
    def test_generation_prompt_has_requirements(self):
        """Generation prompt should have clear requirements."""
        assert "ТРЕБОВАНИЯ" in GENERATE_DESCRIPTION_SYSTEM_PROMPT
        assert "уникальн" in GENERATE_DESCRIPTION_SYSTEM_PROMPT.lower()
        assert "профессиональн" in GENERATE_DESCRIPTION_SYSTEM_PROMPT.lower()
    
    def test_generation_prompt_forbids_unwanted_elements(self):
        """Generation prompt should forbid certain elements."""
        assert "ЗАПРЕЩЕНО" in GENERATE_DESCRIPTION_SYSTEM_PROMPT
        assert "эмодзи" in GENERATE_DESCRIPTION_SYSTEM_PROMPT.lower()
        assert "первого лица" in GENERATE_DESCRIPTION_SYSTEM_PROMPT.lower()
    
    def test_validation_prompt_has_rules(self):
        """Validation prompt should have validation rules."""
        assert "ВАЛИДАЦИИ" in VALIDATION_SYSTEM_PROMPT
        assert "brand" in VALIDATION_SYSTEM_PROMPT
        assert "year" in VALIDATION_SYSTEM_PROMPT
        assert "price" in VALIDATION_SYSTEM_PROMPT


# =============================================================================
# FEW-SHOT EXAMPLES TESTS
# =============================================================================

class TestFewShotExamples:
    """Test that few-shot examples are properly formatted."""
    
    def test_classification_examples_exist(self):
        """Classification should have few-shot examples."""
        assert len(CLASSIFICATION_FEW_SHOT_EXAMPLES) >= 2
    
    def test_classification_examples_have_required_keys(self):
        """Classification examples should have user and assistant keys."""
        for example in CLASSIFICATION_FEW_SHOT_EXAMPLES:
            assert "user" in example
            assert "assistant" in example
    
    def test_classification_examples_have_valid_json(self):
        """Classification examples assistant responses should be valid JSON strings."""
        import json
        
        for example in CLASSIFICATION_FEW_SHOT_EXAMPLES:
            try:
                parsed = json.loads(example["assistant"])
                assert "is_selling_post" in parsed
                assert "confidence" in parsed
                assert "reasoning" in parsed
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON in example: {example['assistant']}")
    
    def test_extraction_examples_exist(self):
        """Extraction should have few-shot examples."""
        assert len(EXTRACTION_FEW_SHOT_EXAMPLES) >= 1
    
    def test_extraction_examples_have_required_keys(self):
        """Extraction examples should have user and assistant keys."""
        for example in EXTRACTION_FEW_SHOT_EXAMPLES:
            assert "user" in example
            assert "assistant" in example
    
    def test_extraction_examples_have_valid_json(self):
        """Extraction examples assistant responses should be valid JSON strings."""
        import json
        
        for example in EXTRACTION_FEW_SHOT_EXAMPLES:
            try:
                parsed = json.loads(example["assistant"])
                # Check at least some required fields
                assert "brand" in parsed
                assert "model" in parsed
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON in example: {example['assistant']}")
    
    def test_generation_examples_exist(self):
        """Generation should have few-shot examples."""
        assert len(GENERATION_FEW_SHOT_EXAMPLES) >= 1
    
    def test_generation_examples_have_required_keys(self):
        """Generation examples should have user and assistant keys."""
        for example in GENERATION_FEW_SHOT_EXAMPLES:
            assert "user" in example
            assert "assistant" in example
    
    def test_generation_examples_have_valid_json(self):
        """Generation examples assistant responses should be valid JSON strings."""
        import json
        
        for example in GENERATION_FEW_SHOT_EXAMPLES:
            try:
                parsed = json.loads(example["assistant"])
                assert "generated_text" in parsed
                assert "key_points_preserved" in parsed
                assert "tone" in parsed
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON in example: {example['assistant']}")


# =============================================================================
# HELPER FUNCTIONS TESTS
# =============================================================================

class TestHelperFunctions:
    """Test prompt building helper functions."""
    
    def test_build_classification_prompt_returns_tuple(self):
        """build_classification_prompt should return tuple."""
        result = build_classification_prompt("Test post")
        assert isinstance(result, tuple)
        assert len(result) == 2
    
    def test_build_classification_prompt_truncates_long_text(self):
        """build_classification_prompt should truncate long text."""
        long_text = "A" * 5000
        system_prompt, user_prompt = build_classification_prompt(long_text)
        
        # User prompt should not contain full 5000 chars
        assert len(user_prompt) < len(long_text) + 100
    
    def test_build_extraction_prompt_returns_tuple(self):
        """build_extraction_prompt should return tuple."""
        result = build_extraction_prompt("Test post")
        assert isinstance(result, tuple)
        assert len(result) == 2
    
    def test_build_extraction_prompt_truncates_long_text(self):
        """build_extraction_prompt should truncate long text."""
        long_text = "A" * 5000
        system_prompt, user_prompt = build_extraction_prompt(long_text)
        
        # User prompt should not contain full 5000 chars
        assert len(user_prompt) < len(long_text) + 100
    
    def test_build_generation_prompt_returns_tuple(self):
        """build_generation_prompt should return tuple."""
        result = build_generation_prompt("Original text", '{"brand": "BMW"}')
        assert isinstance(result, tuple)
        assert len(result) == 2
    
    def test_build_generation_prompt_truncates_long_text(self):
        """build_generation_prompt should truncate long texts."""
        long_text = "A" * 5000
        long_json = '{"data": "' + "B" * 3000 + '"}'
        
        system_prompt, user_prompt = build_generation_prompt(long_text, long_json)
        
        # Should truncate both
        assert len(user_prompt) < len(long_text) + len(long_json) + 200
    
    def test_build_validation_prompt_returns_tuple(self):
        """build_validation_prompt should return tuple."""
        result = build_validation_prompt('{"brand": "BMW", "year": 2008}')
        assert isinstance(result, tuple)
        assert len(result) == 2
    
    def test_build_prompts_include_placeholders(self):
        """Build prompts should include actual content."""
        test_text = "Продам BMW 3 серии 2008 года"
        
        _, user_prompt = build_classification_prompt(test_text)
        assert test_text in user_prompt
        
        _, user_prompt = build_extraction_prompt(test_text)
        assert test_text in user_prompt
        
        test_json = '{"brand": "BMW"}'
        _, user_prompt = build_generation_prompt(test_text, test_json)
        assert test_text in user_prompt
        assert test_json in user_prompt


# =============================================================================
# TOKEN OPTIMIZATION TESTS
# =============================================================================

class TestTokenOptimization:
    """Test that prompts are optimized for token usage."""
    
    def test_prompts_are_not_excessively_long(self):
        """System prompts should be reasonably sized."""
        max_chars = 3000  # Reasonable limit for system prompt
        
        prompts_to_check = [
            ("Classification", CLASSIFY_POST_SYSTEM_PROMPT),
            ("Extraction", EXTRACT_DATA_SYSTEM_PROMPT),
            ("Generation", GENERATE_DESCRIPTION_SYSTEM_PROMPT),
            ("Validation", VALIDATION_SYSTEM_PROMPT),
        ]
        
        for name, prompt in prompts_to_check:
            assert len(prompt) < max_chars, (
                f"{name} prompt is too long: {len(prompt)} chars "
                f"(max {max_chars})"
            )
    
    def test_prompts_avoid_redundancy(self):
        """Prompts should not repeat the same instruction multiple times."""
        # This is a heuristic test - check for repeated phrases
        
        def count_phrase_occurrences(text: str, phrase: str) -> int:
            return text.lower().count(phrase.lower())
        
        # Should not repeat "JSON" too many times in system prompt
        assert count_phrase_occurrences(CLASSIFY_POST_SYSTEM_PROMPT, "JSON") <= 3
        assert count_phrase_occurrences(EXTRACT_DATA_SYSTEM_PROMPT, "JSON") <= 3
    
    def test_user_prompts_are_concise(self):
        """User prompt templates should be concise."""
        templates = [
            CLASSIFY_POST_USER_PROMPT_TEMPLATE,
            EXTRACT_DATA_USER_PROMPT_TEMPLATE,
            GENERATE_DESCRIPTION_USER_PROMPT_TEMPLATE,
            VALIDATION_USER_PROMPT_TEMPLATE,
        ]
        
        for template in templates:
            # User prompts should be very short (excluding placeholder)
            template_only = template.replace("{text}", "").replace("{original_text}", "")
            template_only = template_only.replace("{car_data_json}", "")
            
            assert len(template_only.strip()) < 300, (
                f"User prompt template is too verbose: {len(template_only)} chars"
            )


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestPromptIntegration:
    """Test that prompts work together as expected."""
    
    def test_all_prompts_use_russian(self):
        """All prompts should primarily use Russian."""
        prompts = [
            CLASSIFY_POST_SYSTEM_PROMPT,
            EXTRACT_DATA_SYSTEM_PROMPT,
            GENERATE_DESCRIPTION_SYSTEM_PROMPT,
            VALIDATION_SYSTEM_PROMPT,
        ]
        
        for prompt in prompts:
            # Check for Cyrillic characters (indicates Russian)
            cyrillic_count = sum(1 for c in prompt if '\u0400' <= c <= '\u04FF')
            total_letters = sum(1 for c in prompt if c.isalpha())
            
            if total_letters > 0:
                cyrillic_ratio = cyrillic_count / total_letters
                assert cyrillic_ratio > 0.5, (
                    f"Prompt should use more Russian (only {cyrillic_ratio:.1%} Cyrillic)"
                )
    
    def test_prompts_specify_response_format(self):
        """All prompts should specify JSON response format."""
        prompts = [
            CLASSIFY_POST_SYSTEM_PROMPT,
            EXTRACT_DATA_SYSTEM_PROMPT,
            GENERATE_DESCRIPTION_SYSTEM_PROMPT,
            VALIDATION_SYSTEM_PROMPT,
        ]
        
        for prompt in prompts:
            assert "JSON" in prompt.upper()
    
    def test_helper_functions_signature_compatibility(self):
        """Helper functions should have consistent signatures."""
        # All should accept text as first parameter
        # All should return tuple[str, str]
        
        test_text = "Test"
        test_json = '{"test": "data"}'
        
        result1 = build_classification_prompt(test_text)
        result2 = build_extraction_prompt(test_text)
        result3 = build_generation_prompt(test_text, test_json)
        result4 = build_validation_prompt(test_json)
        
        for result in [result1, result2, result3, result4]:
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert isinstance(result[0], str)  # system prompt
            assert isinstance(result[1], str)  # user prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])




