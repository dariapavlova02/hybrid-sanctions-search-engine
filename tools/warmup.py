#!/usr/bin/env python3
"""
Warmup script for AI normalization service.

This script preloads the service and runs normalization on sample data
to warm up caches and ensure the service is ready for production.
"""

import argparse
import asyncio
import os
import sys
import time
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai_service.layers.normalization.normalization_service import NormalizationService
from ai_service.utils import get_logger

logger = get_logger(__name__)

# Sample data for warmup
SAMPLE_DATA = {
    "russian": [
        "Владимир Владимирович Путин",
        "Мария Ивановна Петрова",
        "Александр Сергеевич Пушкин",
        "Анна Андреевна Ахматова",
        "Дмитрий Иванович Менделеев",
        "Екатерина Великая",
        "Петр Первый",
        "Иван Грозный",
        "Николай Второй",
        "Александр Невский"
    ],
    "ukrainian": [
        "Петро Порошенко",
        "Володимир Зеленський",
        "Леся Українка",
        "Тарас Шевченко",
        "Іван Франко",
        "Олександр Довженко",
        "Михайло Грушевський",
        "Богдан Хмельницький",
        "Іван Мазепа",
        "Симон Петлюра"
    ],
    "english": [
        "John Smith",
        "Mary Johnson",
        "Robert Brown",
        "Jennifer Davis",
        "Michael Wilson",
        "Elizabeth Taylor",
        "William Anderson",
        "Sarah Martinez",
        "David Thompson",
        "Lisa Garcia"
    ],
    "mixed": [
        "José María García",
        "Jean-Baptiste Müller",
        "O'Connor Patrick",
        "van der Berg Jan",
        "de la Cruz Maria",
        "Al-Hassan Ahmed",
        "O'Brien Michael",
        "MacDonald James",
        "Fitzgerald John",
        "O'Connor Mary"
    ]
}

class WarmupService:
    """Service for warming up the normalization service."""
    
    def __init__(self):
        self.service = None
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }
    
    async def initialize_service(self) -> None:
        """Initialize the normalization service."""
        try:
            logger.info("Initializing normalization service...")
            self.service = NormalizationService()
            logger.info("✓ Service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize service: {e}")
            raise
    
    async def warmup_single_text(self, text: str, language: str = "auto") -> Dict[str, Any]:
        """Warmup a single text."""
        start_time = time.time()
        
        try:
            result = await self.service.normalize_async(text, language=language)
            end_time = time.time()
            
            self.stats["total_requests"] += 1
            self.stats["successful_requests"] += 1
            self.stats["total_time"] += (end_time - start_time)
            
            # Check cache statistics if available
            if hasattr(self.service, '_morph_cache') and hasattr(self.service._morph_cache, 'cache_info'):
                cache_info = self.service._morph_cache.cache_info()
                # Defensive access to cache_info attributes
                hits = getattr(cache_info, 'hits', cache_info.get('hits', 0) if isinstance(cache_info, dict) else 0)
                misses = getattr(cache_info, 'misses', cache_info.get('misses', 0) if isinstance(cache_info, dict) else 0)
                self.stats["cache_hits"] += hits
                self.stats["cache_misses"] += misses
            
            return {
                "text": text,
                "language": language,
                "success": result.success,
                "normalized": result.normalized_text,
                "tokens": len(result.tokens),
                "processing_time": end_time - start_time
            }
            
        except Exception as e:
            end_time = time.time()
            self.stats["total_requests"] += 1
            self.stats["failed_requests"] += 1
            self.stats["total_time"] += (end_time - start_time)
            
            logger.warning(f"Failed to normalize '{text}': {e}")
            return {
                "text": text,
                "language": language,
                "success": False,
                "error": str(e),
                "processing_time": end_time - start_time
            }
    
    async def warmup_batch(self, texts: List[str], language: str = "auto") -> List[Dict[str, Any]]:
        """Warmup a batch of texts."""
        logger.info(f"Warming up {len(texts)} texts in {language}...")
        
        results = []
        for i, text in enumerate(texts):
            if i % 10 == 0:
                logger.info(f"Processing text {i+1}/{len(texts)}: {text[:50]}...")
            
            result = await self.warmup_single_text(text, language)
            results.append(result)
        
        return results
    
    async def run_warmup(self, n: int = 200) -> None:
        """Run the complete warmup process."""
        logger.info(f"Starting warmup with {n} requests...")
        
        # Initialize service
        await self.initialize_service()
        
        # Prepare sample data
        all_texts = []
        for lang, texts in SAMPLE_DATA.items():
            all_texts.extend(texts)
        
        # Repeat texts to reach n requests
        while len(all_texts) < n:
            all_texts.extend(list(SAMPLE_DATA.values())[0])  # Add more from first category
        
        # Take first n texts
        selected_texts = all_texts[:n]
        
        # Warmup with different languages
        languages = ["ru", "uk", "en", "auto"]
        results = []
        
        for lang in languages:
            lang_texts = selected_texts[:n//len(languages)]
            if lang_texts:
                lang_results = await self.warmup_batch(lang_texts, lang)
                results.extend(lang_results)
        
        # Print statistics
        self.print_statistics()
    
    def print_statistics(self) -> None:
        """Print warmup statistics."""
        logger.info("=== Warmup Statistics ===")
        logger.info(f"Total requests: {self.stats['total_requests']}")
        logger.info(f"Successful requests: {self.stats['successful_requests']}")
        logger.info(f"Failed requests: {self.stats['failed_requests']}")
        logger.info(f"Success rate: {self.stats['successful_requests']/self.stats['total_requests']*100:.1f}%")
        logger.info(f"Total time: {self.stats['total_time']:.2f}s")
        logger.info(f"Average time per request: {self.stats['total_time']/self.stats['total_requests']*1000:.1f}ms")
        
        if self.stats['cache_hits'] + self.stats['cache_misses'] > 0:
            cache_hit_rate = self.stats['cache_hits'] / (self.stats['cache_hits'] + self.stats['cache_misses']) * 100
            logger.info(f"Cache hit rate: {cache_hit_rate:.1f}%")
            logger.info(f"Cache hits: {self.stats['cache_hits']}")
            logger.info(f"Cache misses: {self.stats['cache_misses']}")

async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Warmup AI normalization service")
    parser.add_argument("--n", type=int, default=200, help="Number of warmup requests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Set up logging
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.INFO)
    
    # Create and run warmup service
    warmup_service = WarmupService()
    await warmup_service.run_warmup(args.n)
    
    logger.info("✓ Warmup completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
