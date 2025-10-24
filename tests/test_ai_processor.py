"""
Unit tests for AI Processor.

Tests cover:
- Pydantic model validation
- Prompt building
- AI classification
- Car data extraction
- Description generation
- Error handling and retries
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError

from cars_bot.ai.models import (
    AIProcessingResult,
    CarDataExtraction,
    ClassificationResult,
    UniqueDescription,
)
from cars_bot.ai.processor import AIProcessor, AIProcessorConfig
from cars_bot.ai.prompts import (
    build_classification_prompt,
    build_extraction_prompt,
    build_generation_prompt,
)


class TestPydanticModels:
    """Test Pydantic models for AI responses."""
    
    def test_classification_result_valid(self):
        """Test valid classification result."""
        result = ClassificationResult(
            is_selling_post=True,
            confidence=0.95,
            reasoning="Contains price and car details"
        )
        
        assert result.is_selling_post is True
        assert result.confidence == 0.95
        assert "price" in result.reasoning.lower()
    
    def test_classification_result_invalid_confidence(self):
        """Test invalid confidence score."""
        with pytest.raises(ValidationError):
            ClassificationResult(
                is_selling_post=True,
                confidence=1.5,  # > 1.0
            )
        
        with pytest.raises(ValidationError):
            ClassificationResult(
                is_selling_post=True,
                confidence=-0.1,  # < 0.0
            )
    
    def test_car_data_extraction_valid(self):
        """Test valid car data extraction."""
        data = CarDataExtraction(
            brand="BMW",
            model="3 серии",
            engine_volume="2.5",
            transmission="automatic",
            year=2008,
            owners_count=2,
            mileage=150000,
            price=850000,
        )
        
        assert data.brand == "BMW"
        assert data.model == "3 Серии"  # Capitalized by validator
        assert data.transmission == "automatic"
        assert data.year == 2008
    
    def test_car_data_transmission_normalization(self):
        """Test transmission type normalization."""
        test_cases = [
            ("автомат", "automatic"),
            ("АКПП", "automatic"),
            ("механика", "manual"),
            ("робот", "robot"),
            ("вариатор", "variator"),
        ]
        
        for input_val, expected in test_cases:
            data = CarDataExtraction(transmission=input_val)
            assert data.transmission == expected
    
    def test_car_data_autoteka_normalization(self):
        """Test autoteka status normalization."""
        test_cases = [
            ("зеленая", "green"),
            ("без дтп", "green"),
            ("есть дтп", "has_accidents"),
            ("битая", "has_accidents"),
            ("неизвестно", "unknown"),
        ]
        
        for input_val, expected in test_cases:
            data = CarDataExtraction(autoteka_status=input_val)
            assert data.autoteka_status == expected
    
    def test_car_data_year_validation(self):
        """Test year validation."""
        with pytest.raises(ValidationError):
            CarDataExtraction(year=1800)  # Too old
        
        with pytest.raises(ValidationError):
            CarDataExtraction(year=2200)  # Too far in future
        
        # Valid years
        CarDataExtraction(year=2008)
        CarDataExtraction(year=1990)
        CarDataExtraction(year=2025)
    
    def test_unique_description_valid(self):
        """Test valid unique description."""
        desc = UniqueDescription(
            generated_text="Предлагаем к продаже BMW 3 серии 2008 года выпуска с автоматической коробкой передач.",
            key_points_preserved=["BMW 3 series", "2008", "automatic"],
            tone="professional"
        )
        
        assert len(desc.generated_text) >= 50
        assert len(desc.key_points_preserved) > 0
    
    def test_unique_description_too_short(self):
        """Test that short descriptions are rejected."""
        with pytest.raises(ValidationError):
            UniqueDescription(
                generated_text="Short text",  # < 50 chars
                key_points_preserved=[],
            )
    
    def test_unique_description_whitespace_cleaning(self):
        """Test whitespace cleaning in description."""
        desc = UniqueDescription(
            generated_text="Предлагаем   к   продаже    BMW",  # Multiple spaces
            key_points_preserved=["BMW"],
        )
        
        assert "  " not in desc.generated_text  # No double spaces
    
    def test_ai_processing_result_complete(self):
        """Test complete AI processing result."""
        classification = ClassificationResult(
            is_selling_post=True,
            confidence=0.95
        )
        
        car_data = CarDataExtraction(
            brand="BMW",
            model="3 серии",
            year=2008,
            price=850000
        )
        
        description = UniqueDescription(
            generated_text="Предлагаем BMW 3 серии 2008 года с автоматической коробкой передач.",
            key_points_preserved=["BMW 3 series 2008"]
        )
        
        result = AIProcessingResult(
            classification=classification,
            car_data=car_data,
            unique_description=description,
            processing_time_seconds=2.5,
            tokens_used=1500
        )
        
        assert result.classification.is_selling_post is True
        assert result.car_data.brand == "BMW"
        assert result.unique_description is not None
        assert result.tokens_used == 1500


class TestPrompts:
    """Test prompt building functions."""
    
    def test_build_classification_prompt(self):
        """Test classification prompt building."""
        text = "Продам BMW 3 серии 2008 года"
        
        system_prompt, user_prompt = build_classification_prompt(text)
        
        assert "classify" in system_prompt.lower()
        assert "selling" in system_prompt.lower()
        assert text in user_prompt
        assert "json" in system_prompt.lower()
    
    def test_build_extraction_prompt(self):
        """Test extraction prompt building."""
        text = "Продам BMW 3 серии 2.5 Автомат 2008 года"
        
        system_prompt, user_prompt = build_extraction_prompt(text)
        
        assert "extract" in system_prompt.lower()
        assert "brand" in system_prompt.lower()
        assert text in user_prompt
    
    def test_build_generation_prompt(self):
        """Test generation prompt building."""
        original_text = "Продам BMW 3 серии"
        car_data_json = '{"brand": "BMW", "model": "3 серии"}'
        
        system_prompt, user_prompt = build_generation_prompt(
            original_text, car_data_json
        )
        
        assert "unique" in system_prompt.lower()
        assert "rewrite" in system_prompt.lower()
        assert original_text in user_prompt
        assert "BMW" in user_prompt
    
    def test_prompt_length_limits(self):
        """Test that prompts limit input length."""
        very_long_text = "Продам " * 1000  # Very long text
        
        system_prompt, user_prompt = build_classification_prompt(very_long_text)
        
        # User prompt should be truncated
        assert len(user_prompt) < len(very_long_text)


class TestAIProcessorConfig:
    """Test AI Processor configuration."""
    
    def test_valid_config(self):
        """Test valid configuration."""
        config = AIProcessorConfig(
            api_key="test_key",
            model="gpt-4o-mini",
            max_retries=3,
        )
        
        assert config.api_key == "test_key"
        assert config.model == "gpt-4o-mini"
        assert config.max_retries == 3
    
    def test_config_defaults(self):
        """Test default configuration values."""
        config = AIProcessorConfig(api_key="test_key")
        
        assert config.model == "gpt-4o-mini"
        assert config.max_retries == 3
        assert config.temperature == 0.3
    
    def test_config_immutable(self):
        """Test that config is immutable."""
        config = AIProcessorConfig(api_key="test_key")
        
        with pytest.raises(ValidationError):
            config.api_key = "new_key"  # Should fail


class TestAIProcessor:
    """Test AI Processor class."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return AIProcessorConfig(
            api_key="test_key",
            model="gpt-4o-mini",
            max_retries=2,
            retry_delay=0.1,
        )
    
    @pytest.fixture
    def processor(self, config):
        """Create AI Processor instance."""
        return AIProcessor(config)
    
    def test_processor_initialization(self, processor, config):
        """Test processor initialization."""
        assert processor.config == config
        assert processor.total_requests == 0
        assert processor.total_tokens_used == 0
        assert processor.total_errors == 0
    
    def test_get_statistics(self, processor):
        """Test statistics retrieval."""
        stats = processor.get_statistics()
        
        assert "total_requests" in stats
        assert "total_tokens_used" in stats
        assert "total_errors" in stats
        assert "error_rate" in stats
    
    def test_estimate_tokens(self, processor):
        """Test token estimation."""
        text = "Продам BMW 3 серии"
        
        estimated = processor._estimate_tokens(text, 100)
        
        assert estimated > 100  # Should include input + response
        assert isinstance(estimated, int)
    
    @pytest.mark.asyncio
    async def test_classify_post_mock(self, processor):
        """Test post classification with mocked API."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.parsed = ClassificationResult(
            is_selling_post=True,
            confidence=0.95,
            reasoning="Test"
        )
        mock_response.choices[0].message.refusal = None
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 500
        mock_response.usage.prompt_tokens = 300
        mock_response.usage.completion_tokens = 200
        
        with patch.object(
            processor.client.beta.chat.completions,
            'parse',
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            result = await processor.classify_post("Продам BMW")
            
            assert result.is_selling_post is True
            assert result.confidence == 0.95
            assert processor.total_requests == 1
            assert processor.total_tokens_used == 500
    
    @pytest.mark.asyncio
    async def test_extract_car_data_mock(self, processor):
        """Test car data extraction with mocked API."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.parsed = CarDataExtraction(
            brand="BMW",
            model="3 серии",
            year=2008,
            price=850000
        )
        mock_response.choices[0].message.refusal = None
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 800
        mock_response.usage.prompt_tokens = 500
        mock_response.usage.completion_tokens = 300
        
        with patch.object(
            processor.client.beta.chat.completions,
            'parse',
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            result = await processor.extract_car_data("Продам BMW 3 серии 2008")
            
            assert result.brand == "BMW"
            assert result.year == 2008
            assert processor.total_tokens_used == 800
    
    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self, processor):
        """Test retry logic on rate limit error."""
        from openai import RateLimitError
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.parsed = ClassificationResult(
            is_selling_post=True,
            confidence=0.95
        )
        mock_response.choices[0].message.refusal = None
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 500
        mock_response.usage.prompt_tokens = 300
        mock_response.usage.completion_tokens = 200
        
        # First call raises RateLimitError, second succeeds
        mock_parse = AsyncMock()
        mock_parse.side_effect = [
            RateLimitError("Rate limit exceeded", response=None, body=None),
            mock_response
        ]
        
        with patch.object(
            processor.client.beta.chat.completions,
            'parse',
            mock_parse
        ):
            result = await processor.classify_post("Test")
            
            assert result.is_selling_post is True
            assert mock_parse.call_count == 2  # Retried once
    
    @pytest.mark.asyncio
    async def test_all_retries_fail(self, processor):
        """Test behavior when all retries fail."""
        from openai import APIError
        
        mock_parse = AsyncMock()
        mock_parse.side_effect = APIError("Persistent error", response=None, body=None)
        
        with patch.object(
            processor.client.beta.chat.completions,
            'parse',
            mock_parse
        ):
            with pytest.raises(APIError):
                await processor.classify_post("Test")
            
            # Should have tried max_retries times
            assert mock_parse.call_count == processor.config.max_retries


