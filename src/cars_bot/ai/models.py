"""
Pydantic models for AI processing responses.

These models define the structure of expected responses from OpenAI API
and provide validation, type safety, and serialization.
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from cars_bot.database.enums import AutotekaStatus, TransmissionType


class ClassificationResult(BaseModel):
    """
    Result of post classification by AI.
    
    Determines whether the post is a selling advertisement or not.
    """
    
    is_selling_post: bool = Field(
        description="Whether this is a car selling advertisement"
    )
    
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0 to 1.0)"
    )
    
    reasoning: Optional[str] = Field(
        default=None,
        description="Explanation of the classification decision"
    )
    
    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    "is_selling_post": True,
                    "confidence": 0.95,
                    "reasoning": "Post contains price, car details, and seller contact information"
                }
            ]
        }
    }


class CarDataExtraction(BaseModel):
    """
    Structured car data extracted from post by AI.
    
    Maps to the car_data table in database.
    """
    
    # Vehicle basic information
    brand: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Car brand (e.g., BMW, Toyota, Mercedes)"
    )
    
    model: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Car model (e.g., 3 Series, Camry, E-Class)"
    )
    
    engine_volume: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Engine volume (e.g., 2.0, 1.6, 3.5)"
    )
    
    transmission: Optional[str] = Field(
        default=None,
        description="Transmission type: automatic, manual, robot, variator"
    )
    
    year: Optional[int] = Field(
        default=None,
        ge=1900,
        le=2100,
        description="Manufacturing year"
    )
    
    # Vehicle history
    owners_count: Optional[int] = Field(
        default=None,
        ge=0,
        le=20,
        description="Number of previous owners"
    )
    
    mileage: Optional[int] = Field(
        default=None,
        ge=0,
        description="Mileage in kilometers"
    )
    
    autoteka_status: Optional[str] = Field(
        default=None,
        description="Vehicle history check: green, has_accidents, unknown"
    )
    
    # Equipment & condition
    equipment: Optional[str] = Field(
        default=None,
        description="Equipment and features description"
    )
    
    # Pricing
    price: Optional[int] = Field(
        default=None,
        ge=0,
        description="Selling price in rubles"
    )
    
    market_price: Optional[int] = Field(
        default=None,
        ge=0,
        description="Market price estimate in rubles"
    )
    
    price_justification: Optional[str] = Field(
        default=None,
        description="Justification for the price"
    )
    
    @field_validator('transmission')
    @classmethod
    def validate_transmission(cls, v: Optional[str]) -> Optional[str]:
        """Normalize transmission type."""
        if not v:
            return None
        
        v_lower = v.lower()
        
        # Mapping from various inputs to standard values
        transmission_map = {
            'автомат': 'automatic',
            'акпп': 'automatic',
            'автоматическая': 'automatic',
            'automatic': 'automatic',
            'механика': 'manual',
            'мкпп': 'manual',
            'механическая': 'manual',
            'manual': 'manual',
            'робот': 'robot',
            'роботизированная': 'robot',
            'robot': 'robot',
            'вариатор': 'variator',
            'cvt': 'variator',
            'variator': 'variator',
        }
        
        return transmission_map.get(v_lower, v_lower)
    
    @field_validator('autoteka_status')
    @classmethod
    def validate_autoteka(cls, v: Optional[str]) -> Optional[str]:
        """Normalize autoteka status."""
        if not v:
            return None
        
        v_lower = v.lower()
        
        # Mapping from various inputs to standard values
        autoteka_map = {
            'зеленая': 'green',
            'чистая': 'green',
            'без дтп': 'green',
            'green': 'green',
            'дтп': 'has_accidents',
            'есть дтп': 'has_accidents',
            'битая': 'has_accidents',
            'has_accidents': 'has_accidents',
            'неизвестно': 'unknown',
            'нет данных': 'unknown',
            'unknown': 'unknown',
        }
        
        return autoteka_map.get(v_lower, 'unknown')
    
    @field_validator('brand', 'model')
    @classmethod
    def capitalize_name(cls, v: Optional[str]) -> Optional[str]:
        """Capitalize brand and model names."""
        if not v:
            return None
        return v.strip().title()
    
    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    "brand": "BMW",
                    "model": "3 серии",
                    "engine_volume": "2.5",
                    "transmission": "automatic",
                    "year": 2008,
                    "owners_count": 2,
                    "mileage": 150000,
                    "autoteka_status": "green",
                    "equipment": "Полная комплектация, кожаный салон, панорама",
                    "price": 850000,
                    "market_price": 900000,
                    "price_justification": "Цена ниже рынка из-за срочной продажи"
                }
            ]
        }
    }


class UniqueDescription(BaseModel):
    """
    Unique generated description for publication.
    
    AI-generated text that preserves key information but uses unique wording.
    """
    
    generated_text: str = Field(
        min_length=50,
        max_length=3000,
        description="Unique generated description"
    )
    
    key_points_preserved: list[str] = Field(
        default_factory=list,
        description="List of key information points preserved from original"
    )
    
    tone: str = Field(
        default="professional",
        description="Tone of the generated text"
    )
    
    @field_validator('generated_text')
    @classmethod
    def clean_text(cls, v: str) -> str:
        """Clean and normalize generated text."""
        # Remove excessive whitespace
        import re
        v = re.sub(r'\s+', ' ', v).strip()
        return v
    
    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    "generated_text": "Предлагаем к продаже BMW 3 серии 2008 года выпуска...",
                    "key_points_preserved": [
                        "BMW 3 series 2008",
                        "2.5L engine automatic",
                        "150k km, 2 owners",
                        "Price: 850,000 RUB"
                    ],
                    "tone": "professional"
                }
            ]
        }
    }


class AIProcessingResult(BaseModel):
    """
    Complete result of AI processing for a post.
    
    Combines all AI operations: classification, extraction, and generation.
    """
    
    classification: ClassificationResult = Field(
        description="Post classification result"
    )
    
    car_data: Optional[CarDataExtraction] = Field(
        default=None,
        description="Extracted car data (only if is_selling_post=True)"
    )
    
    unique_description: Optional[UniqueDescription] = Field(
        default=None,
        description="Generated unique description (only if is_selling_post=True)"
    )
    
    processing_time_seconds: float = Field(
        ge=0.0,
        description="Total processing time in seconds"
    )
    
    tokens_used: int = Field(
        ge=0,
        description="Total tokens used for all API calls"
    )
    
    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    "classification": {
                        "is_selling_post": True,
                        "confidence": 0.95,
                        "reasoning": "Contains price and car details"
                    },
                    "car_data": {
                        "brand": "BMW",
                        "model": "3 серии",
                        "year": 2008,
                        "price": 850000
                    },
                    "unique_description": {
                        "generated_text": "Предлагаем BMW 3 серии...",
                        "key_points_preserved": ["BMW 3 series 2008"],
                        "tone": "professional"
                    },
                    "processing_time_seconds": 2.5,
                    "tokens_used": 1500
                }
            ]
        }
    }


