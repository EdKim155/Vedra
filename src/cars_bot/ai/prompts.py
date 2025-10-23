"""
Optimized prompts for AI processing.

All prompts are designed to:
- Minimize token usage
- Provide clear instructions
- Return structured JSON responses
- Handle edge cases
"""

# System prompts for different tasks

CLASSIFICATION_SYSTEM_PROMPT = """You are an expert at classifying Telegram channel posts about cars.

Your task: Determine if a post is a SELLING ADVERTISEMENT for a car.

Selling post characteristics:
- Contains car details (brand, model, year)
- Mentions price or "продам" (selling)
- Has seller contact information
- Describes car condition or features

NOT selling posts:
- News articles
- General discussions
- Questions from buyers
- Service advertisements
- Memes or entertainment

Respond ONLY with valid JSON matching this schema:
{
  "is_selling_post": boolean,
  "confidence": float (0.0-1.0),
  "reasoning": string (brief explanation)
}"""

CLASSIFICATION_USER_PROMPT_TEMPLATE = """Classify this Telegram post:

{text}

Is this a car selling advertisement?"""


EXTRACTION_SYSTEM_PROMPT = """You are an expert at extracting structured car data from Russian-language selling advertisements.

Extract ALL available information. Use null for missing data.

Field guidelines:
- brand: Standard brand name (BMW, Toyota, Mercedes, etc.)
- model: Model name as written (3 серии, Camry, E-Class)
- engine_volume: Just the number (2.0, 1.6, 3.5)
- transmission: automatic/manual/robot/variator
- year: 4-digit year (1990-2025)
- owners_count: Number of previous owners
- mileage: Kilometers as integer
- autoteka_status: green/has_accidents/unknown
- equipment: Brief description of features
- price: Price in rubles (integer)
- market_price: Market estimate if mentioned
- price_justification: Why this price

Respond ONLY with valid JSON matching the CarDataExtraction schema."""

EXTRACTION_USER_PROMPT_TEMPLATE = """Extract car data from this advertisement:

{text}

Return complete JSON with all available fields."""


GENERATION_SYSTEM_PROMPT = """You are a professional car advertisement writer.

Task: Rewrite the car advertisement in a UNIQUE, professional style while preserving ALL key information.

Requirements:
1. Use completely different wording (for anti-plagiarism)
2. Keep ALL factual information:
   - Brand, model, year, engine, transmission
   - Mileage, owners, condition
   - Price and justification
   - Equipment and features
3. Professional, neutral tone
4. Well-structured format
5. 100-500 words
6. Russian language

Output format:
{
  "generated_text": "Unique rewritten advertisement...",
  "key_points_preserved": ["BMW 3 series 2008", "Price 850k"],
  "tone": "professional"
}

Do NOT:
- Add information not in the original
- Use overly promotional language
- Include contact details (handled separately)
- Write in first person"""

GENERATION_USER_PROMPT_TEMPLATE = """Original advertisement:
{original_text}

Structured data:
{car_data_json}

Rewrite this as a unique, professional car advertisement preserving all key facts."""


# Prompts for error handling and validation

VALIDATION_SYSTEM_PROMPT = """You are a data quality validator.

Check if extracted car data is reasonable and complete.

Validation rules:
- Brand/model should be real car brands
- Year should be realistic (1980-2025)
- Price should be reasonable (50k-50M rubles)
- Mileage should match year (avg 15k km/year)
- Transmission type should be valid

Respond with:
{
  "is_valid": boolean,
  "issues": [list of problems if any],
  "completeness_score": float (0.0-1.0)
}"""

VALIDATION_USER_PROMPT_TEMPLATE = """Validate this car data:

{car_data_json}

Check for errors and completeness."""


# Few-shot examples for better results

CLASSIFICATION_EXAMPLES = [
    {
        "text": "Продам BMW 3 серии 2008 года, 2.5 автомат. Пробег 150к, 2 владельца, зеленая автотека. Цена 850к. @seller",
        "response": {
            "is_selling_post": True,
            "confidence": 0.98,
            "reasoning": "Contains brand, model, year, price, mileage, and seller contact"
        }
    },
    {
        "text": "Кто знает хороший сервис для ремонта BMW? Нужны рекомендации.",
        "response": {
            "is_selling_post": False,
            "confidence": 0.95,
            "reasoning": "This is a question about car service, not a selling advertisement"
        }
    }
]

EXTRACTION_EXAMPLES = [
    {
        "text": "Продам BMW 3 серии 2.5 Автомат 2008. Пробег 150 тыс км, 2 владельца по ПТС. Зеленая автотека. Полная комплектация, кожа, панорама. Цена 850 тысяч рублей, реальный торг.",
        "response": {
            "brand": "BMW",
            "model": "3 серии",
            "engine_volume": "2.5",
            "transmission": "automatic",
            "year": 2008,
            "owners_count": 2,
            "mileage": 150000,
            "autoteka_status": "green",
            "equipment": "Полная комплектация, кожаный салон, панорамная крыша",
            "price": 850000,
            "market_price": None,
            "price_justification": "Реальный торг уместен"
        }
    }
]


# Helper functions for prompt construction

def build_classification_prompt(text: str) -> tuple[str, str]:
    """
    Build classification prompt with system and user messages.
    
    Args:
        text: Post text to classify
    
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    return (
        CLASSIFICATION_SYSTEM_PROMPT,
        CLASSIFICATION_USER_PROMPT_TEMPLATE.format(text=text[:2000])  # Limit length
    )


def build_extraction_prompt(text: str) -> tuple[str, str]:
    """
    Build extraction prompt with system and user messages.
    
    Args:
        text: Post text to extract data from
    
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    return (
        EXTRACTION_SYSTEM_PROMPT,
        EXTRACTION_USER_PROMPT_TEMPLATE.format(text=text[:3000])  # Limit length
    )


def build_generation_prompt(original_text: str, car_data_json: str) -> tuple[str, str]:
    """
    Build generation prompt with system and user messages.
    
    Args:
        original_text: Original advertisement text
        car_data_json: JSON string of extracted car data
    
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    return (
        GENERATION_SYSTEM_PROMPT,
        GENERATION_USER_PROMPT_TEMPLATE.format(
            original_text=original_text[:2000],  # Limit length
            car_data_json=car_data_json[:1000]   # Limit length
        )
    )


def build_validation_prompt(car_data_json: str) -> tuple[str, str]:
    """
    Build validation prompt with system and user messages.
    
    Args:
        car_data_json: JSON string of extracted car data
    
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    return (
        VALIDATION_SYSTEM_PROMPT,
        VALIDATION_USER_PROMPT_TEMPLATE.format(car_data_json=car_data_json)
    )


# Token optimization tips
"""
Token optimization strategies used in these prompts:

1. **Concise instructions**: Clear, brief system prompts
2. **Structured output**: JSON schema reduces token usage in responses
3. **Length limits**: Input text is truncated to prevent excessive tokens
4. **No redundancy**: Each instruction appears only once
5. **Direct format**: No conversational fluff
6. **Schema reference**: Use schema names instead of repeating structure

Typical token usage:
- Classification: ~500-700 tokens (system + user + response)
- Extraction: ~800-1200 tokens
- Generation: ~1000-1500 tokens

Total per post: ~2500-3500 tokens
With GPT-4o: ~$0.03-0.04 per post
With GPT-3.5-turbo: ~$0.005-0.007 per post
"""