class TestEndToEnd:
    """End-to-end integration tests (with mocked API)."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_selling_post(self):
        """Test complete pipeline for selling post."""
        config = AIProcessorConfig(
            api_key="test_key",
            max_retries=1,
        )
        processor = AIProcessor(config)
        
        # Mock all API calls
        mock_classification = ClassificationResult(
            is_selling_post=True,
            confidence=0.95
        )
        
        mock_car_data = CarDataExtraction(
            brand="BMW",
            model="3 серии",
            year=2008,
            price=850000
        )
        
        mock_description = UniqueDescription(
            generated_text="Предлагаем BMW 3 серии 2008 года с автоматической коробкой передач.",
            key_points_preserved=["BMW 3 series 2008"]
        )
        
        # Mock responses
        def create_mock_response(parsed_obj):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message = MagicMock()
            mock_response.choices[0].message.parsed = parsed_obj
            mock_response.choices[0].message.refusal = None
            mock_response.usage = MagicMock()
            mock_response.usage.total_tokens = 500
            mock_response.usage.prompt_tokens = 300
            mock_response.usage.completion_tokens = 200
            return mock_response
        
        mock_parse = AsyncMock()
        mock_parse.side_effect = [
            create_mock_response(mock_classification),
            create_mock_response(mock_car_data),
            create_mock_response(mock_description),
        ]
        
        with patch.object(
            processor.client.beta.chat.completions,
            'parse',
            mock_parse
        ):
            result = await processor.process_post("Продам BMW 3 серии 2008 года")
            
            assert result.classification.is_selling_post is True
            assert result.car_data is not None
            assert result.car_data.brand == "BMW"
            assert result.unique_description is not None
            assert result.tokens_used > 0
            assert result.processing_time_seconds > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


