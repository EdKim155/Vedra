"""
AI Processing Service for car advertisement posts.

Uses OpenAI API to:
1. Classify posts (is it a selling advertisement?)
2. Extract structured car data
3. Generate unique descriptions

Includes:
- Retry logic with exponential backoff
- Comprehensive error handling
- Request/response logging
- Token usage tracking
"""

import asyncio
import json
import time
from typing import Optional, Type, TypeVar

from loguru import logger
from openai import AsyncOpenAI, APIError, RateLimitError, APITimeoutError
from pydantic import BaseModel, ValidationError

from cars_bot.ai.models import (
    AIProcessingResult,
    CarDataExtraction,
    ClassificationResult,
    UniqueDescription,
)
from cars_bot.ai.prompts import (
    build_classification_prompt,
    build_extraction_prompt,
    build_generation_prompt,
)


T = TypeVar('T', bound=BaseModel)


class AIProcessorConfig(BaseModel):
    """Configuration for AI Processor."""
    
    api_key: str
    model: str = "gpt-4o-mini"  # Default to mini for cost efficiency
    max_retries: int = 3
    retry_delay: float = 1.0  # Initial delay in seconds
    timeout: float = 30.0  # Request timeout
    temperature: float = 0.3  # Lower for more consistent results
    
    model_config = {
        'frozen': True  # Immutable config
    }


