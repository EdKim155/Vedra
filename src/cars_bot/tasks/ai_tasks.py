"""
AI processing tasks for Celery.

Tasks:
- process_post_task: Full AI processing pipeline
- classify_post_task: Classify if post is selling advertisement
- extract_data_task: Extract structured car data
- generate_description_task: Generate unique description
"""

import time
from datetime import datetime
from typing import Optional

from celery import Task
from loguru import logger
from openai import APIError, RateLimitError

from cars_bot.ai.models import AIProcessingResult, CarDataExtraction, ClassificationResult
from cars_bot.ai.processor import AIProcessor, AIProcessorConfig
from cars_bot.celery_app import app


class AIProcessingTask(Task):
    """
    Base task for AI processing with retry logic.

    Automatically retries on API errors with exponential backoff.
    """

    autoretry_for = (APIError, RateLimitError, ConnectionError, TimeoutError)
    max_retries = 5
    retry_backoff = True  # Exponential backoff
    retry_backoff_max = 600  # Max 10 minutes
    retry_jitter = True  # Add randomness to prevent thundering herd

    _processor: Optional[AIProcessor] = None

    @property
    def processor(self) -> AIProcessor:
        """
        Lazy-loaded AI processor (shared across tasks in same worker).

        Returns:
            AIProcessor instance
        """
        if self._processor is None:
            import os

            config = AIProcessorConfig(
                api_key=os.getenv("OPENAI_API_KEY"),
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                max_retries=3,
                timeout=30.0,
                temperature=0.3,
            )
            self._processor = AIProcessor(config)
            logger.info("AIProcessor initialized for Celery task")

        return self._processor


@app.task(
    bind=True,
    base=AIProcessingTask,
    name="cars_bot.tasks.ai_tasks.process_post_task",
    soft_time_limit=300,  # 5 minutes soft limit
    time_limit=360,  # 6 minutes hard limit
)
def process_post_task(self, post_id: int) -> dict:
    """
    Process post through full AI pipeline.

    Steps:
    1. Load post from database
    2. Classify post (is it selling?)
    3. If selling: extract data + generate description
    4. Save results to database
    5. Queue for publishing

    Args:
        post_id: Post ID to process

    Returns:
        Dict with processing results
    """
    import asyncio
    from sqlalchemy import select
    from cars_bot.database.session import get_db_manager
    from cars_bot.database.models.post import Post
    from cars_bot.database.models.car_data import CarData

    logger.info(f"[Task] Processing post {post_id}")
    start_time = time.time()

    async def do_process():
        from sqlalchemy.orm import selectinload
        
        db_manager = get_db_manager()
        async with db_manager.session() as session:
            # Load post with relationships
            result = await session.execute(
                select(Post)
                .where(Post.id == post_id)
                .options(
                    selectinload(Post.seller_contact),
                    selectinload(Post.car_data)
                )
            )
            post = result.scalar_one_or_none()

            if not post:
                logger.error(f"Post {post_id} not found")
                return {"success": False, "error": "Post not found"}

            if not post.original_text:
                logger.error(f"Post {post_id} has no text")
                return {"success": False, "error": "Post has no text"}

            try:
                # Process with AI
                result: AIProcessingResult = await self.processor.process_post(
                    post.original_text, skip_if_not_selling=True
                )

                # Update post with classification
                post.is_selling_post = result.classification.is_selling_post
                post.confidence_score = result.classification.confidence
                
                logger.info(
                    f"Post {post_id}: is_selling={result.classification.is_selling_post}, "
                    f"has_car_data={result.car_data is not None}"
                )

                if result.classification.is_selling_post and result.car_data:
                    logger.info(f"💾 Saving car data for post {post_id}: {result.car_data.brand} {result.car_data.model}")
                    
                    # Save car data
                    car_data = CarData(
                        post_id=post.id,
                        brand=result.car_data.brand,
                        model=result.car_data.model,
                        engine_volume=result.car_data.engine_volume,
                        transmission=result.car_data.transmission,
                        year=result.car_data.year,
                        owners_count=result.car_data.owners_count,
                        mileage=result.car_data.mileage,
                        autoteka_status=result.car_data.autoteka_status,
                        equipment=result.car_data.equipment,
                        price=result.car_data.price,
                        market_price=result.car_data.market_price,
                        price_justification=result.car_data.price_justification,
                    )
                    session.add(car_data)
                    
                    # Save AI-extracted contacts (replacing old regex extraction)
                    if result.contacts:
                        from cars_bot.database.models.seller_contact import SellerContact
                        
                        # Check if seller_contact already exists (from regex)
                        if post.seller_contact:
                            # Update existing contact with AI data
                            post.seller_contact.telegram_username = result.contacts.telegram_username or post.seller_contact.telegram_username
                            post.seller_contact.phone_number = result.contacts.phone_number or post.seller_contact.phone_number
                            post.seller_contact.other_contacts = result.contacts.other_contacts or post.seller_contact.other_contacts
                            logger.info(f"📞 Updated contacts for post {post_id} with AI data")
                        else:
                            # Create new seller contact
                            seller_contact = SellerContact(
                                post_id=post.id,
                                telegram_username=result.contacts.telegram_username,
                                phone_number=result.contacts.phone_number,
                                other_contacts=result.contacts.other_contacts,
                            )
                            session.add(seller_contact)
                            logger.info(f"📞 Saved AI-extracted contacts for post {post_id}")

                    # Save generated description
                    if result.unique_description:
                        post.processed_text = result.unique_description.generated_text
                        logger.info(f"📝 Saved processed text ({len(post.processed_text)} chars)")

                    # Mark as ready for publishing
                    post.date_processed = datetime.now()

                    # Commit before queuing publish task
                    await session.commit()
                    logger.info(f"✅ Committed post {post_id} to database")

                    # Queue for publishing
                    from cars_bot.tasks.publishing_tasks import publish_post_task

                    task = publish_post_task.apply_async(
                        args=[post_id], countdown=5, priority=5
                    )
                    logger.info(f"📤 Queued post {post_id} for publishing (task_id={task.id})")
                    
                else:
                    # Just commit the classification
                    await session.commit()
                    logger.info(
                        f"⚠️ Post {post_id} not queued for publishing: "
                        f"is_selling={result.classification.is_selling_post}, "
                        f"has_car_data={result.car_data is not None}"
                    )

                processing_time = time.time() - start_time

                logger.info(
                    f"✅ Post {post_id} processed in {processing_time:.2f}s: "
                    f"is_selling={result.classification.is_selling_post}, "
                    f"confidence={result.classification.confidence:.2f}"
                )

                return {
                    "success": True,
                    "post_id": post_id,
                    "is_selling_post": result.classification.is_selling_post,
                    "confidence": result.classification.confidence,
                    "tokens_used": result.tokens_used,
                    "processing_time": processing_time,
                }

            except Exception as e:
                logger.error(f"Error processing post {post_id}: {e}", exc_info=True)
                raise

    return asyncio.run(do_process())


