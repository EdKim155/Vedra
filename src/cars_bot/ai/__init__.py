"""
AI Processing module for car advertisements.

This module provides AI-powered functionality for:
- Post classification (is it a selling advertisement?)
- Car data extraction (structured information)
- Unique description generation (for publication)

Uses OpenAI API with:
- Pydantic for data validation
- Retry logic with exponential backoff
- Comprehensive error handling
- Request/response logging
"""

from cars_bot.ai.models import (
    AIProcessingResult,
    CarDataExtraction,
    ClassificationResult,
    UniqueDescription,
)
from cars_bot.ai.processor import AIProcessor, AIProcessorConfig, create_ai_processor_from_env
from cars_bot.ai.prompts import (
    build_classification_prompt,
    build_extraction_prompt,
    build_generation_prompt,
)

__all__ = [
    # Main processor
    "AIProcessor",
    "AIProcessorConfig",
    "create_ai_processor_from_env",
    # Models
    "ClassificationResult",
    "CarDataExtraction",
    "UniqueDescription",
    "AIProcessingResult",
    # Prompts
    "build_classification_prompt",
    "build_extraction_prompt",
    "build_generation_prompt",
]