class AIProcessor:
    """
    AI processing service for car advertisements.
    
    Handles all AI operations:
    - Post classification
    - Car data extraction
    - Unique description generation
    
    Features:
    - Structured outputs with Pydantic
    - Retry logic with exponential backoff
    - Comprehensive error handling
    - Request/response logging
    - Token usage tracking
    """
    
    def __init__(self, config: AIProcessorConfig):
        """
        Initialize AI Processor.
        
        Args:
            config: AI Processor configuration
        """
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            timeout=config.timeout,
        )
        
        # Statistics
        self.total_requests = 0
        self.total_tokens_used = 0
        self.total_errors = 0
        
        logger.info(
            f"AIProcessor initialized with model={config.model}, "
            f"max_retries={config.max_retries}"
        )
    
    async def classify_post(self, text: str) -> ClassificationResult:
        """
        Classify if post is a car selling advertisement.
        
        Args:
            text: Post text to classify
        
        Returns:
            ClassificationResult with is_selling_post and confidence
        
        Raises:
            APIError: If OpenAI API request fails after retries
            ValidationError: If response doesn't match expected schema
        """
        logger.debug(f"Classifying post (length={len(text)})")
        
        system_prompt, user_prompt = build_classification_prompt(text)
        
        result = await self._call_openai_with_retry(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=ClassificationResult,
            operation="classify_post",
        )
        
        logger.info(
            f"Classification result: is_selling={result.is_selling_post}, "
            f"confidence={result.confidence:.2f}"
        )
        
        return result
    
    async def extract_car_data(self, text: str) -> CarDataExtraction:
        """
        Extract structured car data from post text.
        
        Args:
            text: Post text to extract data from
        
        Returns:
            CarDataExtraction with all extracted fields
        
        Raises:
            APIError: If OpenAI API request fails after retries
            ValidationError: If response doesn't match expected schema
        """
        logger.debug(f"Extracting car data (length={len(text)})")
        
        system_prompt, user_prompt = build_extraction_prompt(text)
        
        result = await self._call_openai_with_retry(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=CarDataExtraction,
            operation="extract_car_data",
        )
        
        logger.info(
            f"Extracted car data: {result.brand} {result.model} {result.year}, "
            f"price={result.price}"
        )
        
        return result
    
    async def generate_unique_description(
        self,
        original_text: str,
        car_data: CarDataExtraction,
    ) -> UniqueDescription:
        """
        Generate unique description for publication.
        
        Args:
            original_text: Original advertisement text
            car_data: Extracted car data
        
        Returns:
            UniqueDescription with generated text
        
        Raises:
            APIError: If OpenAI API request fails after retries
            ValidationError: If response doesn't match expected schema
        """
        logger.debug(
            f"Generating unique description (original_length={len(original_text)})"
        )
        
        # Convert car_data to JSON for prompt
        car_data_json = car_data.model_dump_json(exclude_none=True, indent=2)
        
        system_prompt, user_prompt = build_generation_prompt(
            original_text, car_data_json
        )
        
        result = await self._call_openai_with_retry(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=UniqueDescription,
            operation="generate_unique_description",
        )
        
        logger.info(
            f"Generated unique description (length={len(result.generated_text)})"
        )
        
        return result
    
    async def process_post(
        self,
        text: str,
        skip_if_not_selling: bool = True,
    ) -> AIProcessingResult:
        """
        Process post through complete AI pipeline.
        
        Pipeline:
        1. Classify post
        2. If selling post:
           - Extract car data
           - Generate unique description
        3. Return complete result
        
        Args:
            text: Post text to process
            skip_if_not_selling: Skip extraction/generation if not selling post
        
        Returns:
            AIProcessingResult with all processing results
        """
        start_time = time.time()
        total_tokens = 0
        
        logger.info(f"Starting full post processing (length={len(text)})")
        
        # Step 1: Classify
        classification = await self.classify_post(text)
        total_tokens += self._estimate_tokens(text, 200)  # Rough estimate
        
        car_data = None
        unique_description = None
        
        # Step 2 & 3: Extract and Generate (only for selling posts)
        if classification.is_selling_post:
            if skip_if_not_selling:
                logger.info("Skipping extraction/generation for non-selling post")
            else:
                try:
                    car_data = await self.extract_car_data(text)
                    total_tokens += self._estimate_tokens(text, 500)
                    
                    unique_description = await self.generate_unique_description(
                        text, car_data
                    )
                    total_tokens += self._estimate_tokens(text, 800)
                    
                except Exception as e:
                    logger.error(f"Error in extraction/generation: {e}")
                    # Continue with partial results
        
        # If selling post but skip_if_not_selling is True, do extraction/generation
        if classification.is_selling_post and skip_if_not_selling:
            try:
                car_data = await self.extract_car_data(text)
                total_tokens += self._estimate_tokens(text, 500)
                
                unique_description = await self.generate_unique_description(
                    text, car_data
                )
                total_tokens += self._estimate_tokens(text, 800)
                
            except Exception as e:
                logger.error(f"Error in extraction/generation: {e}")
                # Continue with partial results
        
        processing_time = time.time() - start_time
        
        result = AIProcessingResult(
            classification=classification,
            car_data=car_data,
            unique_description=unique_description,
            processing_time_seconds=processing_time,
            tokens_used=total_tokens,
        )
        
        logger.info(
            f"✅ Post processing complete: "
            f"is_selling={classification.is_selling_post}, "
            f"time={processing_time:.2f}s, tokens={total_tokens}"
        )
        
        return result
    
    async def _call_openai_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        operation: str,
    ) -> T:
        """
        Call OpenAI API with retry logic and exponential backoff.
        
        Args:
            system_prompt: System message
            user_prompt: User message
            response_model: Pydantic model for response
            operation: Operation name for logging
        
        Returns:
            Parsed response as Pydantic model
        
        Raises:
            APIError: If all retries fail
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                self.total_requests += 1
                
                logger.debug(
                    f"[{operation}] API call attempt {attempt + 1}/"
                    f"{self.config.max_retries}"
                )
                
                # Use structured outputs (parse method)
                completion = await self.client.beta.chat.completions.parse(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format=response_model,
                    temperature=self.config.temperature,
                )
                
                # Extract parsed response
                message = completion.choices[0].message
                
                if message.parsed:
                    result = message.parsed
                    
                    # Log usage
                    if completion.usage:
                        tokens_used = completion.usage.total_tokens
                        self.total_tokens_used += tokens_used
                        logger.debug(
                            f"[{operation}] Tokens used: {tokens_used} "
                            f"(prompt={completion.usage.prompt_tokens}, "
                            f"completion={completion.usage.completion_tokens})"
                        )
                    
                    logger.debug(f"[{operation}] ✅ Success")
                    return result
                
                elif message.refusal:
                    logger.warning(f"[{operation}] Model refused: {message.refusal}")
                    raise APIError(f"Model refused to respond: {message.refusal}")
                
                else:
                    logger.error(f"[{operation}] No parsed response")
                    raise APIError("No parsed response from model")
                
            except RateLimitError as e:
                last_exception = e
                self.total_errors += 1
                
                # Exponential backoff for rate limits
                delay = self.config.retry_delay * (2 ** attempt)
                logger.warning(
                    f"[{operation}] Rate limit hit, retrying in {delay}s... "
                    f"(attempt {attempt + 1}/{self.config.max_retries})"
                )
                
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(delay)
                
            except APITimeoutError as e:
                last_exception = e
                self.total_errors += 1
                
                logger.warning(
                    f"[{operation}] Request timeout, retrying... "
                    f"(attempt {attempt + 1}/{self.config.max_retries})"
                )
                
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
                
            except APIError as e:
                last_exception = e
                self.total_errors += 1
                
                logger.error(
                    f"[{operation}] API error: {e} "
                    f"(attempt {attempt + 1}/{self.config.max_retries})"
                )
                
                # Don't retry on certain errors
                if "invalid_request" in str(e).lower():
                    raise
                
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                
            except ValidationError as e:
                last_exception = e
                self.total_errors += 1
                
                logger.error(
                    f"[{operation}] Response validation error: {e} "
                    f"(attempt {attempt + 1}/{self.config.max_retries})"
                )
                
                # Don't retry validation errors
                raise
                
            except Exception as e:
                last_exception = e
                self.total_errors += 1
                
                logger.error(
                    f"[{operation}] Unexpected error: {e} "
                    f"(attempt {attempt + 1}/{self.config.max_retries})",
                    exc_info=True
                )
                
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
        
        # All retries failed
        logger.error(
            f"[{operation}] ❌ All {self.config.max_retries} attempts failed"
        )
        raise last_exception or APIError("All retry attempts failed")
    
    def _estimate_tokens(self, text: str, response_tokens: int = 100) -> int:
        """
        Estimate token usage for a request.
        
        Rough estimation: 1 token ≈ 4 characters for English, ~3 for Russian.
        
        Args:
            text: Input text
            response_tokens: Estimated response tokens
        
        Returns:
            Estimated total tokens
        """
        # Very rough estimation
        input_tokens = len(text) // 3  # ~3 chars per token for Russian
        return input_tokens + response_tokens
    
    def get_statistics(self) -> dict:
        """
        Get processor statistics.
        
        Returns:
            Dict with usage statistics
        """
        return {
            "total_requests": self.total_requests,
            "total_tokens_used": self.total_tokens_used,
            "total_errors": self.total_errors,
            "error_rate": (
                self.total_errors / self.total_requests
                if self.total_requests > 0
                else 0.0
            ),
        }
    
    async def close(self):
        """Close OpenAI client."""
        await self.client.close()
        logger.info("AIProcessor closed")


# Convenience function for creating processor from environment
def create_ai_processor_from_env() -> AIProcessor:
    """
    Create AI Processor from environment variables.
    
    Expected environment variables:
    - OPENAI_API_KEY
    - OPENAI_MODEL (optional, defaults to gpt-4o-mini)
    - OPENAI_MAX_RETRIES (optional, defaults to 3)
    
    Returns:
        Configured AIProcessor instance
    """
    import os
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    config = AIProcessorConfig(
        api_key=api_key,
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "3")),
        retry_delay=float(os.getenv("OPENAI_RETRY_DELAY", "1.0")),
        timeout=float(os.getenv("OPENAI_TIMEOUT", "30.0")),
        temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.3")),
    )
    
    return AIProcessor(config)

