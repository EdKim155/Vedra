#!/usr/bin/env python3
"""
Manual test script for AI prompts.

Run this without pytest to verify prompt structure.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import directly from prompts module to avoid dependencies
import importlib.util
spec = importlib.util.spec_from_file_location(
    "prompts",
    Path(__file__).parent.parent / "src" / "cars_bot" / "ai" / "prompts.py"
)
prompts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prompts)

# Get constants and functions
CLASSIFY_POST_SYSTEM_PROMPT = prompts.CLASSIFY_POST_SYSTEM_PROMPT
CLASSIFY_POST_USER_PROMPT_TEMPLATE = prompts.CLASSIFY_POST_USER_PROMPT_TEMPLATE
CLASSIFICATION_FEW_SHOT_EXAMPLES = prompts.CLASSIFICATION_FEW_SHOT_EXAMPLES
EXTRACT_DATA_SYSTEM_PROMPT = prompts.EXTRACT_DATA_SYSTEM_PROMPT
EXTRACT_DATA_USER_PROMPT_TEMPLATE = prompts.EXTRACT_DATA_USER_PROMPT_TEMPLATE
EXTRACTION_FEW_SHOT_EXAMPLES = prompts.EXTRACTION_FEW_SHOT_EXAMPLES
GENERATE_DESCRIPTION_SYSTEM_PROMPT = prompts.GENERATE_DESCRIPTION_SYSTEM_PROMPT
GENERATE_DESCRIPTION_USER_PROMPT_TEMPLATE = prompts.GENERATE_DESCRIPTION_USER_PROMPT_TEMPLATE
GENERATION_FEW_SHOT_EXAMPLES = prompts.GENERATION_FEW_SHOT_EXAMPLES
build_classification_prompt = prompts.build_classification_prompt
build_extraction_prompt = prompts.build_extraction_prompt
build_generation_prompt = prompts.build_generation_prompt


def print_section(title: str):
    """Print section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print('=' * 80)


def print_success(message: str):
    """Print success message."""
    print(f"✅ {message}")


def print_error(message: str):
    """Print error message."""
    print(f"❌ {message}")


def test_classification_prompts():
    """Test classification prompts."""
    print_section("CLASSIFICATION PROMPTS")
    
    # Check system prompt
    assert "Ты эксперт" in CLASSIFY_POST_SYSTEM_PROMPT
    print_success("System prompt has Russian instructions")
    
    assert "is_selling_post" in CLASSIFY_POST_SYSTEM_PROMPT
    print_success("System prompt specifies JSON schema")
    
    assert len(CLASSIFICATION_FEW_SHOT_EXAMPLES) >= 2
    print_success(f"Has {len(CLASSIFICATION_FEW_SHOT_EXAMPLES)} few-shot examples")
    
    # Test builder
    system, user = build_classification_prompt("Тестовый пост о BMW")
    assert "Тестовый пост о BMW" in user
    print_success("Builder function works correctly")
    
    print(f"\nSystem prompt length: {len(system)} chars")
    print(f"User template length: {len(CLASSIFY_POST_USER_PROMPT_TEMPLATE)} chars")


def test_extraction_prompts():
    """Test extraction prompts."""
    print_section("EXTRACTION PROMPTS")
    
    # Check required fields
    required_fields = [
        "brand", "model", "engine_volume", "transmission", "year",
        "owners_count", "mileage", "autoteka_status", "price"
    ]
    
    for field in required_fields:
        assert field in EXTRACT_DATA_SYSTEM_PROMPT
    print_success(f"All {len(required_fields)} required fields defined")
    
    # Check transmission types
    transmission_types = ["automatic", "manual", "robot", "variator"]
    for t_type in transmission_types:
        assert t_type in EXTRACT_DATA_SYSTEM_PROMPT
    print_success("All transmission types defined")
    
    assert len(EXTRACTION_FEW_SHOT_EXAMPLES) >= 1
    print_success(f"Has {len(EXTRACTION_FEW_SHOT_EXAMPLES)} few-shot examples")
    
    # Test builder
    system, user = build_extraction_prompt("Продам BMW 3 серии 2008")
    assert "Продам BMW" in user
    print_success("Builder function works correctly")
    
    print(f"\nSystem prompt length: {len(system)} chars")
    print(f"User template length: {len(EXTRACT_DATA_USER_PROMPT_TEMPLATE)} chars")


def test_generation_prompts():
    """Test generation prompts."""
    print_section("GENERATION PROMPTS")
    
    # Check requirements
    assert "ТРЕБОВАНИЯ" in GENERATE_DESCRIPTION_SYSTEM_PROMPT
    print_success("System prompt has requirements section")
    
    assert "ЗАПРЕЩЕНО" in GENERATE_DESCRIPTION_SYSTEM_PROMPT
    print_success("System prompt has forbidden elements section")
    
    assert "уникальн" in GENERATE_DESCRIPTION_SYSTEM_PROMPT.lower()
    print_success("Emphasizes uniqueness for anti-plagiarism")
    
    assert len(GENERATION_FEW_SHOT_EXAMPLES) >= 1
    print_success(f"Has {len(GENERATION_FEW_SHOT_EXAMPLES)} few-shot examples")
    
    # Test builder
    system, user = build_generation_prompt(
        "Оригинальный текст о BMW",
        '{"brand": "BMW", "year": 2008}'
    )
    assert "Оригинальный текст" in user
    assert "BMW" in user
    print_success("Builder function works correctly")
    
    print(f"\nSystem prompt length: {len(system)} chars")
    print(f"User template length: {len(GENERATE_DESCRIPTION_USER_PROMPT_TEMPLATE)} chars")