@app.task(
    bind=True,
    base=AIProcessingTask,
    name="cars_bot.tasks.ai_tasks.classify_post_task",
    soft_time_limit=60,
    time_limit=90,
)
def classify_post_task(self, text: str) -> dict:
    """
    Classify if post is selling advertisement.

    Args:
        text: Post text to classify

    Returns:
        Dict with classification result
    """
    logger.debug(f"[Task] Classifying post (length={len(text)})")

    try:
        result: ClassificationResult = self.processor.classify_post(text)

        return {
            "is_selling_post": result.is_selling_post,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
        }

    except Exception as e:
        logger.error(f"Error classifying post: {e}", exc_info=True)
        raise


@app.task(
    bind=True,
    base=AIProcessingTask,
    name="cars_bot.tasks.ai_tasks.extract_data_task",
    soft_time_limit=120,
    time_limit=150,
)
def extract_data_task(self, text: str) -> dict:
    """
    Extract structured car data from post.

    Args:
        text: Post text to extract data from

    Returns:
        Dict with extracted car data
    """
    logger.debug(f"[Task] Extracting car data (length={len(text)})")

    try:
        result: CarDataExtraction = self.processor.extract_car_data(text)

        return result.model_dump(exclude_none=True)

    except Exception as e:
        logger.error(f"Error extracting car data: {e}", exc_info=True)
        raise


@app.task(
    bind=True,
    base=AIProcessingTask,
    name="cars_bot.tasks.ai_tasks.generate_description_task",
    soft_time_limit=180,
    time_limit=210,
)
def generate_description_task(
    self, original_text: str, car_data_json: str
) -> dict:
    """
    Generate unique description for publication.

    Args:
        original_text: Original post text
        car_data_json: JSON string of extracted car data

    Returns:
        Dict with generated description
    """
    logger.debug(f"[Task] Generating description")

    try:
        import json
        from cars_bot.ai.models import CarDataExtraction

        car_data = CarDataExtraction(**json.loads(car_data_json))

        result = self.processor.generate_unique_description(original_text, car_data)

        return {
            "generated_text": result.generated_text,
            "key_points_preserved": result.key_points_preserved,
            "tone": result.tone,
        }

    except Exception as e:
        logger.error(f"Error generating description: {e}", exc_info=True)
        raise