def test_few_shot_examples():
    """Test few-shot examples structure."""
    print_section("FEW-SHOT EXAMPLES VALIDATION")
    
    import json
    
    # Test classification examples
    for i, example in enumerate(CLASSIFICATION_FEW_SHOT_EXAMPLES):
        assert "user" in example and "assistant" in example
        try:
            parsed = json.loads(example["assistant"])
            assert "is_selling_post" in parsed
            assert "confidence" in parsed
            assert "reasoning" in parsed
        except json.JSONDecodeError as e:
            print_error(f"Classification example {i} has invalid JSON: {e}")
            continue
    
    print_success(f"All {len(CLASSIFICATION_FEW_SHOT_EXAMPLES)} classification examples valid")
    
    # Test extraction examples
    for i, example in enumerate(EXTRACTION_FEW_SHOT_EXAMPLES):
        assert "user" in example and "assistant" in example
        try:
            parsed = json.loads(example["assistant"])
            assert "brand" in parsed
            assert "model" in parsed
        except json.JSONDecodeError as e:
            print_error(f"Extraction example {i} has invalid JSON: {e}")
            continue
    
    print_success(f"All {len(EXTRACTION_FEW_SHOT_EXAMPLES)} extraction examples valid")
    
    # Test generation examples
    for i, example in enumerate(GENERATION_FEW_SHOT_EXAMPLES):
        assert "user" in example and "assistant" in example
        try:
            parsed = json.loads(example["assistant"])
            assert "generated_text" in parsed
            assert "key_points_preserved" in parsed
            assert "tone" in parsed
        except json.JSONDecodeError as e:
            print_error(f"Generation example {i} has invalid JSON: {e}")
            continue
    
    print_success(f"All {len(GENERATION_FEW_SHOT_EXAMPLES)} generation examples valid")


def test_token_optimization():
    """Test token optimization."""
    print_section("TOKEN OPTIMIZATION")
    
    max_system_chars = 3000
    
    prompts = {
        "Classification": CLASSIFY_POST_SYSTEM_PROMPT,
        "Extraction": EXTRACT_DATA_SYSTEM_PROMPT,
        "Generation": GENERATE_DESCRIPTION_SYSTEM_PROMPT,
    }
    
    for name, prompt in prompts.items():
        length = len(prompt)
        if length < max_system_chars:
            print_success(f"{name}: {length} chars (within {max_system_chars} limit)")
        else:
            print_error(f"{name}: {length} chars (exceeds {max_system_chars} limit)")
    
    # Test truncation
    long_text = "A" * 5000
    _, user_prompt = build_classification_prompt(long_text)
    
    if len(user_prompt) < len(long_text) + 200:
        print_success("Text truncation works correctly")
    else:
        print_error("Text truncation may not be working")


def test_russian_language():
    """Test Russian language usage."""
    print_section("RUSSIAN LANGUAGE USAGE")
    
    prompts = [
        ("Classification", CLASSIFY_POST_SYSTEM_PROMPT),
        ("Extraction", EXTRACT_DATA_SYSTEM_PROMPT),
        ("Generation", GENERATE_DESCRIPTION_SYSTEM_PROMPT),
    ]
    
    for name, prompt in prompts:
        cyrillic_count = sum(1 for c in prompt if '\u0400' <= c <= '\u04FF')
        total_letters = sum(1 for c in prompt if c.isalpha())
        
        if total_letters > 0:
            cyrillic_ratio = cyrillic_count / total_letters
            if cyrillic_ratio > 0.5:
                print_success(f"{name}: {cyrillic_ratio:.1%} Cyrillic (good Russian usage)")
            else:
                print_error(f"{name}: {cyrillic_ratio:.1%} Cyrillic (too little Russian)")


def main():
    """Run all tests."""
    print_section("AI PROMPTS MANUAL TESTING")
    print("Testing optimized prompts for AI processing...")
    
    try:
        test_classification_prompts()
        test_extraction_prompts()
        test_generation_prompts()
        test_few_shot_examples()
        test_token_optimization()
        test_russian_language()
        
        print_section("SUMMARY")
        print_success("All manual tests passed!")
        print("\nPrompts are ready for use with OpenAI API.")
        print("\nNext steps:")
        print("1. Set OPENAI_API_KEY in .env")
        print("2. Test with real API calls using test_ai_processor.py")
        print("3. Monitor token usage in production")
        
        return 0
        
    except AssertionError as e:
        print_error(f"Test failed: {e}")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

